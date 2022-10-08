"""LDAP backend for pre-created accounts.
It"s in the proof-of-concept state.
"""


import logging
from ldap3 import (
    AUTO_BIND_NO_TLS,
    SAFE_RESTARTABLE,
    Server,
    Connection,
    ALL,
    MODIFY_REPLACE,
    MODIFY_DELETE,
    MODIFY_ADD,
    SAFE_SYNC,
    LDIF,
)
from enum import Enum, auto

from ldf_adapter.config import CONFIG
from ldf_adapter.results import Failure, Rejection, FatalError


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
            if ldap_connection.strategy_type in [SAFE_SYNC, SAFE_RESTARTABLE]:
                self.status = search_result[0]
                self.result = search_result[1]
                self.response = search_result[2]
                self.request = search_result[3]
            else:
                self.status = ldap_connection.response not in [None, []]
                self.result = ldap_connection.result
                self.response = ldap_connection.response
                self.request = ldap_connection.request
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

    def get_attributes(self):
        attributes = self.response[0]["attributes"]
        for key, value in attributes.items():
            if isinstance(value, list):
                attributes[key] = value[0]
        return attributes

    def get_attribute_for_all(self, attribute_name):
        try:
            all_entries = []
            for entry in self.response:
                value = entry["attributes"][attribute_name]
                if isinstance(value, list):
                    value = value[0]
                all_entries.append(value)
            return all_entries
        except Exception as e:
            logger.warning(f"Attribute {attribute_name} not found in response: {e}")
            return []


