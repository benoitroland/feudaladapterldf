"""
Manages a user and groups via standard UNIX shadow-utils(8).
"""
# vim: foldmethod=indent : tw=100
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=logging-not-lazy, logging-format-interpolation
# pylint: disable=missing-docstring, too-few-public-methods

import subprocess
from subprocess import CalledProcessError
from pathlib import Path
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
        self.name = make_shadow_compatible(userinfo.username)
        self.unique_id = userinfo.unique_id
        self.ssh_keys = [key['value'] for key in userinfo.ssh_keys]
        self.primary_group = Group(userinfo.primary_group) 
        self.credentials = {}

    def exists(self):
        return bool(self.unique_id in [entry['gecos'] for entry in User.__all_passwd_entries().values()])

    def name_taken(self):
        return self.name in [entry['login'] for entry in User.__all_passwd_entries().values()]

    def get_username(self):
        gecos_user_map = {entry['gecos']: entry['login'] 
                for entry in User.__all_passwd_entries().values()}
        try:
            return gecos_user_map[self.unique_id]
        except KeyError:
            return None

    def create(self):
        try:
            # TODO this should consider self.primary_group
            shell = CONFIG['backend.local_unix'].get('shell', '/bin/sh')
            subprocess.run(['useradd', '--comment', self.unique_id, 
                            '-g', self.primary_group.name, 
                            '--shell', shell,
                           self.name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message='Cannot create user')

    def update(self):
        self.credentials['ssh_user'] = self.name
        self.credentials['ssh_host'] = CONFIG['backend.local_unix.login_info'].get('ssh_host', 'undefined')
        self.credentials['commandline'] = "ssh {}@{}".format(
            self.credentials['ssh_user'], self.credentials['ssh_host'])

    def delete(self):
        name = self.__passwd_entry['login']

        try:
            subprocess.run(['/usr/bin/pkill', '-u', name],
                           capture_output=True, check=True)
        except CalledProcessError:
            pass
        try:
            subprocess.run(['userdel', name],
                           capture_output=True, check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b'').decode('utf-8').strip()
            logger.error('Error executing \'{}\': {}'.format(' '.join(e.cmd), msg or "<no output>"))
            raise Failure(message=F'Cannot delete user: {msg}')

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

    def install_ssh_keys(self):
        try:
            self.__authorized_keys.parent.mkdir(parents=True, exist_ok=True)
            self.__authorized_keys.write_text("\n".join(self.ssh_keys))
        except IOError as e:
            logger.error(e)
            raise Failure(message='Could not write new ssh keys')

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
    def __passwd_entry(self):
        return User.__all_passwd_entries().get(self.unique_id, {})

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

class Group:
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
            raise Failure(message='Could not get information about existing users on system')
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

