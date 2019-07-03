#!/usr/bin/env python3
#
# Author: Joshua Bachmeier <joshua.bachmeier@student.kit.edu>
#

import os
import sys
import subprocess
from subprocess import CalledProcessError
from pathlib import Path
import logging
import json
from configparser import ConfigParser

import regex
from unidecode import unidecode

### Result types
class Result:
    def __init__(self, state, message):
        self.state = state
        self.message = message

    @property
    def attributes(self):
        return self.__dict__


## Sucessful
class Success(Result):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Deployed(Success):
    def __init__(self, credentials, **kwargs):
        super().__init__(state='deployed', **kwargs)
        self.credentials = credentials

class NotDeployed(Success):
    def __init__(self, **kwargs):
        super().__init__(state='not_deployed', **kwargs)


## Exceptional (Error or Questionnaire)
class ExceptionalResult(Result, Exception):
    pass

class Failure(ExceptionalResult):
    def __init__(self, **kwargs):
        super().__init__(state='failed', **kwargs)

class Rejection(ExceptionalResult):
    def __init__(self, **kwargs):
        super().__init__(state='rejected', **kwargs)

class Questionnaire(ExceptionalResult):
    def __init__(self, questions, **kwargs):
         super().__init__(state='questionnaire', message='There are unanswered questions.', **kwargs)
         self.questionnaire = questions

class Question(Questionnaire):
    def __init__(self, name, text, **kwargs):
         super().__init__(questions={name: text}, **kwargs)


### Core logic
def main(state_target, user):
    if state_target == 'deployed':
        return deploy(user)
    elif state_target == 'not_deployed':
        return undeploy(user)
    else:
        raise Failure(message="[BUG] Invalid target state: {}".format(state_target))

def deploy(user):
    was_created = user.ensure_exists()
    new_groups = user.ensure_group_memberships()
    new_credentials = user.ensure_credentials_active()

    what_changed = ''
    if was_created:
        what_changed += 'User was created'
    else:
        what_changed += 'User already existed'

    if new_groups:
        what_changed += ' and was added to groups {}'.format(",".join(new_groups))

    what_changed += '.'

    if new_credentials:
        what_changed += ' Credentials {} were activated.'.format(",".join(new_credentials))

    return Deployed(credentials=user.credentials, message=what_changed)

def undeploy(user):
    was_removed = user.ensure_dosent_exist()

    what_changed = ''
    if was_removed:
        what_changed += 'User was removed.'
    else:
        what_changed += 'User didn\'t exist.'

    return NotDeployed(message=what_changed)

class User:
    def __init__(self, data):
        self.data = data

        if 'preferred_username' not in self.data['userinfo']:
            raise Question(
                name='username',
                text='You have not set a global username preference. Please enter your preferred username.'
            )

        self.service_user = backend('user')(
            name=self.data['userinfo']['preferred_username'],
            unique_id='{sub}@{iss}'.format(**self.data['userinfo']).replace(':', '')
        )

        self.entitlement = EduPersonEntitlement(self.data['userinfo']['eduperson_entitlement'])

        self.service_groups = [backend('group')(grp) for grp in [self.entitlement.group] + self.entitlement.subgroups]


    def ensure_exists(self):
        if self.service_user.exists():
            logging.debug('User for {sub}@{iss} already exists. Nothing to do.'.format(**self.data['userinfo']))
            return False

        elif self.service_user.name_taken():
            raise Question(
                name='username',
                text='Username {} already taken on this service. Please enter another one.'.format(
                    service_user.name
                )
            )
        else:
            logging.info('Creating user {preferred_username} for {sub}@{iss}'.format(**self.data['userinfo']))
            self.service_user.create()
            return True

    def ensure_dosent_exist(self):
        if self.service_user.exists():
            logging.info('Deleting user {preferred_username} of {sub}@{iss}'.format(**self.data['userinfo']))
            self.service_user.delete()
            return True
        else:
            logging.debug('No user for {sub}@{iss} didn\'t exists. Nothing to do.'.format(**self.data['userinfo']))
            return False

    def ensure_group_memberships(self):
        for group in filter(lambda grp: not grp.exists(), self.service_groups):
            logging.info("Creating group {}".format(group.name))
            group.create()

        self.service_user.mod(supplementary_groups=self.service_groups)
        return [grp.name for grp in self.service_groups]

    def ensure_credentials_active(self):
        # Currently, only SSH keys are supported
        self.service_user.install_ssh_keys([key['value'] for key in self.data['credentials']['ssh_key']])
        return ["SSH key {name}/{id}".format(**key) for key in self.data['credentials']['ssh_key']]

    @property
    def credentials(self):
        return {
            'username': self.service_user.name
        }