class LdapConnection:
    """Connection to the LDAP server."""

    def __init__(self):
        """Initialise connection to LDAP server."""
        if CONFIG.backend.ldap is None:
            raise FatalError(
                message="LDAP backend is not configured. Please check your configuration."
            )
        self.mode = Mode.from_str(CONFIG.backend.ldap.mode)
        self.user_base = CONFIG.backend.ldap.user_base
        self.group_base = CONFIG.backend.ldap.group_base
        self.attr_oidc_uid = CONFIG.backend.ldap.attribute_oidc_uid
        self.attr_local_uid = CONFIG.backend.ldap.attribute_local_uid
        self.shell = CONFIG.backend.ldap.shell
        self.home_base = CONFIG.backend.ldap.home_base
        self.uid_min = CONFIG.backend.ldap.uid_min
        self.uid_max = CONFIG.backend.ldap.uid_max
        self.gid_min = CONFIG.backend.ldap.gid_min
        self.gid_max = CONFIG.backend.ldap.gid_max

        # initialise connection used to generate LDIFs
        self.ldif_connection = Connection(server=None, client_strategy=LDIF)
        self.ldif_connection.bind()
        # initialise and bind connection to LDAP server
        try:
            server = Server(
                f"ldap://{CONFIG.backend.ldap.host}:{CONFIG.backend.ldap.port}", get_info=ALL
            )
            if CONFIG.backend.ldap.admin_user and CONFIG.backend.ldap.admin_password:
                # add SAFE_SYNC, so we get more return values
                self.connection = Connection(
                    server,
                    CONFIG.backend.ldap.admin_user,
                    CONFIG.backend.ldap.admin_password,
                    client_strategy=SAFE_SYNC,
                    auto_bind=AUTO_BIND_NO_TLS,
                )
            else:
                self.connection = Connection(
                    server, client_strategy=SAFE_SYNC, auto_bind=AUTO_BIND_NO_TLS
                )
        except Exception as e:
            msg = f"Could not connect to server ldap://{CONFIG.backend.ldap.host}:{CONFIG.backend.ldap.port}/"
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
                    result = self.connection.add(
                        f"cn=uidNext,{self.user_base}",
                        object_class=["uidNext"],
                        attributes={"cn": "uidNext", "uidNumber": self.uid_min},
                    )
                    search_uid = self.search_next_uid()
                else:
                    logger.info(
                        f"uidNext already initialised: {search_uid.get_attribute('uidNumber')}."
                    )

                search_gid = self.search_next_gid()
                if not search_gid.found():
                    result = self.connection.add(
                        f"cn=gidNext,{self.group_base}",
                        object_class=["gidNext"],
                        attributes={"cn": "gidNext", "gidNumber": self.gid_min},
                    )
                    search_gid = self.search_next_gid()
                else:
                    logger.info(
                        f"gidNext already initialised: {search_gid.get_attribute('gidNumber')}."
                    )
        except Exception as e:
            msg = "Error adding entries in LDAP for tracking available UID and GID values"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def search_user_by_oidc_uid(self, oidc_uid, attributes=[]):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.user_base}",
                f"(&({self.attr_oidc_uid}={oidc_uid})(objectClass=inetOrgPerson)(objectClass=posixAccount))",
            ],
            {"attributes": attributes},
        )

    def search_user_by_local_username(self, username, get_unique_id=False):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.user_base}",
                f"(&({self.attr_local_uid}={username})(objectClass=inetOrgPerson)(objectClass=posixAccount))",
            ],
            {
                "attributes": [self.attr_local_uid, self.attr_oidc_uid]
                if get_unique_id
                else [self.attr_local_uid]
            },
        )

    def search_group_by_name(self, group_name, attributes=[]):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.group_base}",
                f"(&(cn={group_name})(objectClass=posixGroup))",
            ],
            {"attributes": attributes},
        )

    def search_group_by_gid(self, gid):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.group_base}",
                f"(&(gidNumber={gid})(objectClass=posixGroup))",
            ],
            {"attributes": ["cn"]},
        )

    def search_groups_by_member(self, username):
        return LdapSearchResult(
            self.connection,
            [
                f"{self.group_base}",
                f"(&(memberUid={username})(objectClass=posixGroup))",
            ],
            {"attributes": ["cn", "gidNumber"]},
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
            try:
                uid = int(uid)
            except Exception as e:
                logger.error(f"Could not convert uidNumber to int: {e}")
                raise Failure(message="Could not parse uidNumber from LDAP")

            # make sure uid is not taken already and still in allowed range
            next_uid = uid
            while self.is_uid_taken(next_uid) and next_uid <= self.uid_max:
                next_uid += 1

            # make sure uid still in allowed range
            if next_uid > self.uid_max:
                raise Failure(message="No available UIDs left in configured range.")

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
            try:
                gid = int(gid)
            except Exception as e:
                logger.error(f"Could not convert gidNumber to int: {e}")
                raise Failure(message="Could not parse gidNumber from LDAP")

            # make sure gid is not taken already and still in allowed range
            next_gid = gid
            while self.is_gid_taken(next_gid) and next_gid <= self.gid_max:
                next_gid += 1

            # make sure gid still in allowed range
            if next_gid > self.gid_max:
                raise Failure(message="No available GIDs left in configured range.")

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
            dn = f"uid={local_username},{self.user_base}"
            object_class = ["top", "inetOrgPerson", "posixAccount"]
            attributes = {
                "uid": local_username,
                "uidNumber": self.get_next_uid(),
                "gidNumber": self.search_group_by_name(
                    primary_group_name, attributes=["gidNumber"]
                ).get_attribute("gidNumber"),
                "homeDirectory": f"{self.home_base}/{local_username}",
                "loginShell": self.shell,
                self.attr_local_uid: local_username,
                self.attr_oidc_uid: userinfo.unique_id,
            }
            if userinfo.family_name is not None:
                attributes["sn"] = userinfo.family_name
            if userinfo.given_name is not None:
                attributes["givenName"] = userinfo.given_name
            if userinfo.full_name is not None:
                attributes["cn"] = userinfo.full_name
            if userinfo.email is not None:
                attributes["mail"] = userinfo.email
            return self.connection.add(
                dn,
                object_class=object_class,
                attributes=attributes,
            )
        except Exception as e:
            msg = f"Failed to add an LDAP entry for uid {userinfo.unique_id} with local username {local_username}"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def get_all_user_info(self, unique_id):
        """Return all user info for a given unique_id."""
        search_result = self.search_user_by_oidc_uid(unique_id, attributes=["*"])
        if not search_result.found():
            raise Failure(message=f"User with unique_id {unique_id} not found.")
        return search_result.get_attributes()

    def add_user_ldif(self, userinfo, local_username, primary_group_name):
        """Return LDIF representation for a new user entry for `local_username` with
        all information from `userinfo`.
        If user exists, a Failure exception is raised.
        """
        dn = f"uid={local_username},{self.user_base}"
        object_class = ["top", "inetOrgPerson", "posixAccount"]
        gidNumber = self.search_group_by_name(
            primary_group_name, attributes=["gidNumber"]
        ).get_attribute("gidNumber")
        if not gidNumber:
            gidNumber = ""
        attributes = {
            "uid": local_username,
            "uidNumber": "",
            "gidNumber": gidNumber,
            "homeDirectory": f"{self.home_base}/{local_username}",
            "loginShell": self.shell,
            self.attr_local_uid: local_username,
            self.attr_oidc_uid: userinfo.unique_id,
        }
        if userinfo.family_name is not None:
            attributes["sn"] = userinfo.family_name
        if userinfo.given_name is not None:
            attributes["givenName"] = userinfo.given_name
        if userinfo.full_name is not None:
            attributes["cn"] = userinfo.full_name
        if userinfo.email is not None:
            attributes["mail"] = userinfo.email
        self.ldif_connection.add(dn, object_class=object_class, attributes=attributes)
        return self.ldif_connection.response

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
            msg = f"Failed to modify the LDAP entry for uid {userinfo.unique_id} with local username {local_username}"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def map_user_ldif(self, userinfo, local_username):
        """Return LDIF representation for updating the LDAP entry for given `local_username` with
        mapped oidc uid. If user doesn't exist, a Failure exception is raised.
        """
        try:
            self.ldif_connection.modify(
                f"uid={local_username},{self.user_base}",
                {self.attr_oidc_uid: [(MODIFY_REPLACE, [userinfo.unique_id])]},
            )
            return self.ldif_connection.response
        except Exception as e:
            msg = f"Failed to get LDIF to modify the LDAP entry for uid {userinfo.unique_id} with local username {local_username}"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def update_user(self, userinfo, local_username):
        """Update the LDAP entry for given `local_username` with
        all information in `userinfo`.
        If user doesn't exist, nothing happens.
        """
        try:
            changes = {
                "homeDirectory": [(MODIFY_REPLACE, [f"{self.home_base}/{local_username}"])],
                "loginShell": [(MODIFY_REPLACE, [self.shell])],
                self.attr_local_uid: [(MODIFY_REPLACE, [local_username])],
                self.attr_oidc_uid: [(MODIFY_REPLACE, [userinfo.unique_id])],
            }
            if userinfo.family_name is not None:
                changes["sn"] = [(MODIFY_REPLACE, [userinfo.family_name])]
            if userinfo.given_name is not None:
                changes["givenName"] = [(MODIFY_REPLACE, [userinfo.given_name])]
            if userinfo.full_name is not None:
                changes["cn"] = [(MODIFY_REPLACE, [userinfo.full_name])]
            if userinfo.email is not None:
                changes["mail"] = [(MODIFY_REPLACE, [userinfo.email])]
            return self.connection.modify(
                f"uid={local_username},{self.user_base}",
                changes,
            )
        except Exception as e:
            msg = f"Failed to modify the LDAP entry for uid {userinfo.unique_id} with local username {local_username}"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def delete_user(self, local_username):
        """Delete the LDAP entry for given `local_username`.
        If user doesn't exist, no failure is raised.
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
            msg = f"Failed to modify the LDAP entry for group {group_name} with local username {local_username}"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def add_user_to_group_ldif(self, local_username, group_name):
        """LDIF representation for adding a user to group."""
        self.ldif_connection.modify(
            f"cn={group_name},{self.group_base}",
            {
                "memberUid": [(MODIFY_ADD, [local_username])],
            },
        )
        return self.ldif_connection.response

    def remove_user_from_group(self, local_username, group_name):
        """Remove a user from group.
        If either of them does not exist, a Failure exception is raised.
        """
        try:
            self.connection.modify(
                f"cn={group_name},{self.group_base}",
                {
                    "memberUid": [(MODIFY_DELETE, [local_username])],
                },
            )
        except Exception as e:
            msg = f"Failed to modify the LDAP entry for group {group_name} with local username {local_username}"
            logger.error(f"{msg}: {e}")
            raise Failure(message=msg)

    def remove_user_from_group_ldif(self, local_username, group_name):
        """LDIF representation for removing a user from a group."""
        self.ldif_connection.modify(
            f"cn={group_name},{self.group_base}",
            {
                "memberUid": [(MODIFY_DELETE, [local_username])],
            },
        )
        return self.ldif_connection.response

    def get_user_groups(self, local_username):
        """Get all groups a user belongs to.

        Returns a list of names.
        """
        logger.debug(f"Searching groups for user {local_username} in LDAP...")
        result = self.search_groups_by_member(local_username)
        if not result.found:
            return []
        return result.get_attribute_for_all("cn")

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

    def add_group_ldif(self, group_name):
        """LDIF representation for adding an LDAP entry for `group_name`."""
        self.ldif_connection.add(
            f"cn={group_name},{self.group_base}",
            object_class=["top", "posixGroup"],
            attributes={
                "cn": group_name,
                "gidNumber": "",
            },
        )
        return self.ldif_connection.response

    def get_all_group_info(self, name):
        """Return all group info for a given name."""
        search_result = self.search_group_by_name(name, attributes=["*"])
        if not search_result.found():
            raise Failure(message=f"Group with name {name} not found.")
        return search_result.get_attributes()

    @staticmethod
    def load():
        """Load config from a file."""
        logger.debug("................... Initialising LDAP connection...")
        ldap = LdapConnection()
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
        self.userinfo = userinfo
        self.unique_id = userinfo.unique_id
        logger.debug(f"backend processing: {userinfo.unique_id}")
        if self.exists():
            username = self.get_username()
            primary_group = self.get_primary_group()
            logger.debug(
                f"This user does actually exist. The name is: {username} and the primary group is: {primary_group}"
            )
            self.set_username(username)
            self.primary_group = Group(primary_group)
        else:
            self.set_username(userinfo.username)
            self.primary_group = Group(userinfo.primary_group)

        self.ssh_keys = [key["value"] for key in userinfo.ssh_keys]

    def exists(self):
        """Return whether the user exists on the service.

        If this returns True,  calling `create` should have no effect or raise an error.
        """
        logger.info(f"Check if user exists: {self.unique_id}")
        return LDAP.search_user_by_oidc_uid(self.unique_id, attributes=[]).found()

    def name_taken(self, name):
        """Return whether the username is already taken by another user on the service,
        i.e. if an entry for it exists in the LDAP and it's not mapped to the current oidc uid.

        In 'pre_created' mode, taken means that the username has been mapped to another oidc uid.
        """
        search_result = LDAP.search_user_by_local_username(name, get_unique_id=True)
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
        return LDAP.search_user_by_oidc_uid(
            self.unique_id, attributes=[LDAP.attr_local_uid]
        ).get_attribute(LDAP.attr_local_uid)

    def set_username(self, username):
        """Set local username on the service."""
        self.name = username

    def get_primary_group(self):
        """Check if a user exists based on unique_id and return the primary group name."""
        gid = LDAP.search_user_by_oidc_uid(self.unique_id, attributes=["gidNumber"]).get_attribute(
            "gidNumber"
        )
        return LDAP.search_group_by_gid(gid).get_attribute("cn")

    def get_groups(self):
        """Get a list of names of all service groups that the user belongs to.

        If the user doesn't exist, return an empty list.
        """
        return LDAP.get_user_groups(self.name)

    def get_ldap_entry(self):
        """Get all information about the user stored in LDAP."""
        return LDAP.get_all_user_info(self.unique_id)

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
            if not LDAP.search_user_by_local_username(self.name, get_unique_id=False).found():
                msg = f"Local username {self.name} not found in LDAP for user {self.unique_id}."
                logger.error(msg)
                raise Rejection(
                    message=f"{msg} Please contact an administrator to pre-create this account for you."
                )
            else:
                # we assume that it was checked via name_taken that the username is not already mapped
                LDAP.map_user(self.userinfo, self.name)
        else:  # Mode.FULL_ACCESS
            LDAP.add_user(self.userinfo, self.name, self.primary_group.name)

    def create_tostring(self):
        """Return command (LDIF) for creating user in LDAP.
        If in pre_created mode and a local username exists, only map the user to it.
        """
        if (
            LDAP.mode == Mode.PRE_CREATED
            and LDAP.search_user_by_local_username(self.name, get_unique_id=False).found()
        ):
            return LDAP.map_user_ldif(self.userinfo, self.name)
        return LDAP.add_user_ldif(self.userinfo, self.name, self.primary_group.name)

    def update(self):
        """Update all relevant information about the user on the service.

        If the user doesn't exists, behaviour is undefined.
        """
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
            raise Rejection(message=msg)
        else:  # Mode.FULL_ACCESS
            LDAP.delete_user(self.name)

    def _get_group_lists(self, supplementary_groups=None):
        """Get the names of the groups the user needs to be added to and removed from,
        based on the given supplementary groups and the groups the user is currently in.

        The supplementary_groups MUST also contain the primary group.

        Arguments:
            supplementary_groups (list(Group) | None): list of group names to which the user should belong.

        Returns:
            (list(str), list(str)): list of groups to add, list of groups to remove
        """
        if supplementary_groups is None:
            supplementary_groups_names = []
        else:
            supplementary_groups_names = [group.name for group in supplementary_groups]
        current_groups = self.get_groups()
        groups_to_add = list(set(supplementary_groups_names) - set(current_groups))
        groups_to_remove = list(set(current_groups) - set(supplementary_groups_names))
        return groups_to_add, groups_to_remove

    def mod(self, supplementary_groups=None):
        """Modify the user on the service.

        The state of the user with respect to the provided Arguments after calling this function
        should not depend on the state the user had previously.

        If the user doesn't exists, behaviour is undefined.

        Arguments:
            supplementary_groups (list[Group], optional): the list of groups the user must be part of. Defaults to None.
        """
        groups_to_add, groups_to_remove = self._get_group_lists(supplementary_groups)
        if groups_to_add == [] and groups_to_remove == []:
            logger.debug(
                f"Empty add & remove group lists for user {self.name}. Nothing to do here."
            )
            return [], []

        if LDAP.mode == Mode.READ_ONLY:
            msg = f"LDAP backend in read_only mode, local username {self.name} cannot be added to given groups."
            logger.warning(msg)
            return [], []
        elif LDAP.mode == Mode.PRE_CREATED:
            msg = "LDAP backend in pre_created mode, group {} does not exist so user {} cannot be added to it."
            added_groups = []
            removed_groups = []
            for group in groups_to_add:
                if Group(group).exists():
                    LDAP.add_user_to_group(self.name, group)
                    added_groups.append(group)
                else:
                    logger.warning(msg.format(group, self.name))
            for group in groups_to_remove:
                if Group(group).exists():
                    LDAP.remove_user_from_group(self.name, group)
                    removed_groups.append(group)
                else:
                    logger.warning(msg.format(group, self.name))
            return added_groups, removed_groups
        else:  # Mode.FULL_ACCESS
            for group in groups_to_add:
                LDAP.add_user_to_group(self.name, group)
            for group in groups_to_remove:
                LDAP.remove_user_from_group(self.name, group)
            return groups_to_add, groups_to_remove

    def mod_tostring(self, supplementary_groups=None):
        """LDIF representation for modifying a user to be added and removed from given groups.

        Arguments:
            supplementary_groups (list[Group], optional): the list of groups the user must be part of. Defaults to None.

        Returns:
            str: LDIF containing all user modifications
        """
        groups_to_add, groups_to_remove = self._get_group_lists(supplementary_groups)
        if groups_to_add == [] and groups_to_remove == []:
            logger.debug(
                f"Empty add & remove group lists for user {self.name}. Nothing to do here."
            )
            return ""
        ldifs = []
        for group in groups_to_add:
            ldifs.append(LDAP.add_user_to_group_ldif(self.name, group))
        for group in groups_to_remove:
            ldifs.append(LDAP.remove_user_from_group_ldif(self.name, group))
        return "\n\n".join(ldifs)

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

    def create_tostring(self):
        return LDAP.add_group_ldif(self.name)

    def get_ldap_entry(self):
        """Get all information about the group stored in LDAP."""
        return LDAP.get_all_group_info(self.name)
