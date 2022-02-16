"""LDAP backend for pre-created accounts.
It"s in the proof-of-concept state.
"""


import logging
from ldap3 import (
    Server,
    Connection,
    ALL,
    BASE,
    MODIFY_REPLACE,
    MODIFY_DELETE,
    MODIFY_ADD,
    SAFE_SYNC,
)
from enum import Enum, auto

from ..config import CONFIG
from ..results import Failure, Rejection


logger = logging.getLogger(__name__)


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
            msg = (
                f"Unknown mode '{label}'. Supported modes: "
                f"{[name for name, member in Mode.__members__.items()]}."
            )
            logger.error(msg)
            raise Failure(message=msg)


DEFAULT_MODE = Mode.READ_ONLY
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
DEFAULT_SHELL = "/bin/sh"
DEFAULT_HOME_BASE = "/home"
DEFAULT_UID_MIN = 1000
DEFAULT_UID_MAX = 60000
DEFAULT_GID_MIN = 1000
DEFAULT_GID_MAX = 60000


class LdapSearchResult:
    def __init__(self, ldap_connection, args, kwargs):
        """Perform a search with given arguments and create LdapSearchResult object.

        Initialise fields from the return value of search (connection in SAFE_SYNC mode),
        where the return value is a tuple (status, result, response, request).

        @param ldap_connection: an active ldap3.Connection object
        @param args: list of arguments for ldap3.Connection.search method
        @param kwargs: dictionary of key-value arguments for ldap3.Connection.search method
        """
        try:
            search_result = ldap_connection.search(*args, **kwargs)
            self.status = search_result[0]
            self.result = search_result[1]
            self.response = search_result[2]
            self.request = search_result[3]
        except Exception as e:
            msg = "Error searching in LDAP"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def found(self):
        return self.status

    def get_attribute(self, attribute_name):
        try:
            value = self.response[0]["attributes"][attribute_name]
            if isinstance(value, list):
                return value[0]
            else:
                return value
        except Exception as e:
            logger.warning(f"Attribute {attribute_name} not found in response: {e}")
            return None


