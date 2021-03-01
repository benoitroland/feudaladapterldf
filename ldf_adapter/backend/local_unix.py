"""
Manages a user and groups via standard UNIX shadow-utils(8).
"""
# vim: foldmethod=indent : tw=100
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=logging-fstring-interpolation, logging-not-lazy, logging-format-interpolation
# pylint: disable=raise-missing-from, missing-docstring, too-few-public-methods

import sys
import subprocess
from subprocess import CalledProcessError
from pathlib import Path
from os import chown
from datetime import date, datetime
import json
import logging

import regex
from unidecode import unidecode

from ..config import CONFIG
from ..results import Failure

logger = logging.getLogger(__name__)

class User:
    def __init__(self, userinfo):
        """
        Arguments:
        userinfo -- Only these attributes are used:
                `username` (which is passed through `make_shadow_compatible`),
                `primary_group`
                `unique_id`  stored in gecos, used to find the user
                `ssh_keys`
        """
        self.unique_id = userinfo.unique_id
        logger.debug(F"backend processing: {userinfo.unique_id}")
        if self.exists():
            logger.debug(F"This user does actually exist. The name is: {self.get_username()}")
            self.set_username(self.get_username())
        else:
            self.set_username(userinfo.username)

        self.ssh_keys = [key['value'] for key in userinfo.ssh_keys]
        self.primary_group = Group(userinfo.primary_group)
        self.credentials = {}

    def exists(self):
        """Check wheter a user (identified by the unique_id) exists"""
        # x = bool(self.unique_id in [entry['gecos'] for entry in User.__all_passwd_entries('gecos').values()])
        # logger.debug(F"user exists: {x}")
        return bool(self.unique_id in [entry['gecos'] for entry in User.__all_passwd_entries('gecos').values()])

    def is_rejected(self):
        """Optional, only if the backend supports it.
        Inform the user whether a user was rejected"""
        return False
    
    def is_suspended(self):
        """Optional, only if the backend supports it.
        Inform the user whether a user was suspended (e.g. due to a security incident)"""
        if self.exists():
            options = ['-i', '-l']
            try:
                result = subprocess.run(['chage'] + options + [self.name],
                                        capture_output=True, check=True)
            except CalledProcessError as e:
                msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
                logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
                raise Failure(message=F"Cannot get info for user: {msg or '<no output>'}")
            try:
                pattern = regex.compile(r'Account expires\s+: (.*)')
                match = pattern.search(result.stdout.decode("utf-8"))
                if match:
                    expiration_date = match.group(1)
                    if expiration_date == 'never':
                        return False
                    expiration_date_sec = int(
                        datetime.fromisoformat(expiration_date).strftime('%s'))
                    if expiration_date_sec - datetime.now().timestamp() <= 0:
                        return True
            except Exception as e:
                logger.error(e)
                raise Failure(message=F"Could not get: {e or '<no output>'}")
        return False

    def is_pending(self):
        """Optional, only if the backend supports it.
        Inform the user whether his creation is pending"""
        return False

    def is_limited(self):
        """Optional, only if the backend supports it.
        Inform the user whether a user has limited access"""
        # if shell is nologin
        try:
            shell = self.__passwd_entry.get('shell', None)
            return (
                shell == '/sbin/nologin' or
                shell == '/usr/bin/nologin' or
                shell == '/bin/nologin'
                )
        except KeyError:
            return False

    def name_taken(self, name):
        """Check if a username is already taken by *another* user"""
        name = make_shadow_compatible(name)
        taken = name in [entry['login'] for entry in User.__all_passwd_entries('login').values()]
        logger.debug(F"name_taken: {taken}")
        return taken and name != self.get_username()

    def get_username(self):
        """Return username based on unique_id"""
        gecos_user_map = {entry['gecos']: entry['login']
                for entry in User.__all_passwd_entries('gecos').values()}
        try:
            return User.__all_passwd_entries('gecos')[self.unique_id]['login']
        except KeyError:
            return None

    def set_username(self, username):
        """Set local username on the service."""
        self.name = make_shadow_compatible(username)

    def create(self):
        logger.debug(F"creating user: {self.name} - {self.unique_id} ")
        try:
            shell = CONFIG['backend.local_unix'].get('shell', '/bin/sh')
            subprocess.run(['useradd', '--comment', self.unique_id,
                            '-g', self.primary_group.name,
                            '--shell', shell,
                            '-m',
                           self.name],
                           check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message=F"Cannot create user ({msg or '<no output>'})")

    def update(self):
        self.credentials['ssh_user'] = self.name
        self.credentials['ssh_host'] = CONFIG['backend.local_unix.login_info'].get('ssh_host', 'undefined')
        self.credentials['commandline'] = "ssh {}@{}".format(
            self.credentials['ssh_user'], self.credentials['ssh_host'])

    def delete(self):
        name = self.__passwd_entry['login']

        try:
            subprocess.run(['/usr/bin/pkill', '-u', name],
                           check=True)
        except CalledProcessError:
            pass
        try:
            subprocess.run(['userdel', name],
                           check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message=F"Cannot delete user: {msg or '<no output>'}")

    def mod(self, supplementary_groups=None):
        options = []
        if supplementary_groups is not None:
            logger.debug("Adding user {} to groups {}".format(self.name, [g.name for g in supplementary_groups]))
            options += ['--groups', ",".join([g.name for g in supplementary_groups])]

        try:
            subprocess.run(['usermod'] + options + [self.name],
                           check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message=F"Cannot modify user: {msg or '<no output>'}")

    def __expire(self, expiration_date=datetime.today().strftime("%Y-%m-%d")):
        options = ['-E', expiration_date]
        try:
            subprocess.run(['chage'] + options + [self.name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message=F"Cannot set expiration date for user: {msg or '<no output>'}")

    def suspend(self):
        self.__expire(datetime.today().strftime("%Y-%m-%d"))

    def resume(self):
        self.__expire('-1')

    def __set_shell(self, shell):
        try:
            subprocess.run(['usermod', '-s', shell, self.name], check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message=F"Cannot modify user: {msg or '<no output>'}")

    def limit(self):
        self.__set_shell('/sbin/nologin')

    def unlimit(self):
        shell = CONFIG['backend.local_unix'].get('shell', '/bin/sh')
        self.__set_shell(shell)

    def install_ssh_keys(self):
        try:
            self.__authorized_keys.parent.mkdir(parents=True, exist_ok=True)
            self.__authorized_keys.parent.chmod(0o700)
            chown(self.__authorized_keys.parent, self.__uid, self.__gid)

            self.__authorized_keys.write_text("\n".join(self.ssh_keys))
            self.__authorized_keys.chmod(0o600)
            chown(self.__authorized_keys, self.__uid, self.__gid)
        except IOError as e:
            logger.error(e)
            raise Failure(message=F"Could not write new ssh keys: {e or '<no output>'}")
        except Exception as e:
            logger.error(e)
            raise Failure(message=F"Cannot change owner or permissions: {e or '<no output>'}")

    def uninstall_ssh_keys(self):
        """Remove any SSH keys stored in the users .authorized_keys file."""
        try:
            self.__authorized_keys.unlink()
        except FileNotFoundError:
            pass

    @property
    def __authorized_keys(self):
        return Path(self.__passwd_entry['home'])/'.ssh'/'authorized_keys'

    @property
    def __uid(self):
        try:
            return int(self.__passwd_entry.get('uid', None))
        except TypeError as e:
            logger.error(e)
            raise Failure(message=F"Could not get uid: {e or '<no output>'}")

    @property
    def __gid(self):
        try:
            return int(self.__passwd_entry.get('gid', None))
        except TypeError as e:
            logger.error(e)
            raise Failure(message=F"Could not get gid: {e or '<no output>'}")

    @property
    def __passwd_entry(self):
        return User.__all_passwd_entries('gecos').get(self.unique_id, {})

    def __all_passwd_entries(ID_FIELD='gecos'):
        PASSWD_PATH = Path('/')/'etc'/'passwd'
        PASSWD_FIELDS = ['login', 'pw', 'uid', 'gid', 'gecos', 'home', 'shell']

        try:
            raw = PASSWD_PATH.read_text()
        except IOError as e:
            logger.error(e)
            raise Failure(message=F"Could not get information about existing users on system: {e or '<no output>'}")
        else:
            users = [dict(zip(PASSWD_FIELDS, line.split(':'))) for line in raw.strip().split('\n')]

            # import json
            # thedata={user[ID_FIELD]: user for user in users}
            # str_str = json.dumps(thedata, sort_keys=True, indent=4, separators=(',', ': '))
            # logger.debug(str_str)
            # x = {user[ID_FIELD]: user for user in users}
            # logger.debug(F"whattttt: {x}")
            return {user[ID_FIELD]: user for user in users}

class Group:
    def __init__(self, name):
        self.name = make_shadow_compatible(name)

    def exists(self):
        return bool(self.__group_entry)

    def create(self):
        try:
            subprocess.run(['groupadd', self.name],
                           check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message=F"Cannot create group: {msg or '<no output>'}")

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
        return Group.__all_group_entries().get(self.name, {})

    def __all_group_entries():
        GROUP_PATH = Path('/')/'etc'/'group'
        GROUP_FIELDS = ['name', 'password', 'gid', 'members']
        ID_FIELD = 'name'
        LIST_FIELD = 'members'

        try:
            raw = GROUP_PATH.read_text()
        except IOError as e:
            logger.error(e)
            raise Failure(message=F"Could not get information about existing users on system: {e or '<no output>'}")
        else:
            users = [dict(zip(GROUP_FIELDS, line.split(':'))) for line in raw.strip().split('\n')]

            for user in users:
                user[LIST_FIELD] = user[LIST_FIELD].split(',')

            return {user[ID_FIELD]: user for user in users}


def make_shadow_compatible(orig_word):
    """Ensure that orig_word is a valid user/group name for standard shadow utils.

    While this could in theory be achived by simply substituting all non-allowed chars with a valid
    one, we try to translitare sensibly, so that usernames look nicer and to avoid collisions. See
    inline comments for further details.

    Any change made to the word is logged with level WARNING.

    """
    if orig_word is None:
        return None
    # Encode German Umlauts
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


    # usernames and group names can only be 32 characters long.
    # My fix is to remove characters a) after the first '_' if there is one.
    #                                b) from the beginning if there is none
    # Also adds two dots as an indicator for where the shortening took place

    excess_chars = len(word) - 32
    if excess_chars > 0:

        if len(word.split('_')) == 1: # no '_' found:
            word = '..' + word[excess_chars+2:] 
            logger.warning(F"shortened {orig_word} to {word}")

        if len(word.split('_')) > 1: # at least one '_' found:
            fragments = word.split('_')
            if len(fragments[1]) > excess_chars: # we're fine, we can cut excess chars from fragments alone
                fragments[1]=".."+fragments[1][excess_chars+2:]
                word = '_'.join(fragments)
            else:
                logger.error(F"User or group name is too long")
                raise(ValueError)
            logger.warning(F"shortened {orig_word} to {word}")

    if word != orig_word:
        logger.warning("Name '{}' changed to '{}' for shadow compatibilty".format(orig_word, word))

    return word
