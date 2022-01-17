"""LDAP backend for pre-created accounts.
It"s in the proof-of-concept state.
"""


import logging
from ldap3 import Server, Connection, ALL, BASE, MODIFY_REPLACE, MODIFY_DELETE, MODIFY_ADD
from enum import Enum, auto

from ..config import CONFIG
from ..results import Failure, Rejection


logger = logging.getLogger(__name__)

DEFAULT_MODE = "read_only"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 1389
DEFAULT_TLS_PORT = 636
DEFAULT_ANONYMOUS = True
DEFAULT_ADMIN_USER = None
DEFAULT_ADMIN_PASSWORD = None
DEFAULT_TLS = False
DEFAULT_USER_BASE = "ou=users,dc=example"
DEFAULT_GROUP_BASE = "ou=groups,dc=example"
DEFAULT_ATTR_OIDC_UID = "gecos"
DEFAULT_ATTR_LOCAL_UID = "uid"
DEFAULT_SHELL="/bin/sh"
DEFAULT_HOME_BASE="/home"

class Mode(Enum):
    READ_ONLY = auto()
    PRE_CREATED = auto()
    FULL_ACCESS = auto()

    @staticmethod
    def from_str(label):
        label = label.lower()
        if label in ("read_only", "read-only", "readonly"):
            return Mode.READ_ONLY
        elif label in ("pre_created", "pre-created", "precreated"):
            return Mode.PRE_CREATED
        elif label in ("full_access", "full-access", "fullaccess"):
            return Mode.FULL_ACCESS
        else:
            msg = f"Unknown mode '{label}'. Supported modes: "\
                  f"{[name for name, member in Mode.__members__.items()]}."
            logger.error(msg)
            raise Failure(message=msg)