class LdapConnection:
    """Connection to the LDAP server."""

    def __init__(
        self,
        mode=DEFAULT_MODE,
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        tls=DEFAULT_TLS,
        admin_user=DEFAULT_ADMIN_USER,
        admin_password=DEFAULT_ADMIN_PASSWORD,
        user_base=DEFAULT_USER_BASE,
        group_base=DEFAULT_GROUP_BASE,
        attr_oidc_uid=DEFAULT_ATTR_OIDC_UID,
        attr_local_uid=DEFAULT_ATTR_LOCAL_UID,
        shell=DEFAULT_SHELL,
        home_base=DEFAULT_HOME_BASE,
        uid_min=DEFAULT_UID_MIN,
        uid_max=DEFAULT_UID_MAX,
        gid_min=DEFAULT_GID_MIN,
        gid_max=DEFAULT_GID_MAX,
    ):
        """Initialise connection to LDAP server.

        :param str host: host where LDAP server is running, default localhost
        :param int port: port where LDAP server is running, default 1389
        :param bool tls: whether connection to LDAP is SSL encrypted
        :param str admin_user: admin username
        :param str admin_password: admin password
        :param str user_base: base used for user namespace in LDAP operations
        :param str group_base: base used for group namespace in LDAP operations
        :param str attr_oidc_uid: LDAP attribute to store uid for federated user, default uid
        :param str attr_local_uid: LDAP attribute to store uid for local user, default gecos
        :param str shell: shell used when creating users
        :param str home_base: base directory for users' home directories
                         local username will be appended to this to create homedir
        """
        self.mode = mode
        self.user_base = user_base
        self.group_base = group_base
        self.attr_oidc_uid = attr_oidc_uid
        self.attr_local_uid = attr_local_uid
        self.shell = shell
        self.home_base = home_base
        self.uid_min = uid_min
        self.uid_max = uid_max
        self.gid_min = gid_min
        self.gid_max = gid_max

        # initialise and bind connection to LDAP
        try:
            server = Server(f"ldap://{host}:{port}", get_info=ALL)
            if admin_user and admin_password:
                # add SAFE_SYNC, so we get more return values
                self.connection = Connection(
                    server,
                    admin_user,
                    admin_password,
                    auto_bind=True,
                    client_strategy=SAFE_SYNC,
                )
            else:
                self.connection = Connection(server, auto_bind=True, client_strategy=SAFE_SYNC)
        except Exception as e:
            msg = f"Could not connect to server ldap://{host}:{port}/"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def init_nextuidgid(self):
        """Initialise uidNext and gidNext entries in FULL_ACCESS mode
        with values starting in configured range.
        """
        try:
            if self.mode == Mode.FULL_ACCESS:
                search_uid = self.search_next_uid()
                if not search_uid.found():
                    self.connection.add(
                        f"cn=uidNext,{self.user_base}",
                        object_class=["uidNext"],
                        attributes={"cn": "uidNext", "uidNumber": self.uid_min},
                    )
                else:
                    logger.info("Using existing uidNext value.")

                search_gid = self.search_next_gid()
                if not search_gid.found():
                    self.connection.add(
                        f"cn=gidNext,{self.group_base}",
                        object_class=["gidNext"],
                        attributes={"cn": "gidNext", "gidNumber": self.gid_min},
                    )
                else:
                    logger.info("Using existing gidNext value.")
        except Exception as e:
            msg = "Error adding entries in LDAP for tracking available UID and GID values"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def search_user_by_oidc_uid(self, oidc_uid):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.user_base}",
                f"(&({self.attr_oidc_uid}={oidc_uid})(objectClass=inetOrgPerson)(objectClass=posixAccount))",
            ],
            {"attributes": [self.attr_local_uid]},
        )

    def search_user_by_local_username(self, username):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.user_base}",
                f"(&({self.attr_local_uid}={username})(objectClass=inetOrgPerson)(objectClass=posixAccount))",
            ],
            {"attributes": [self.attr_oidc_uid]},
        )

    def search_group_by_name(self, group_name):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.group_base}",
                f"(&(cn={group_name})(objectClass=posixGroup))",
            ],
            {"attributes": ["memberUid", "gidNumber"]},
        )

    def search_next_uid(self):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.user_base}",
                "(&(cn=uidNext)(objectClass=uidNext))",
            ],
            {"attributes": ["uidNumber"]},
        )

    def search_next_gid(self):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.group_base}",
                "(&(cn=gidNext)(objectClass=gidNext))",
            ],
            {"attributes": ["gidNumber"]},
        )

    def is_uid_taken(self, uid):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.user_base}",
                f"(&(uidNumber={uid})(objectClass=posixAccount))",
            ],
            {},
        ).found()

    def is_gid_taken(self, gid):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.group_base}",
                f"(&(gidNumber={gid})(objectClass=posixGroup))",
            ],
            {},
        ).found()

    def get_next_uid(self):
        search_result = self.search_next_uid()
        if search_result.found():
            uid = search_result.get_attribute("uidNumber")

            # make sure uid is not taken already
            next_uid = uid
            while self.is_uid_taken(next_uid):
                next_uid += 1

            # make sure uid still in allowed range
            if next_uid > self.uid_max:
                raise Exception("No available UIDs left in configured range.")

            # specify uid in MODIFY_DELETE operation to avoid race conditions
            # the operation will fail if the value has been modified in the meantime
            result = self.connection.modify(
                f"cn=uidNext,{self.user_base}",
                {"uidNumber": [(MODIFY_DELETE, [uid]), (MODIFY_ADD, [next_uid + 1])]},
            )
            return next_uid

    def get_next_gid(self):
        search_result = self.search_next_gid()
        if search_result.found():
            gid = search_result.get_attribute("gidNumber")

            # make sure gid is not taken already
            next_gid = gid
            while self.is_gid_taken(next_gid):
                next_gid += 1

            # make sure gid still in allowed range
            if next_gid > self.gid_max:
                raise Exception("No available GIDs left in configured range.")

            # specify gid in MODIFY_DELETE operation to avoid race conditions
            # the operation will fail if the value has been modified in the meantime
            result = self.connection.modify(
                f"cn=gidNext,{self.group_base}",
                {"gidNumber": [(MODIFY_DELETE, [gid]), (MODIFY_ADD, [next_gid + 1])]},
            )
            return next_gid

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
                    "gidNumber": self.search_group_by_name(primary_group_name).get_attribute(
                        "gidNumber"
                    ),
                    "homeDirectory": f"{self.home_base}/{local_username}",
                    "loginShell": self.shell,
                    self.attr_local_uid: local_username,
                    self.attr_oidc_uid: userinfo.unique_id,
                },
            )
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
                {self.attr_oidc_uid: [(MODIFY_REPLACE, [userinfo.unique_id])]},
            )
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
                    self.attr_oidc_uid: [(MODIFY_REPLACE, [userinfo.unique_id])],
                },
            )
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
                },
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
                },
            )
        except Exception as e:
            msg = f"Failed to add an LDAP entry for group {group_name}."
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    @staticmethod
    def load():
        try:
            config = CONFIG["backend.ldap"]
            mode = Mode.from_str(config.get("mode", DEFAULT_MODE))
            host = config.get("host", DEFAULT_HOST)
            tls = config.get("tls", DEFAULT_TLS)
            if tls:
                port = config.getint("port", DEFAULT_TLS_PORT)
            else:
                port = config.getint("port", DEFAULT_PORT)
            admin_user = config.get("admin_user", DEFAULT_ADMIN_USER)
            admin_password = config.get("admin_password", DEFAULT_ADMIN_PASSWORD)
            user_base = config.get("user_base", DEFAULT_USER_BASE)
            group_base = config.get("group_base", DEFAULT_GROUP_BASE)
            attr_oidc_uid = config.get("attribute_oidc_uid", DEFAULT_ATTR_OIDC_UID)
            attr_local_uid = config.get("attribute_local_uid", DEFAULT_ATTR_LOCAL_UID)

            # only needed in FULL_ACCESS mode
            shell = config.get("shell", DEFAULT_SHELL)
            home_base = config.get("home_base", DEFAULT_HOME_BASE).rstrip("/")
            uid_min = config.getint("uid_min", DEFAULT_UID_MIN)
            uid_max = config.getint("uid_max", DEFAULT_UID_MAX)
            gid_min = config.getint("gid_min", DEFAULT_GID_MIN)
            gid_max = config.getint("gid_max", DEFAULT_GID_MAX)

            ldap = LdapConnection(
                mode,
                host,
                port,
                tls,
                admin_user,
                admin_password,
                user_base,
                group_base,
                attr_oidc_uid,
                attr_local_uid,
                shell,
                home_base,
                uid_min,
                uid_max,
                gid_min,
                gid_max,
            )
        except KeyError:
            logger.warning(
                "Could not find [backend.ldap] section in feudal config, using defaults..."
            )
            ldap = LdapConnection()
        # init uidNext and gidNext entries in LDAP
        ldap.init_nextuidgid()
        return ldap


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
        logger.debug(f"backend processing: {userinfo.unique_id}")
        if self.exists():
            username = self.get_username()
            logger.debug(f"This user does actually exist. The name is: {username}")
            self.set_username(username)
        else:
            self.set_username(userinfo.username)

        self.ssh_keys = [key["value"] for key in userinfo.ssh_keys]
        self.credentials = {}

    def exists(self):
        """Return whether the user exists on the service.

        If this returns True,  calling `create` should have no effect or raise an error.
        """
        logger.info(f"Check if user exists: {self.unique_id}")
        return LDAP.search_user_by_oidc_uid(self.unique_id).found()

    def name_taken(self, name):
        """Return whether the username is already taken by another user on the service,
        i.e. if an entry for it exists in the LDAP and it's not mapped to the current oidc uid.

        In 'pre_created' mode, taken means that the username has been mapped to another oidc uid.
        """
        search_result = LDAP.search_user_by_local_username(name)
        if search_result.found():  # there is an entry for name in LDAP
            oidc_uid = search_result.get_attribute(
                LDAP.attr_oidc_uid
            )  # this is the oidc_uid mapped to name
            if LDAP.mode == Mode.PRE_CREATED and oidc_uid is None:  # pre-created but not mapped
                return False
            return oidc_uid != self.unique_id  # name already mapped to another oidc uid
        else:  # no entry for name found in LDAP
            return False

    def get_username(self):
        """Check if a user exists based on unique_id and return the name"""
        return LDAP.search_user_by_oidc_uid(self.unique_id).get_attribute(LDAP.attr_local_uid)

    def set_username(self, username):
        """Set local username on the service."""
        self.name = username

    def create(self):
        """Create the user on the service.

        If the user already exists, do nothing or raise an error
        """
        if LDAP.mode == Mode.READ_ONLY:
            msg = (
                f"LDAP backend in read_only mode, new entry cannot be added for user {self.unique_id}."
                f" (local username {self.name})"
            )
            logger.error(msg)
            raise Rejection(
                message=f"{msg} Please contact an administrator to create an account for you."
            )
        elif LDAP.mode == Mode.PRE_CREATED:
            if not LDAP.search_user_by_local_username(self.name).found():
                msg = f"Local username {self.name} not found in LDAP for user {self.unique_id}."
                logger.error(msg)
                raise Failure(
                    message=f"{msg} Please contact an administrator to pre-create this account for you."
                )
            else:
                LDAP.map_user(self.userinfo, self.name)
        else:  # Mode.FULL_ACCESS
            LDAP.add_user(self.userinfo, self.name, self.primary_group.name)

    def update(self):
        """Update all relevant information about the user on the service.

        If the user doesn't exists, behaviour is undefined.
        """
        self.credentials["ssh_user"] = self.name
        self.credentials["ssh_host"] = CONFIG["backend.ldap.login_info"].get(
            "ssh_host", "undefined"
        )
        self.credentials["commandline"] = "ssh {}@{}".format(
            self.credentials["ssh_user"], self.credentials["ssh_host"]
        )

        if LDAP.mode == Mode.READ_ONLY:
            msg = (
                f"LDAP backend in read_only mode, entry for user {self.unique_id} "
                f"cannot be modified."
            )
            logger.warning(msg)
        elif LDAP.mode == Mode.PRE_CREATED:
            msg = (
                f"LDAP backend in pre_created mode, entry for user {self.unique_id} "
                f"cannot be modified."
            )
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
            logger.debug(
                f"Ensuring user '{self.name}' is member of these groups: \
                         {[g.name for g in supplementary_groups]}"
            )
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
        logger.debug(f"Check if group exists: {self.name}")
        if LDAP.search_group_by_name(self.name).found():
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
            msg = (
                f"LDAP backend in read_only mode, new entry cannot be added for group {self.name}."
            )
            logger.warning(msg)
        elif LDAP.mode == Mode.PRE_CREATED:
            msg = f"LDAP backend in pre_created mode, new entry cannot be added for group {self.name}."
            logger.warning(msg)
        else:  # Mode.FULL_ACCESS
            LDAP.add_group(self.name)
