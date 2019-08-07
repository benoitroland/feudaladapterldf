#!/usr/bin/env python3
#
# Author: Joshua Bachmeier <joshua.bachmeier@student.kit.edu>
#

import os
import sys
import subprocess
from subprocess import CalledProcessError
from pathlib import Path
import logging as logger
import json
from configparser import ConfigParser
import collections
from functools import lru_cache, reduce
import copy

import regex
from unidecode import unidecode
import requests
from urllib.parse import urljoin


### Result types
class Result:
    """A Result returned by the adapter to the feudalClient.

    Serialized to JSON as the final act of this script.
    """

    def __init__(self, state, message):
        """Called by subclasses, usually not directly.

        Arguments:
        state -- The state that was reached. One of 'deployed', 'not_deployed', 'failure' and 'rejected' (see subclasses below).
        message -- Displayed to the user in the feudalClient webinterface.
        """
        self.state = state
        self.message = message

    @property
    def attributes(self):
        return self.__dict__


## Sucessful
class Success(Result):
    """Indicates a successful result (i.e. user was deployed or undeployed)."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Deployed(Success):
    """Indicates that the user was successfully deployed to the service."""
    def __init__(self, credentials, **kwargs):
        """Initialises this Result with a state of 'deployed'.

        Arguments:
        credentials -- A dictionary displayed to the user in the feudalClient webinterface.
        **kwargs -- Any additional keyword arguments are passed to Success.__init__
        """
        super().__init__(state='deployed', **kwargs)
        self.credentials = credentials

class NotDeployed(Success):
    """Indicates that the user was successfully undeployed from the service."""
    def __init__(self, **kwargs):
        super().__init__(state='not_deployed', **kwargs)


## Exceptional (Error or Questionnaire)
class ExceptionalResult(Result, Exception):
    """Raise a subclass of this to abort and directly return this Result to the feudalClient"""
    pass

class Failure(ExceptionalResult):
    """Indicates a failure in attempting to deploy/undeploy the user.

    The previous state should be retained, but might also be inconsistent
    """
    def __init__(self, **kwargs):
        super().__init__(state='failed', **kwargs)

class Rejection(ExceptionalResult):
    """Indicates that the user is not allowed to access the requested resource.

    A reason for this might be an insufficient assurance level.
    """
    def __init__(self, **kwargs):
        super().__init__(state='rejected', **kwargs)

class Questionnaire(ExceptionalResult):
    """Additional information is needed to reach the desired state.

    Usually, this is raised during deployment to get additional
    information.  The feudalClient then calls this script again with
    an additional object under the key 'answers' in the
    input dictionary. This can be accessed from within the UserInfo
    class (see below).

    Can be used to ask multiple questions at once.

    Arguments:
    questions -- A Dictionary of `{name: text, ...}` questions. The text is the question
                 displayed to the user in the feudalClient webinterface. The answer
                 submitted by the user can then be found under the key `name` in the
                 answers dictionary.
    **kwargs -- Any additional keyword arguments ar passed to ExceptionalResult.__init__
    """
    def __init__(self, questions, **kwargs):
         super().__init__(state='questionnaire', message='There are unanswered questions.', **kwargs)
         self.questionnaire = questions

class Question(Questionnaire):
    """Convenience class to ask a single question."""
    def __init__(self, name, text, **kwargs):
        """See Questionaire.__init__ for details.

        Arguments:
        name -- The name of the question
        text -- Displayed to the user
        **kwargs -- Any additional keyword arguments are passed to Questionaire.__init__
        """
        super().__init__(questions={name: text}, **kwargs)

def raise_question(*args, **kwarsg):
    """Convenice function needed in places where an expression is required.

    E.g: `userinfo.get_value() or raise Question(...)` is not valid,
    but `userinfo.get_value() or raise_question(...)` is.
    """
    raise Question(*args, **kwargs)


### Core logic
def main(state_target, user):
    """Attempt to put the user into the desired state on the configured service.

    Arguments:
    state_target -- The desired state. One of 'deployed' and 'not_deployed'.
    user -- The user to be deployed/undeployed (type: User)
    """
    if not user.data.assurance.is_accepted():
        raise Rejection(message="Your assurance level is insufficient to access this resource")

    if state_target == 'deployed':
        return user.deploy()
    elif state_target == 'not_deployed':
        return user.undeploy()
    else:
        raise Failure(message="[BUG] Invalid target state: {}".format(state_target))

class User:
    """Represents a user, abstracting from the concrete service.

    An abstract User is backed by a service_user and is associated with a set of groups (backed by
    service_groups).

    A user is usually identified on the service not by a username but by `self.data.unique_id` (see
    __init__ for details).
    """
    def __init__(self, data):
        """
        Arguments:
        data -- Information about the user (type: UserInfo)

        Relevant config:
        ldf_adapter.backend -- The name of the backend. See function the `backend` for possible values
        """
        self.data = data
        self.service_user = backend('user')(data)
        self.service_groups = [backend('group')(grp) for grp in data.groups]

    def deploy(self):
        """Deploy the user.

        Ensure that the user exists, is a member in the right groups (and only in those groups)
        and has the correct credentials installed.

        Return a Deployed result, with a message describing what was done.
        """
        was_created = self.ensure_exists()
        new_groups = self.ensure_group_memberships()
        new_credentials = self.ensure_credentials_active()

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

        return Deployed(credentials=self.credentials, message=what_changed)

    def undeploy(self):
        """Ensure that the user dosen't exist.

        Return a NotDeployed result with a message saying if the user previously existed.
        """
        was_removed = self.ensure_dosent_exist()

        what_changed = ''
        if was_removed:
            what_changed += 'User was removed.'
        else:
            what_changed += 'User didn\'t exist.'

        return NotDeployed(message=what_changed)

    def ensure_exists(self):
        """Ensure that the user exists on the service.

        If the username is already taken on the service, raise a questionaire for a new one. See
        UserInfo.username for details.

        Also ensure that all info about the user is up to date on the service. This is done
        independently of creating the user, so that the user is updated even if they already existed.

        Return True, if the user didn't exist before.
        """
        if self.service_user.exists():
            logger.debug('User for {unique_id} already exists. Nothing to do.'.format(**self.data))
            created = False

        elif self.service_user.name_taken():
            raise Question(
                name='username',
                text='Username {} already taken on this service. Please enter another one.'.format(
                    self.service_user.name
                )
            )
        else:
            logger.info('Creating user {username} for {unique_id}'.format(**self.data))
            self.service_user.create()
            created = True

        self.service_user.update()
        return created

    def ensure_dosent_exist(self):
        """Ensure that the user doesn't exist.

        Before deleting them, uninstall all SSH keys, to be sure that they are really gone.

        Return True, if the user existed before.
        """
        if self.service_user.exists():
            logger.info('Deleting user {username} of {unique_id}'.format(**self.data))
            self.service_user.uninstall_ssh_keys()
            self.service_user.delete()
            return True
        else:
            logger.debug('No user for {unique_id} did exist. Nothing to do.'.format(**self.data))
            return False

    def ensure_group_memberships(self):
        """Ensure that the user is a member of all the groups in self.service_groups.

        Create the groups on the service, if necessary.

        Return the names of all groups the user is now a member of.
        """
        for group in filter(lambda grp: not grp.exists(), self.service_groups):
            logger.info("Creating group {}".format(group.name))
            group.create()

        self.service_user.mod(supplementary_groups=self.service_groups)
        return [grp.name for grp in self.service_groups]

    def ensure_credentials_active(self):
        """Install all SSH Keys on the service.

        Return a list of the names/ids of all the keys now active.
        """
        self.service_user.install_ssh_keys([key['value'] for key in self.data.ssh_keys])
        return ["ssh_key:{name}/{id}".format(**key) for key in self.data.ssh_keys]

    @property
    def credentials(self):
        """The Credentials displayed to the user.

        Simply merges all the credentials provided by the service_user with those configured for
        the backend in the config file.

        See Deployed.__init__ for details on how this value is used.

        Relevant config:
        ldf_adapter.backend -- The backend to be used
        backend.{}.login_info -- Everything in this section is merged into the credentials dictionary.
        """
        return {
            **self.service_user.credentials,
            **CONFIG['backend.{}.login_info'.format(CONFIG['ldf_adapter']['backend'])]
        }


### User/Group management on the service
def make_shadow_compatible(orig_word):
    # Sinvoll Umlaute kodieren
    word = orig_word.translate(str.maketrans({
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
        'ß': 'ss',
        '!': 'i', '$': 's',
        '*': 'x', '@': '_at_',
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
        logger.warning("Name '{}' changed to '{}' for shadow compatibilty".format(orig_word, word))

    return word

class UnixUser:
    def __init__(self, userinfo):
        self._name = make_shadow_compatible(userinfo.username)
        self.unique_id = userinfo.unique_id

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
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot create user')

    def update(self):
        pass

    def delete(self):
        name = self.__passwd_entry['login']

        try:
            subprocess.run(['userdel', name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot delete user')

    def mod(self, supplementary_groups=None):
        options = []
        if supplementary_groups is not None:
            logger.debug("Adding user {} to groups {}".format(self.name, [g.name for g in supplementary_groups]))
            options += ['--groups', ",".join([g.name for g in supplementary_groups])]

        try:
            subprocess.run(['usermod'] + options + [self.name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot modify user')


    def install_ssh_keys(self, keys):
        try:
            self.__authorized_keys.parent.mkdir(parents=True, exist_ok=True)
            self.__authorized_keys.write_text("\n".join(keys))
        except IOError as e:
            logger.error(e)
            raise Failure(message='Could not write new ssh keys')

    def uninstall_ssh_keys(self):
        try:
            self.__authorized_keys.unlink()
        except FileNotFoundError:
            pass

    @property
    def __authorized_keys(self):
        return Path(self.__passwd_entry['home'])/'.ssh'/'authorized_keys'


    @property
    def credentials(self):
        return {
            'login_name': self.__passwd_entry.get('login', self._name)
        }

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
            logger.error(e)
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
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot create user')

    def delete(self):
        # groupdel
        raise NotImplementedError('Do we even need this function?')

    def mod(self):
        # groupmod
        raise NotImplementedError('Do we even need this function?')

    @property
    def members(self):
        return self.__group_entry.get('members', [])

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
            logger.error(e)
            raise Failure(message='Could not get information about existing users on system')
        else:
            users = [dict(zip(GROUP_FIELDS, line.split(':'))) for line in raw.strip().split('\n')]

            for user in users:
                user[LIST_FIELD] = user[LIST_FIELD].split(',')

            return {user[ID_FIELD]: user for user in users}


class BwIdmUser:
    ATTR_USERNAME = 'urn:oid:0.9.2342.19200300.100.1.1'
    ATTR_ORG_ID = 'http://bwidm.de/bwidmOrgId'
    VALUE_USER_ACTIVE = 'ACTIVE'
    VALUE_USER_INACTIVE = 'ON_HOLD'

    def __init__(self, userinfo):
        self.info = userinfo
        self.credentials = {}

    def exists(self):
        return self._exists() and self._is_active()

    def _exists(self):
        exists = b'no such user' not in self.reg_info(json=False, fail=False)
        logger.debug('User {} {} on service BWIDM'.format(
            self.info.unique_id, 'exists' if exists else "doesn't exist"
        ))
        return exists

    def _is_active(self):
        status = self.reg_info()['userStatus']
        logger.debug('User {} is {} on service BWIDM'.format(
            self.info.unique_id, status
        ))
        return status == self.VALUE_USER_ACTIVE

    def name_taken(self):
        users_with_name = BWIDM.get(
            'external-user', 'find',
            'attribute', self.ATTR_USERNAME, self.info.username
        ).json()

        other_users_with_name = [user for user in users_with_name if user['externalId'] != self.info.unique_id]
        if len(other_users_with_name) < len(users_with_name):
            logger.debug("Username '{}' is reserved for us".format(self.info.username))

        return bool(other_users_with_name)

    def create(self):
        if self._exists() and not self._is_active():
            logger.info("Activating user {unique_id}".format(**self.info))
            BWIDM.get('external-user', 'activate', 'externalId', self.info.unique_id)
        else:
            logger.info("Creating user {unique_id}".format(**self.info))
            BWIDM.post('external-user', 'create', json={
                'externalId': self.info.unique_id
            })

    def update(self):
        self.external_user_update({
            'externalId': self.info.unique_id,
            'eppn': self.info.unique_id,
            'email': self.info.email,
            'givenName': self.info.given_name,
            'surName': self.info.family_name,
            'primaryGroup': {
                'id': CONFIG['backend.bwidm'].getint('primary_group_id')
            },
            'attributeStore': {
                self.ATTR_USERNAME: self.info.username,
                self.ATTR_ORG_ID: CONFIG['backend.bwidm']['org_id'],
            }
        })

        rsp = BWIDM.get('external-reg', 'register',
                        'externalId', self.info.unique_id,
                        'ssn', CONFIG['backend.bwidm.service']['name'])

        self.credentials['login_name'] = rsp.json()['registryValues']['localUid']

    def delete(self):
        BWIDM.get('external-user', 'deactivate', 'externalId', self.info.unique_id)

    def mod(self, supplementary_groups=None):
        reg_info = self.reg_info()

        if supplementary_groups is not None:
            current_groups = (grp for grp in reg_info['secondaryGroups'])
            new_groups = (grp.reg_info(short=True) for grp in supplementary_groups)

            # Remove user from groups he should not be a member of
            to_be_removed_from = [g for g in current_groups
                                  if g['id'] not in (ng['id'] for ng in new_groups)]

            # Only add user to groups she is not already a member of
            to_be_added_to = [g for g in new_groups
                              if g['id'] not in (cg['id'] for cg in current_groups)]

            if to_be_removed_from:
                logger.info('Remove user {} from groups {}'.format(
                    self.info.username, ",".join(g['name'] for g in to_be_removed_from)))
            for grp in to_be_removed_from:
                BWIDM.get('group-admin', 'remove', 'groupId', grp['id'], 'userId', reg_info['id'])

            if to_be_added_to:
                logger.info('Add user {} to groups {}'.format(
                    self.info.username, ",".join(g['name'] for g in to_be_added_to)))
            for grp in to_be_added_to:
                BWIDM.get('group-admin', 'add', 'groupId', grp['id'], 'userId', reg_info['id'])

    def install_ssh_keys(self, keys):
        self.external_user_update({
            'externalId': self.info.unique_id,
            'genericStore': {
                **self.reg_info()['genericStore'],
                'ssh_key': json.dumps(self.info.ssh_keys)
            }
        })

    def uninstall_ssh_keys(self):
        self.external_user_update({
            'externalId': self.info.unique_id,
            'genericStore': {'ssh_key': None}
        })

    # {..., k: val, ...} means `state[k] = val`
    # {..., k: None, ...} means `del state[k]` or `state[k]=None`
    # {..., k: {}, ...} means no change to k
    # {..., k: val={...}, ...} means `state[k]=merge state[k] with val`
    #
    # This is applied recursivly.
    def external_user_update(self, state_updates):
        current_state = self.reg_info()
        new_state = dictmerge(current_state, state_updates, verbose=True)

        for k in list(new_state):
            if new_state[k] is None:
                new_state[k] = {}

        BWIDM.post('external-user', 'update', json=new_state)

    def reg_info(self, json=True, **kwargs):
        rsp = BWIDM.get('external-user', 'find', 'externalId', self.info.unique_id, **kwargs)
        return rsp.json() if json else rsp.content

class BwIdmGroup:
    def __init__(self, name):
        self.name = name

    def exists(self):
        return b'no such group' not in BWIDM.get('group-admin', 'find', 'name', self.name, fail=False).content

    def create(self):
        BWIDM.get('group-admin', 'create', CONFIG['backend.bwidm.service']['name'], self.name)

    def delete(self):
        # groupdel
        raise NotImplementedError('Do we even need this function?')

    def mod(self):
        # groupmod
        raise NotImplementedError('Do we even need this function?')

    def reg_info(self, json=True, short=False, **kwargs):
        rsp = BWIDM.get('group-admin', 'find' if short else 'find-detail', 'name', self.name, **kwargs)
        return rsp.json() if json else rsp.content

    @property
    def members(self):
        raise NotImplementedError('Do we even need this function?')

class BwIdmConnection:
    def __init__(self, config=None):
        self.session = requests.Session()
        if config:
            self.session.auth = (
                config['backend.bwidm.auth']['http_user'],
                config['backend.bwidm.auth']['http_pass']
            )

    def get(self, *url_fragments, **kwargs):
        return self._request('GET', url_fragments, **kwargs)

    def post(self, *url_fragments, **kwargs):
        return self._request('POST', url_fragments, **kwargs)

    def _request(self, method, url_fragments, **kwargs):
        fail = kwargs.pop('fail', True)

        url_fragments = map(str, url_fragments)
        url_fragments = map(lambda frag: requests.utils.quote(frag, safe=''), url_fragments)
        url = reduce(lambda acc, frag: urljoin(acc, frag) if acc.endswith('/') else urljoin(acc+'/', frag),
                     url_fragments,
                     CONFIG['backend.bwidm']['url'])

        req = requests.Request(method, url, **kwargs)
        rsp = self.session.send(self.session.prepare_request(req))

        if fail:
            if not rsp.ok:
                logger.error("Server responded with: {}".format(rsp.content.decode('utf-8')))
            rsp.raise_for_status()

        return rsp


### Data preprocessing
class UserInfo(collections.Mapping):
    def __init__(self, data):
        self.userinfo = data['user']['userinfo']
        self.answers = data.get('answers', {})
        self.credentials = data['user'].get('credentials', {})

    @property
    @lru_cache(maxsize=None)
    def unique_id(self, allow_question=True):
        return '{sub}@{iss}'.format(
            sub=self._sub_masked_for_bwidm_eppn(),
            iss=self._iss_masked_for_bwidm_eppn()
        )

    def _sub_masked_for_bwidm_eppn(self):
        sub = regex.sub('[^a-zA-Z0-9_!#$%&*+/=?{|}~^.-]', '-', self.userinfo['sub'])

        if sub != self.userinfo['sub']:
            logger.warning("Subject '{}' changed to '{}' for BWIDM compatibilty".format(
                self.userinfo['sub'], sub))

        return sub

    def _iss_masked_for_bwidm_eppn(self):
        stripped_iss = regex.sub('^https?://', '', self.userinfo['iss'])
        iss = regex.sub('[^a-zA-Z0-9.-]', '-', stripped_iss)

        # We don't consider stripping the http[s]-prefix a change, since we always do that anyway,
        # and there shouldn't be two different issuers `http://example.org' and `https://example.org'.
        if iss != stripped_iss:
            logger.warning("Issuer '{}' changed to '{}' for BWIDM compatibilty".format(
                stripped_iss, iss))

        return iss

    @property
    @lru_cache(maxsize=None)
    def username(self, allow_question=True):
        return self.value_or_ask(
            self.userinfo.get('preferred_username'), 'username',
            'You have not set a global username preference. Please enter your preferred username.',
            allow_question
        )

    @property
    @lru_cache(maxsize=None)
    def email(self, allow_question=True):
        return self.userinfo['email']

    @property
    @lru_cache(maxsize=None)
    def given_name(self, allow_question=True):
        return (self.userinfo.get('given_name')
                or ' '.join(self.userinfo['name'].split(' ')[:-1]))

    @property
    @lru_cache(maxsize=None)
    def family_name(self, allow_question=True):
        return (self.userinfo.get('family_name')
                or self.userinfo.get('sn')
                or self.userinfo['name'].split(' ')[-1])

    @property
    @lru_cache(maxsize=None)
    def full_name(self, allow_question=True):
        return (self.userinfo.get('name')
                or ' '.join(filter(None, [given_name, family_name])))

    @property
    @lru_cache(maxsize=None)
    def ssh_keys(self, allow_question=True):
        return self.credentials.get('ssh_key', [])

    @property
    @lru_cache(maxsize=None)
    def entitlement(self, allow_question=True):
        return EduPersonEntitlement(self.userinfo['eduperson_entitlement'])

    @property
    @lru_cache(maxsize=None)
    def groups(self, allow_question=True):
        return [self._group_masked_for_bwidm(grp) for grp in [self.entitlement.group] + self.entitlement.subgroups]

    def _group_masked_for_bwidm(self, orig_grp):
        grp = orig_grp

        # First char has to be [a-z]
        grp = regex.sub('^[A-Z]', lambda m: m.group(0).lower(), grp)
        grp = regex.sub('^[-_]*', '', grp)
        grp = regex.sub('^0', 'zero_', grp)
        grp = regex.sub('^1', 'one_', grp)
        grp = regex.sub('^2', 'two_', grp)
        grp = regex.sub('^3', 'three_', grp)
        grp = regex.sub('^4', 'four_', grp)
        grp = regex.sub('^5', 'five_', grp)
        grp = regex.sub('^6', 'six_', grp)
        grp = regex.sub('^7', 'seven_', grp)
        grp = regex.sub('^8', 'eight_', grp)
        grp = regex.sub('^9', 'nine_', grp)
        grp = regex.sub('^[^a-z]', 'bwidm_\0', grp)

        # camelCase to snake_case
        grp = regex.sub('([a-z])([A-Z])', lambda m: '{}_{}'.format(m.group(1), m.group(2).lower()), grp)

        # Catch remaining chars
        grp = regex.sub('[^a-z0-9-_]', '-', grp)

        if grp != orig_grp:
            logger.warning("Group name '{}' changed to '{}' for BWIDM compatibilty".format(orig_grp, grp))

        return grp

    @property
    @lru_cache(maxsize=None)
    def assurance(self, allow_question=True):
        return EduPersonAssurance(self.userinfo['eduperson_assurance'])

    def value_or_ask(self, value, answer_name, question_text, allow_question):
        return (self.answers.get(answer_name)
                or value
                or (allow_question and raise_question(
                    name=answer_name,
                    text=question_text
                )))


    def __str__(self):
        attrs = ("{} = {}".format(k, getattr(UserInfo, k).fget(self, allow_question=False)) for k in iter(self))

        return "<UserInfo\n{}\n>".format("\n".join("\t{}".format(attr) for attr in attrs))

    def __getitem__(self, key):
        return getattr(self, key, lambda: (_ for _ in ()).throw(KeyError(key)))

    def __iter__(self):
        return (k for k in dir(UserInfo) if type(getattr(UserInfo, k)) is property)

    def __len__(self, allow_questions=True):
        sum(1 for _ in filter(lambda k: type(getattr(UserInfo, k)) is property, dir(UserInfo)))

    def __hash__(self):
        return id(self) # Good enough for lru_cache

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

        logger.debug("Parsing entitlement attribute: {}".format(match.capturesdict()))
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

    def __repr__(self):
        return ((
            'urn:{namespace_id}:{delegated_namespace}{subnamespaces}' +
            ':group:{group}{subgroups}{role}' +
            '#{group_authority}'
        ).format(**{
            **self.__dict__, **{
                'subnamespaces': ''.join([':{}'.format(ns) for ns in self.subnamespaces]),
                'subgroups': ''.join([':{}'.format(grp) for grp in self.subgroups]),
                'role': ':role={}'.format(self.role) if self.role else ''
        }}))

    def __str__(self):
        return ((
            '<EduPersonEntitlement' +
            ' namespace={namespace_id}:{delegated_namespace}{subnamespaces}' +
            ' group={group}{subgroups}' +
            '{role}' +
            ' auth={group_authority}>'
        ).format(**{
            **self.__dict__, **{
                'subnamespaces': ''.join([',{}'.format(ns) for ns in self.subnamespaces]),
                'subgroups': ''.join([',{}'.format(grp) for grp in self.subgroups]),
                'role': ' role={}'.format(self.role) if self.role else ''
        }}))

class EduPersonAssurance:
    def __init__(self, level):
        self.level = level

    def is_accepted(self):
        try:
            accepted_levels = [lvl.strip() for lvl in CONFIG['assurance']['accepted_levels'].split(',')]
        except KeyError:
            accepted_levels = None

        accepted_level_regex = regex.compile(CONFIG['assurance'].get('accepted_level_regex', '.*'))

        accepted = True

        if not self.level:
            logger.warning("No assurance level provided. Rejecting.")
            accepted = False

        if accepted_levels is not None and self.level not in accepted_levels:
            logger.warning("Assurance level '{}' is not one of {}. Rejecting.".format(self.level, accepted_levels))
            accepted = False

        if not accepted_level_regex.match(self.level):
            logger.warning("Assurance level '{}' does not match {}. Rejecting.".format(self.level, accepted_level_regex))
            accepted = False

        return accepted

    def __str__(self):
        return ('<EduPersonAssurance level={}>'.format(self.level))


### Utils
def dictdiff(old, new):
    def _dictdiff(old, new):
        for k in new:
            if isinstance(new.get(k), dict) and isinstance(old.get(k), dict):
                subdiff = dict(_dictdiff(old[k], new[k]))
                if subdiff:
                    yield (k, subdiff)
            elif old.get(k) != new.get(k):
                yield (k, (old.get(k), new.get(k)))

    return dict(_dictdiff(old, new))

def log_dictdiff(diff, prefix=''):
    for k,v in diff.items():
        if isinstance(v, dict):
            log_dictdiff(v, "{}/".format(k))
        else:
            (old, new) = v
            if old:
                logger.info("Updating {}{} from '{}' to '{}'".format(prefix, k, old, new))
            else:
                logger.info("Setting {}{} to '{}'".format(prefix, k, new))

def dictmerge(lhs, rhs, verbose=False):
    res = copy.deepcopy(lhs)
    for k in rhs:
        if isinstance(rhs[k], dict) and k in res and isinstance(res[k], dict):
            res[k] = dictmerge(res[k], rhs[k])
        else:
            res[k] = rhs[k]

    if verbose:
        log_dictdiff(dictdiff(lhs, res))

    return res


### Globals
logger.basicConfig(
    level=os.environ.get("LOG", "INFO"),
    format='%(asctime)s [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
)

CONFIG = ConfigParser()
files = []
filename = os.environ.get("LDF_ADAPTER_CONFIG")
if filename:
    files += [Path(filename)]
files += [Path('ldf_adapter.conf'), Path.home()/'.config'/'ldf_adapter.conf', Path('/')/'etc'/'ldf_adapter.conf']
CONFIG.read(files)

BWIDM = BwIdmConnection(CONFIG)

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
    data = json.load(sys.stdin)
    info = UserInfo(data)
    logger.debug("Using {}".format(info))

    logger.debug("Attempting to reach state '{state_target}' for user '{full_name}'".format(**data, **info))

    try:
        result = main(data['state_target'], User(info)).attributes
    except ExceptionalResult as result:
        result = result.attributes
        logger.debug("Reached state '{state}': {message}".format(**result))
        json.dump(result, sys.stdout)
    else:
        logger.debug("Reached state '{state}': {message}".format(**result))
        json.dump(result, sys.stdout)