class EduPersonEntitlement:
    # This regex is not compatible with stdlib 're', we need 'regex'!
    # (because of repeated captures, see https://bugs.python.org/issue7132)
    re = regex.compile(
        r'urn:' +
           r'(?P<nid>[^:]+):(?P<delegated_namespace>[^:]+)' +     # Namespace-ID and delegated URN namespace
           r'(:(?P<subnamespace>[^:]+))*?' +                      # Sub-namespaces
        r':group:' +
           r'(?P<group>[^:]+)' +                                  # Root group
           r'(:(?P<subgroup>[^:]+))*?' +                          # Sub-groups
           r'(:role=(?P<role>.+))?' +                             # Role of the user in the deepest group
        r'#(?P<group_authority>.+)'                               # Authoritative soruce of the entitlement (URN)
    )

    def __init__(self, raw):
        match = self.re.fullmatch(raw)

        if not match:
            raise Failure(message="Failed to parse entitlements attribute")

        logging.debug("Parsing entitlement attribute: {}".format(match.capturesdict()))
        try:
            [self.namespace_id] = match.captures('nid')
            [self.delegated_namespace] = match.captures('delegated_namespace')
            self.subnamespaces = match.captures('subnamespace')

            [self.group] = match.captures('group')
            self.subgroups = match.captures('subgroup')
            [self.role] = match.captures('role') or [None]

            [self.group_authority] = match.captures('group_authority')
        except ValueError:
            raise Failure(message="Failed to parse entitlements attribute")