class LdapConnection:
    """Connection to the LDAP server."""
    def __init__(self,
                 mode=DEFAULT_MODE,
                 host=DEFAULT_HOST,
                 port=DEFAULT_PORT,
                 tls=DEFAULT_TLS,
                 user=DEFAULT_ADMIN_USER,
                 password=DEFAULT_ADMIN_PASSWORD,
                 user_base=DEFAULT_USER_BASE,
                 group_base=DEFAULT_GROUP_BASE,
                 attr_oidc_uid=DEFAULT_ATTR_OIDC_UID,
                 attr_local_uid=DEFAULT_ATTR_LOCAL_UID,
                 shell=DEFAULT_SHELL,
                 home_base=DEFAULT_HOME_BASE):
        """Initialise connection to LDAP server.

        :param str host: host where LDAP server is running, default localhost
        :param int port: port where LDAP server is running, default 1389
        :param bool tls: whether connection to LDAP is SSL encrypted
        :param str user: admin username
        :param str password: admin password
        :param str user_base: base used for user namespace in LDAP operations
        :param str group_base: base used for group namespace in LDAP operations
        :param str attr_oidc_uid: LDAP attribute to store uid for federated user, default uid
        :param str attr_local_uid: LDAP attribute to store uid for local user, default gecos
        :param str shell: shell used when creating users
        :param str home_base: base directory for users' home directories
                         local username will be appended to this to create homedir
        """
        self.mode = Mode.from_str(mode)
        self.user_base = user_base
        self.group_base = group_base
        self.attr_oidc_uid = attr_oidc_uid
        self.attr_local_uid = attr_local_uid
        self.shell = shell
        self.home_base = home_base

        try:
            server = Server(f"ldap://{host}:{port}", get_info=ALL)
            if user and password:
                self.connection = Connection(server, user, password, auto_bind=True)
            else:
                self.connection = Connection(server, auto_bind=True)
        except Exception as e:
            msg = f"Could not connect to server ldap://{host}:{port}/"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def search_user_by_oidc_uid(self, oidc_uid):
        try:
            return self.connection.search(
                f"{self.user_base}",
                f"(&({self.attr_oidc_uid}={oidc_uid})(objectClass=inetOrgPerson)(objectClass=posixAccount))",
                attributes=[self.attr_local_uid]
            )
        except Exception as e:
            logger.warning(f"Error searching for uid {oidc_uid}, assuming not found:{e}")
            return False

    def search_user_by_local_username(self, username):
        try:
            return self.connection.search(
                f"{self.user_base}",
                f"(&({self.attr_local_uid}={username})(objectClass=inetOrgPerson)(objectClass=posixAccount))",
                attributes=[self.attr_oidc_uid]
            )
        except Exception as e:
            logger.warning(f"Error searching for uid {oidc_uid}, assuming not found:{e}")
            return False

    def search_group(self, group_name):
        try:
            return self.connection.search(
                f"{self.group_base}",
                f"(&(cn={group_name})(objectClass=posixGroup))",
                attributes=["memberUid", "gidNumber"]
            )
        except Exception as e:
            logger.warning(f"Error searching for group {group_name}, assuming not found: {e}")
            return False

    def get_username_by_id(self, oidc_uid):
        try:
            if self.search_user_by_oidc_uid(oidc_uid):
                entry = self.connection.entries[0]
                return entry[self.attr_local_uid].value
        except Exception as e:
            logger.warning(f"Error retrieving entry for uid {oidc_uid}, assuming not found: {e}")
        return None

    def get_id_by_username(self, name):
        try:
            if self.search_user_by_local_username(name):
                entry = self.connection.entries[0]
                return entry[self.attr_oidc_uid].value
        except Exception as e:
            logger.warning(f"Error retrieving entry for local_username {name}, assuming not found: {e}")
        return None

    def get_gid_by_name(self, name):
        try:
            if self.search_group(name):
                return self.connection.entries[0]["gidNumber"].value
        except Exception as e:
            msg = f"Error retrieving entry for group {name}: {e}"
            logger.error(msg)
            raise Failure(message=msg)

    def get_next_uid(self):
        try:
            if self.connection.search(
                f"{self.user_base}",
                "(&(cn=uidNext)(objectClass=uidNext))",
                attributes=["uidNumber"]
            ):
                uid = self.connection.entries[0]["uidNumber"].value
                # specify uid in MODIFY_DELETE operation to avoid race conditions
                # the operation will fail if the value has been modified in the meantime
                result = self.connection.modify(f"cn=uidNext,{self.user_base}", {
                    "uidNumber": [(MODIFY_DELETE, [uid]), (MODIFY_ADD, [uid+1])]
                })
                return uid
        except Exception as e:
            logger.error(e)
        msg = "Error retrieving next UID."
        logger.error(msg)
        raise Failure(message=msg)

    def get_next_gid(self):
        try:
            if self.connection.search(
                f"{self.group_base}",
                "(&(cn=gidNext)(objectClass=gidNext))",
                attributes=["gidNumber"]
            ):
                gid = self.connection.entries[0]["gidNumber"].value
                # specify gid in MODIFY_DELETE operation to avoid race conditions
                # the operation will fail if the value has been modified in the meantime
                result = self.connection.modify(f"cn=gidNext,{self.group_base}", {
                    "gidNumber": [(MODIFY_DELETE, [gid]), (MODIFY_ADD, [gid+1])]
                })
                return gid
        except Exception as e:
            logger.error(e)
        msg = "Error retrieving next GID."
        logger.error(msg)
        raise Failure(message=msg)

    def add_user(self, userinfo, local_username, primary_group_name):
        """Add an LDAP entry for `local_username` with
        all information from `userinfo`.
        If user exists, a Failure exception is raised.
        """
        try:
            return self.connection.add(
                f"uid={local_username},{self.user_base}",
                object_class=["top", "inetOrgPerson", "posixAccount"],
                attributes={
                    "sn": userinfo.family_name,
                    "givenName": userinfo.given_name,
                    "cn": userinfo.full_name,
                    "mail": userinfo.email,
                    "uid": local_username,
                    "uidNumber": self.get_next_uid(),
                    "gidNumber": self.get_gid_by_name(primary_group_name),
                    "homeDirectory": f"{self.home_base}/{local_username}",
                    "loginShell": self.shell,
                    self.attr_local_uid: local_username,
                    self.attr_oidc_uid: userinfo.unique_id
                })
        except Exception as e:
            msg = f"Failed to add an LDAP entry for uid {userinfo.unique_id} with local username {local_username}."
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def map_user(self, userinfo, local_username):
        """Update the LDAP entry for given `local_username` with
        mapped oidc uid.
        If user doesn't exist, a Failure exception is raised.
        """
        try:
            return self.connection.modify(
                f"uid={local_username},{self.user_base}",
                {
                    self.attr_oidc_uid: [(MODIFY_REPLACE, [userinfo.unique_id])]
                })
        except Exception as e:
            msg = f"Failed to modify the LDAP entry for uid {userinfo.unique_id} with local username {local_username}."
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def update_user(self, userinfo, local_username):
        """Update the LDAP entry for given `local_username` with
        all information in `userinfo`.
        If user doesn't exist, a Failure exception is raised.
        """
        try:
            return self.connection.modify(
                f"uid={local_username},{self.user_base}",
                {
                    "sn": [(MODIFY_REPLACE, [userinfo.family_name])],
                    "givenName": [(MODIFY_REPLACE, [userinfo.given_name])],
                    "cn": [(MODIFY_REPLACE, [userinfo.full_name])],
                    "mail": [(MODIFY_REPLACE, [userinfo.email])],
                    "uid": [(MODIFY_REPLACE, [local_username])],
                    "homeDirectory": [(MODIFY_REPLACE, [f"{self.home_base}/{local_username}"])],
                    "loginShell": [(MODIFY_REPLACE, [self.shell])],
                    self.attr_local_uid: [(MODIFY_REPLACE, [local_username])],
                    self.attr_oidc_uid: [(MODIFY_REPLACE, [userinfo.unique_id])]
                })
        except Exception as e:
            msg = f"Failed to modify the LDAP entry for uid {userinfo.unique_id} with local username {local_username}."
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def delete_user(self, local_username):
        """Delete the LDAP entry for given `local_username`.
        If user doesn't exist, a Failure exception is raised.
        """
        try:
            return self.connection.delete(f"uid={local_username},{self.user_base}")
        except Exception as e:
            msg = f"Failed to delete the LDAP entry for local username {local_username}."
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def add_user_to_group(self, local_username, group_name):
        """Add a user to group.
        If either of them does not exist, a Failure exception is raised.
        """
        try:
            self.connection.modify(
                f"cn={group_name},{self.group_base}",
                {
                    "memberUid": [(MODIFY_ADD, [local_username])],
                }
            )
        except Exception as e:
            msg = f"Failed to modify the LDAP entry for group {group_name} with local username {local_username}."
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def add_group(self, group_name):
        """Add an LDAP entry for `group_name`.
        If group exists, a warning is issued.
        """
        try:
            return self.connection.add(
                f"cn={group_name},{self.group_base}",
                object_class=["top", "posixGroup"],
                attributes={
                    "cn": group_name,
                    "gidNumber": self.get_next_gid(),
                })
        except Exception as e:
            msg = f"Failed to add an LDAP entry for group {group_name}."
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    @staticmethod
    def load():
        try:
            config = CONFIG["backend.ldap"]
            mode = config.get("mode", DEFAULT_MODE)
            host = config.get("host", DEFAULT_HOST)
            tls = config.get("tls", DEFAULT_TLS)
            if tls:
                port = config.get("port", DEFAULT_TLS_PORT)
            else:
                port = config.get("port", DEFAULT_PORT)
            user = config.get("user", DEFAULT_ADMIN_USER)
            password = config.get("password", DEFAULT_ADMIN_PASSWORD)
            user_base = config.get("user_base", DEFAULT_USER_BASE)
            group_base = config.get("group_base", DEFAULT_GROUP_BASE)
            attr_oidc_uid = config.get("attribute_oidc_uid", DEFAULT_ATTR_OIDC_UID)
            attr_local_uid = config.get("attribute_local_uid", DEFAULT_ATTR_LOCAL_UID)
            shell = config.get("shell", DEFAULT_SHELL)
            home_base = config.get("home_base", DEFAULT_HOME_BASE).rstrip("/")

            return LdapConnection(mode, host, port, tls, user, password,
                                  user_base, group_base, attr_oidc_uid,
                                  attr_local_uid, shell, home_base)
        except Exception:
            logger.warning("Could not find [backend.ldap] section in feudalt config, using defaults...")
            return LdapConnection()