### User/Group management on the service
class UnixUser:
    def __init__(self, name, unique_id):
        self._name = make_shadow_compatible(name)
        self.unique_id = unique_id

    def exists(self):
        return bool(self.__passwd_entry)

    def name_taken(self):
        return self.name in [entry['login'] for entry in UnixUser.__all_passwd_entries().values()]

    def create(self):
        try:
            subprocess.run(['useradd', '--comment', self.unique_id, self.name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logging.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot create user')

    def delete(self):
        name = self.__passwd_entry['login']

        try:
            subprocess.run(['userdel', name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logging.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot delete user')

    def mod(self, supplementary_groups=None):
        options = []
        if supplementary_groups is not None:
            logging.debug("Adding user {} to groups {}".format(self.name, [g.name for g in supplementary_groups]))
            options += ['--groups', ",".join([g.name for g in supplementary_groups])]

        try:
            subprocess.run(['usermod'] + options + [self.name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logging.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot modify user')


    def install_ssh_keys(self, keys):
        try:
            self.__authorized_keys.parent.mkdir(parents=True, exist_ok=True)
            self.__authorized_keys.write_text("\n".join(keys))
        except IOError as e:
            logging.error(e)
            raise Failure(message='Could not write new ssh keys')

    def uninstall_ssh_keys(self, keys):
        try:
            self.__authorized_keys.unlink()
        except FileNotFoundError:
            pass

    @property
    def __authorized_keys(self):
        return Path(self.__passwd_entry['home'])/'.ssh'/'authorized_keys'


    @property
    def name(self):
        return self.__passwd_entry.get('login', self._name)

    @property
    def __passwd_entry(self):
        return UnixUser.__all_passwd_entries().get(self.unique_id, {})

    def __all_passwd_entries():
        PASSWD_PATH = Path('/')/'etc'/'passwd'
        PASSWD_FIELDS = ['login', 'pw', 'uid', 'gid', 'gecos', 'home', 'shell']
        ID_FIELD = 'gecos'

        try:
            raw = PASSWD_PATH.read_text()
        except IOError as e:
            logging.error(e)
            raise Failure(message='Could not get information about existing users on system')
        else:
            users = [dict(zip(PASSWD_FIELDS, line.split(':'))) for line in raw.strip().split('\n')]
            return {user[ID_FIELD]: user for user in users}

class UnixGroup:
    def __init__(self, name):
        self.name = make_shadow_compatible(name)

    def exists(self):
        return bool(self.__group_entry)

    def create(self):
        try:
            subprocess.run(['groupadd', self.name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logging.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot create user')

    def delete(self):
        # groupdel
        raise NotImplementedError('Do we even need this function?')

    def mod(self):
        # groupmod
        raise NotImplementedError('Do we even need this function?')

    @property
    def members(self):
        return self.__group_entry.get('name', [])

    @property
    def __group_entry(self):
        return UnixGroup.__all_group_entries().get(self.name, {})

    def __all_group_entries():
        GROUP_PATH = Path('/')/'etc'/'group'
        GROUP_FIELDS = ['name', 'password', 'gid', 'members']
        ID_FIELD = 'name'
        LIST_FIELD = 'members'

        try:
            raw = GROUP_PATH.read_text()
        except IOError as e:
            logging.error(e)
            raise Failure(message='Could not get information about existing users on system')
        else:
            users = [dict(zip(GROUP_FIELDS, line.split(':'))) for line in raw.strip().split('\n')]

            for user in users:
                user[LIST_FIELD] = user[LIST_FIELD].split(',')

            return {user[ID_FIELD]: user for user in users}


class BwIdmUser:
    def __init__(self, name, unique_id):
        raise NotImplementedError

    def exists(self):
        raise NotImplementedError

    def name_taken(self):
        raise NotImplementedError

    def create(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def mod(self, supplementary_groups=None):
        raise NotImplementedError

    def install_ssh_keys(self, keys):
        raise NotImplementedError

    def uninstall_ssh_keys(self, keys):
        raise NotImplementedError

    @property
    def name(self):
        raise NotImplementedError

class BwIdmGroup:
    def __init__(self, name):
        raise NotImplementedError

    def exists(self):
        raise NotImplementedError

    def create(self):
        raise NotImplementedError

    def delete(self):
        # groupdel
        raise NotImplementedError('Do we even need this function?')

    def mod(self):
        # groupmod
        raise NotImplementedError('Do we even need this function?')

    @property
    def members(self):
        raise NotImplementedError


### Data preprocessing
def apply_answers(data):
    for question, answer in data.get('answers', {}).items():
        if question == 'username':
            data['user']['userinfo']['preferred_username'] = answer

def sanitize(data):
    pass

def make_shadow_compatible(orig_word):
    # Sinvoll Umlaute kodieren
    word = orig_word.translate(str.maketrans({
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
        'ß': 'ss',
        '!': 'i', '$': 's',
        '*': 'x', '@': 'a',
    }))

    # Downcase
    word = word.lower()

    # Unicode -> Ascii
    word = unidecode(word)

    # Shadow will das Namen mit Kleinbuchstaben oder Underscore anfangen
    if regex.match(r'^[a-z_]', word):
        word = word
    else:
        word = '_' + word

    # Das ist der doofe part. Für die ganzen Sonderzeichen gibt es nicht wirklich
    # eine transliterierung in [-0-9_a-z], daher nehme ich einfach underscore,
    # was ggf. zu Kollisionen führen kann. Witzig: Shadow erlaubt '$' im namen,
    # aber nur *ganz* am Ende ...
    word = regex.sub(r'[^-0-9_a-z]', '_', word[:-1]) + regex.sub(r'[^-0-9_a-z$]', '_', word[-1])

    if word != orig_word:
        logging.warning("Name '{}' changed to '{}' for shadow compatibilty".format(orig_word, word))

    return word


### Globals
CONFIG = ConfigParser()
BACKENDS = {
    'local_unix': (UnixUser, UnixGroup),
    'bwidm': (BwIdmUser, BwIdmGroup),
}
def backend(what):
    conf = BACKENDS[CONFIG['ldf_adapter']['backend']]
    if what == 'user':
        return conf[0]
    elif what == 'group':
        return conf[1]
    else:
        raise ValueError


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG", "INFO"),
        format='%(asctime)s [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
    )

    files = []
    filename = os.environ.get("LDF_ADAPTER_CONFIG")
    if filename:
        files += [Path(filename)]
    files += [Path('ldf_adapter.conf'), Path.home()/'.config'/'ldf_adapter.conf', Path('/')/'etc'/'ldf_adapter.conf']
    CONFIG.read(files)

    data = json.load(sys.stdin)
    apply_answers(data)
    sanitize(data)

    logging.debug("Attempting to reach state '{state_target}' for user '{user[userinfo][name]}'".format(**data))

    try:
        result = main(data['state_target'], User(data['user'])).attributes
    except ExceptionalResult as result:
        result = result.attributes
        logging.debug("Reached state '{state}': {message}".format(**result))
        json.dump(result, sys.stdout)
    else:
        logging.debug("Reached state '{state}': {message}".format(**result))
        json.dump(result, sys.stdout)