LDAP = LdapConnection.load()


class User:
    """Manages the user object on the service."""
    def __init__(self, userinfo):
        """
        Arguments:
        userinfo -- (type: UserInfo)
        """
        self.primary_group = Group(userinfo.primary_group)
        self.userinfo = userinfo
        self.unique_id = userinfo.unique_id
        logger.debug(F"backend processing: {userinfo.unique_id}")
        if self.exists():
            username = self.get_username()
            logger.debug(F"This user does actually exist. The name is: {username}")
            self.set_username(username)
        else:
            self.set_username(userinfo.username)

        self.ssh_keys = [key["value"] for key in userinfo.ssh_keys]
        self.credentials = {}

    def exists(self):
        """Return whether the user exists on the service.

        If this returns True,  calling `create` should have no effect or raise an error.
        """
        logger.info(F"Check if user exists: {self.unique_id}")
        return LDAP.search_user_by_oidc_uid(self.unique_id)

    def name_taken(self, name):
        """Return whether the username is already taken by another user on the service,
        i.e. if an entry for it exists in the LDAP and it's not mapped to the current oidc uid.

        In 'pre_created' mode, taken means that the username has been mapped to another oidc uid.
        """
        if LDAP.search_user_by_local_username(name):  # there is an entry for name in LDAP
            oidc_uid = LDAP.get_id_by_username(name)  # this is the oidc_uid mapped to name
            if LDAP.mode == Mode.PRE_CREATED and oidc_uid is None:  # pre-created but not mapped
                return False
            return oidc_uid != self.unique_id         # name already mapped to another oidc uid?
        else:                                         # no entry for name found in LDAP
            return False

    def get_username(self):
        """Check if a user exists based on unique_id and return the name"""
        return LDAP.get_username_by_id(self.unique_id)

    def set_username(self, username):
        """Set local username on the service."""
        self.name = username

    def create(self):
        """Create the user on the service.

        If the user already exists, do nothing or raise an error
        """
        if LDAP.mode == Mode.READ_ONLY:
            msg = f"LDAP backend in read_only mode, new entry cannot be added for user {self.unique_id}."\
                  f" (local username {self.name})"
            logger.error(msg)
            raise Rejection(message=f"{msg} Please contact an administrator to create an account for you.")
        elif LDAP.mode == Mode.PRE_CREATED:
            if not LDAP.search_user_by_local_username(self.name):    
                msg = f"Local username {self.name} not found in LDAP for user {self.unique_id}."
                logger.error(msg)
                raise Failure(message=f"{msg} Please contact an administrator to pre-create this account for you.")
            else:
                LDAP.map_user(self.userinfo, self.name)
        else:  # Mode.FULL_ACCESS
            LDAP.add_user(self.userinfo, self.name, self.primary_group.name)

    def update(self):
        """Update all relevant information about the user on the service.

        If the user doesn't exists, behaviour is undefined.
        """
        self.credentials['ssh_user'] = self.name
        self.credentials['ssh_host'] = CONFIG['backend.ldap.login_info'].get('ssh_host', 'undefined')
        self.credentials['commandline'] = "ssh {}@{}".format(
            self.credentials['ssh_user'], self.credentials['ssh_host'])

        if LDAP.mode == Mode.READ_ONLY:
            msg = f"LDAP backend in read_only mode, entry for user {self.unique_id} "\
                  f"cannot be modified."
            logger.warning(msg)
        elif LDAP.mode == Mode.PRE_CREATED:
            msg = f"LDAP backend in pre_created mode, entry for user {self.unique_id} "\
                  f"cannot be modified."
            logger.warning(msg)
        else:  # Mode.FULL_ACCESS
            LDAP.update_user(self.userinfo, self.name)

    def delete(self):
        """Delete the user on the service.

        If the user doesn"t exists, do nothing or raise an error.
        """
        if LDAP.mode == Mode.READ_ONLY:
            msg = f"LDAP backend in read_only mode, entry for local username {self.name} cannot be deleted."
            logger.error(msg)
            raise Rejection(message=msg)
        elif LDAP.mode == Mode.PRE_CREATED:
            msg = f"LDAP backend in pre_created mode, entry for local username {self.name} cannot be deleted."
            logger.error(msg)
            raise Failure(message=msg)
        else:  # Mode.FULL_ACCESS
            LDAP.delete_user(self.name)

    def mod(self, supplementary_groups=None):
        """Modify the user on the service.

        The state of the user with respect to the provided Arguments after calling this function
        should not depend on the state the user had previously.

        If the user doesn't exists, behaviour is undefined.

        Arguments:
        supplementary_groups -- A list of groups to add the user to (type: list(Group))
        """
        if supplementary_groups is None or supplementary_groups == []:
            logger.debug(f"Empty group list for user {self.name}. Nothing to do here.")
        else:
            logger.debug(f"Ensuring user '{self.name}' is member of these groups: \
                         {[g.name for g in supplementary_groups]}")
            if LDAP.mode == Mode.READ_ONLY:
                msg = f"LDAP backend in read_only mode, local username {self.name} cannot be added to given groups."
                logger.warning(msg)
            elif LDAP.mode == Mode.PRE_CREATED:
                for group in supplementary_groups:
                    LDAP.add_user_to_group(self.name, group.name)
            else:  # Mode.FULL_ACCESS
                for group in supplementary_groups:
                    LDAP.add_user_to_group(self.name, group.name)
    def install_ssh_keys(self):
        """Install users SSH keys on the service.

        No other SSH keys should be active after calling this function.

        If the user doesn't exists, behaviour is undefined.
        """
        # TODO: use ldapPublicKey schema (sshPublicKey attribute) for storing ssh key in LDAP
        pass
    def uninstall_ssh_keys(self):
        """Uninstall the users SSH keys on the service.

        This must uninstall all SSH keys installed with `install_ssh_keys`. It may uninstall SSH
        keys installed by other means.

        If the user doesn't exists, behaviour is undefined.
        """
        # TODO: use ldapPublicKey schema (sshPublicKey attribute) for storing ssh key in LDAP
        pass


class Group:
    """Manages the group object on the service."""
    def __init__(self, name):
        """
        Arguments:
        name -- The name of the group
        """
        self.name = name
    def exists(self):
        """Return whether the group already exists."""
        logger.debug(F"Check if group exists: {self.name}")
        if LDAP.search_group(self.name):
            logger.debug(f"Group {self.name} exists.")
            return True
        else:
            logger.debug(f"Group {self.name} doesn't exist.")
            return False
    def create(self):
        """Create the group on the service.

        If the group already exists, nothing happens.
        """
        if self.exists():
            logger.info(f"Group {self.name} exists.")
        elif LDAP.mode == Mode.READ_ONLY:
            msg = f"LDAP backend in read_only mode, new entry cannot be added for group {self.name}."
            logger.warning(msg)
        elif LDAP.mode == Mode.PRE_CREATED:
            msg = f"LDAP backend in pre_created mode, new entry cannot be added for group {self.name}."
            logger.warning(msg)
        else:  # Mode.FULL_ACCESS
            LDAP.add_group(self.name)
