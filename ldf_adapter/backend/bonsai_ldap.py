"""LDAP backend for pre-created accounts based on the bonsai libraries"""

from typing import Optional, cast, Generator
from enum import Enum, auto
import pprint
import logging

from bonsai import ConnectionError, TimeoutError, LDAPClient, LDAPSearchScope, LDAPEntry, LDAPModOp, LDAPError
from bonsai.pool import ThreadedConnectionPool
from bonsai.ldapconnection import BaseLDAPConnection

from ldf_adapter.config import CONFIG
from ldf_adapter.backend.generic import User as BaseUser
from ldf_adapter.backend.generic import Group as BaseGroup
from ldf_adapter.results import Failure, Rejection

from contextlib import contextmanager

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


class BonsaiLDAPSearchResult:
    def __init__(self, search_result):
        logger.debug(f"search result: {pprint.pformat(search_result)}")
        self._search_result = search_result

    def found(self) -> bool:
        return bool(self._search_result)

    def get_attribute(self, attribute_name: str) -> Optional[str]:
        try:
            value = self._search_result[0][attribute_name]
        except IndexError as ierr:
            logger.warning(f"Attribute {attribute_name} not found in response: {ierr}")
            return None
        except KeyError as kerr:
            logger.warning(f"Attribute {attribute_name} not found in response: {kerr}")
            return None
        if isinstance(value, list):
            return value[0]
        else:
            return value

    def get_attributes(self) -> Optional[dict]:
        try:
            attributes = self._search_result[0]
        except IndexError as ierr:
            logger.warning(f"No attributes found in search result: {ierr}")
            return None
        except KeyError as kerr:
            logger.warning(f"No attributes found in search result: {kerr}")
            return None

        for key, value in attributes.items():
            if isinstance(value, list):
                attributes[key] = value[0]
            else:
                attributes[key] = value
        return attributes

    def get_attribute_for_all(self, attribute_name: str) -> list:
        all_entries = []
        for entry in self._search_result:
            try:
                value = entry[attribute_name]
            except KeyError as kerr:
                logger.warning(f"Attribute {attribute_name} not found in response: {kerr}")
                return []
            if isinstance(value, list):
                value = value[0]
            all_entries.append(value)
        return all_entries


class BonsaiLDAPClient:
    # class-level pool, initialized once
    pool = cast(ThreadedConnectionPool, None)

    def __init__(self):
        # Read comfiguration
        self.user_base = CONFIG.backend.bonsai_ldap.user_base
        self.group_base = CONFIG.backend.bonsai_ldap.group_base
        self.attr_oidc_uid = CONFIG.backend.bonsai_ldap.attribute_oidc_uid
        self.attr_local_uid = CONFIG.backend.bonsai_ldap.attribute_local_uid
        self.mode = Mode.from_str(CONFIG.backend.bonsai_ldap.mode)
        self.shell = CONFIG.backend.bonsai_ldap.shell
        self.home_base = CONFIG.backend.bonsai_ldap.home_base
        self.uid_min = CONFIG.backend.bonsai_ldap.uid_min
        self.uid_max = CONFIG.backend.bonsai_ldap.uid_max
        self.gid_min = CONFIG.backend.bonsai_ldap.gid_min
        self.gid_max = CONFIG.backend.bonsai_ldap.gid_max

        # create one threaded pool with 10 connections per class
        if not self.pool:
            url = f"ldap://{CONFIG.backend.bonsai_ldap.host}:{CONFIG.backend.bonsai_ldap.port}"
            client = LDAPClient(url=url, tls=CONFIG.backend.bonsai_ldap.tls)
            client.set_credentials(
                "SIMPLE",
                user=CONFIG.backend.bonsai_ldap.admin_user,
                password=CONFIG.backend.bonsai_ldap.admin_password,
            )
            self.pool = ThreadedConnectionPool(
                client, maxconn=CONFIG.backend.bonsai_ldap.connection_pool_size
            )
            self._init_nextuidgid()

    @contextmanager
    def _spawn_connection(self) -> Generator[BaseLDAPConnection, None, None]:
        idle_count = self.pool.idle_connection
        connection = None

        for retry in range(idle_count + 1):
            with self.pool.spawn() as conn:
                try:
                    result = conn.whoami(timeout=5)
                    connection = conn
                except TimeoutError as err:
                    msg = f"Attempt to spawn a connection failed after {retry} attempts"
                    logger.error(f"{msg}: {err}")
                    conn.close()
                    if retry == idle_count:
                        raise Failure(message=msg) from err

        yield connection

    def _add(self, ldap_entry: LDAPEntry) -> bool:
        with self._spawn_connection() as connection:
            return connection.add(ldap_entry)

    def _change_attributes(self, dn: str, changes: dict) -> bool:
        with self._spawn_connection() as connection:
            entry = LDAPEntry(dn=dn, conn=connection)
            for attribute, (optype, *values) in changes.items():
                entry.change_attribute(attribute, optype, *values)
            return entry.modify()

    def _delete(
        self, dname: str, timeout: Optional[float] = None, recursive: bool = False
    ) -> bool:
        with self._spawn_connection() as connection:
            return connection.delete(dname=dname, timeout=timeout, recursive=recursive)

    def _entry_to_ldif(self, entry: LDAPEntry):
        lines = [f"dn: {entry.dn}"]
        for attr, values in entry.items(exclude_dn=True):
            if not isinstance(values, list):
                values = [values]
            for value in values:
                lines.append(f"{attr}: {value}")
        return "\n".join(lines)

    def _init_nextuidgid(self):
        """
        Initialise uidNext and gidNext entries in FULL_ACCESS mode
        with values starting in configured range.
        """
        if self.mode == Mode.FULL_ACCESS:
            try:
                search_uid = self.search_next_uid()
                if not search_uid.found():
                    first_uid_entry = LDAPEntry(f"cn=uidNext,{self.user_base}")
                    first_uid_entry["objectClass"] = ["uidNext"]
                    first_uid_entry["cn"] = "uidNext"
                    first_uid_entry["uidNumber"] = self.uid_min
                    self._add(first_uid_entry)
                    search_uid = self.search_next_uid()
                else:
                    logger.debug(
                        f"uidNext already initialised: {search_uid.get_attribute('uidNumber')}."
                    )

                search_gid = self.search_next_gid()
                if not search_gid.found():
                    first_gid_entry = LDAPEntry(f"cn=gidNext,{self.group_base}")
                    first_gid_entry["objectClass"] = ["gidNext"]
                    first_gid_entry["cn"] = "gidNext"
                    first_gid_entry["gidNumber"] = self.gid_min
                    self._add(first_gid_entry)
                    search_gid = self.search_next_gid()
                else:
                    logger.debug(
                        f"gidNext already initialised: {search_gid.get_attribute('gidNumber')}."
                    )

            except Exception as err:
                msg = "Failed to add entries in LDAP when tracking available UID and GID values"
                logger.error(f"{msg}: {err}")
                raise Failure(message=msg) from err

    def _search(
        self, base: str, scope: LDAPSearchScope, filter_exp: str, attrlist: list[str]
    ) -> BonsaiLDAPSearchResult:
        with self._spawn_connection() as connection:
            logger.debug(f"base, scope, filter_exp, attrlist: {pprint.pformat((base, scope, filter_exp, attrlist))}")
            return BonsaiLDAPSearchResult(
                connection.search(
                    base=base,
                    scope=scope,
                    filter_exp=filter_exp,
                    attrlist=attrlist,
                )
            )

    def search_user_by_oidc_uid(
        self, oidc_uid, attributes=[]
    ) -> BonsaiLDAPSearchResult:
        return self._search(
            base=self.user_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp=f"(&({self.attr_oidc_uid}={oidc_uid})(objectClass=inetOrgPerson)(objectClass=posixAccount))",
            attrlist=attributes,
        )

    def search_user_by_local_username(
        self, username, get_unique_id=False
    ) -> BonsaiLDAPSearchResult:
        return self._search(
            base=self.user_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp=f"(&({self.attr_local_uid}={username})(objectClass=inetOrgPerson)(objectClass=posixAccount))",
            attrlist=(
                [self.attr_local_uid, self.attr_oidc_uid]
                if get_unique_id
                else [self.attr_local_uid]
            ),
        )

    def search_group_by_gid(self, gid) -> BonsaiLDAPSearchResult:
        return self._search(
            base=self.group_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp=f"(&(gidNumber={gid})(objectClass=posixGroup))",
            attrlist=["cn"],
        )

    def search_group_by_name(self, group_name) -> BonsaiLDAPSearchResult:
        return self._search(
            base=self.group_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp=f"(&(cn={group_name})(objectClass=posixGroup))",
            attrlist=[],
        )

    def search_groups_by_member(self, username) -> BonsaiLDAPSearchResult:
        return self._search(
            base=self.group_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp=f"(&(memberUid={username})(objectClass=posixGroup))",
            attrlist=["cn", "gidNumber"],
        )

    def search_next_uid(self):
        return self._search(
            base=self.user_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp="(&(cn=uidNext)(objectClass=uidNext))",
            attrlist=["uidNumber"],
        )

    def search_next_gid(self):
        return self._search(
            base=self.group_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp="(&(cn=gidNext)(objectClass=gidNext))",
            attrlist=["gidNumber"],
        )

    def get_next_uid(self):
        result = self.search_next_uid()
        if not result.found():
            raise Failure(message="No UID found in LDAP search.")

        uid = result.get_attribute("uidNumber")

        if uid is None:
            raise Failure(message="uidNumber attribute is missing from LDAP entry")

        try:
            uid = int(uid)
        except Exception as err:
            logger.error(f"Could not convert uidNumber to int: {err}")
            raise Failure(message="Could not parse uidNumber from LDAP") from err

        # find nearest free uid
        next_uid = uid
        while self.is_uid_taken(next_uid) and next_uid <= self.uid_max:
            next_uid += 1
        # make sure nearest free uid still in allowed range
        if next_uid > self.uid_max:
            logger.debug(f"next uid: {next_uid} - uid max: {self.uid_max} - no free uid found in the allowed uid range.")
            raise Failure(message="No available UIDs left in configured range.")
        return next_uid

    def get_next_gid(self):
        result = self.search_next_gid()
        if not result.found():
            raise Failure(message="No GID found in LDAP search.")

        gid = result.get_attribute("gidNumber")

        if gid is None:
            raise Failure(message="gidNumber attribute is missing from LDAP entry")

        try:
            gid = int(gid)
        except Exception as err:
            logger.error(f"Could not convert gidNumber to int: {err}")
            raise Failure(message="Could not parse gidNumber from LDAP") from err

        # make sure gid is not taken already and still in allowed range
        next_gid = gid
        while self.is_gid_taken(next_gid) and next_gid <= self.gid_max:
            next_gid += 1

        # make sure gid still in allowed range
        if next_gid > self.gid_max:
            logger.debug(f"next gid: {next_gid} - gid max: {self.gid_max} - no free gid found in the allowed gid range.")
            raise Failure(message="No available GIDs left in configured range.")
        return next_gid

    def is_gid_taken(self, gid: int) -> bool:
        return self._search(
            base=self.group_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp=f"(&(gidNumber={gid})(objectClass=posixGroup))",
            attrlist=[],
        ).found()

    def is_uid_taken(self, uid: int) -> bool:
        return self._search(
            base=self.user_base,
            scope=LDAPSearchScope.ONELEVEL,
            filter_exp=f"(&(uidNumber={uid})(objectClass=posixAccount))",
            attrlist=[],
        ).found()

    def get_user_groups(self, local_username) -> list:
        """Get all groups a user belongs to.

        Returns a list of names.
        """
        logger.debug(f"Searching groups for user {local_username} in LDAP.")
        result = self.search_groups_by_member(local_username)
        if not result.found():
            return []
        logger.debug(f"User {local_username} belongs to the group(s) {result.get_attribute_for_all('cn')}.")
        return result.get_attribute_for_all("cn")

    def _create_group_entry(self, group_name, existing_gid=None) -> LDAPEntry:
        new_group_entry = LDAPEntry(f"cn={group_name},{self.group_base}")
        new_group_entry["objectClass"] = ["top", "posixGroup"]
        new_group_entry["cn"] = group_name
        new_group_entry["gidNumber"] = existing_gid or self.get_next_gid()
        return new_group_entry

    def add_group(self, group_name) -> bool:
        new_group_entry = self._create_group_entry(group_name)
        logger.debug(f"LDIF add group: {self._entry_to_ldif(new_group_entry)}")
        try:
            logger.debug(f"An entry will be added for the group {group_name}.")
            return self._add(ldap_entry=new_group_entry)
        except Exception as err:
            msg = f"Failed to add an LDAP entry for the group {group_name}"
            logger.error(f"{msg}: {err}")
            raise Failure(message=msg) from err

    def add_group_ldif(self, group_name, existing_gid=None) -> str:
        new_group_entry = self._create_group_entry(group_name, existing_gid)
        return self._entry_to_ldif(new_group_entry)

    def _create_user_entry(
        self, userinfo, local_username: str, primary_group_name: str
    ) -> LDAPEntry:
        new_user_entry = LDAPEntry(f"uid={local_username},{self.user_base}")
        new_user_entry["objectClass"] = ["top", "inetOrgPerson", "posixAccount"]
        new_user_entry["uidNumber"] = self.get_next_uid()
        new_user_entry["gidNumber"] = self.search_group_by_name(
            primary_group_name
        ).get_attribute("gidNumber")
        new_user_entry["homeDirectory"] = f"{self.home_base}/{local_username}"
        new_user_entry["loginShell"] = self.shell

        new_user_entry[self.attr_local_uid] = local_username
        new_user_entry[self.attr_oidc_uid] = userinfo.unique_id

        if userinfo.family_name is not None:
            new_user_entry["sn"] = userinfo.family_name
        if userinfo.given_name is not None:
            new_user_entry["givenName"] = userinfo.given_name
        if userinfo.full_name is not None:
            new_user_entry["cn"] = userinfo.full_name
        if userinfo.email is not None:
            new_user_entry["mail"] = userinfo.email

        return new_user_entry

    def add_user(self, userinfo, local_username: str, primary_group_name: str) -> bool:
        new_user_entry = self._create_user_entry(
            userinfo, local_username, primary_group_name
        )
        logger.debug(f"LDIF add user: {self._entry_to_ldif(new_user_entry)}")
        try:
            logger.debug(
                f"An entry will be added for the user {local_username}."
            )
            return self._add(ldap_entry=new_user_entry)
        except Exception as err:
            msg = f"Failed to add an entry for the user {local_username}"
            logger.error(f"{msg}: {err}")
            raise Failure(message=msg) from err

    def add_user_ldif(
        self, userinfo, local_username: str, primary_group_name: str
    ) -> str:
        new_user_entry = self._create_user_entry(
            userinfo, local_username, primary_group_name
        )
        return self._entry_to_ldif(new_user_entry)

    def add_user_to_group(self, local_username: str, group_name: str) -> bool:
        """
        Add a user to group.
        If either of them does not exist, a Failure exception is raised.
        """
        try:
            changes = {"memberUid": (LDAPModOp.ADD, local_username)}
            dn = f"cn={group_name},{self.group_base}"
            return self._change_attributes(dn, changes)

        except Exception as err:
            msg = f"Failed to modify the LDAP entry for the user {local_username} and the group {group_name}"
            logger.error(f"{msg}: {err}")
            raise Failure(message=msg) from err

    def add_user_to_group_ldif(self, local_username: str, group_name: str) -> str:
        """LDIF representation for adding a user to group."""
        ldif_lines = [f"dn: cn={group_name},{self.group_base}"]
        ldif_lines.append("changetype: modify")
        ldif_lines.append("add: memberUid")
        ldif_lines.append(f"memberUid: {local_username}")
        return "\n".join(ldif_lines)

    def remove_user_from_group(self, local_username: str, group_name: str) -> bool:
        """
        Remove a user from group.
        If either of them does not exist, a Failure exception is raised.
        """
        try:
            changes = {"memberUid": (LDAPModOp.DELETE, local_username)}
            dn = f"cn={group_name},{self.group_base}"
            return self._change_attributes(dn, changes)

        except Exception as err:
            msg = f"Failed to modify the LDAP entry for user {local_username} and group {group_name}"
            logger.error(f"{msg}: {err}")
            raise Failure(message=msg) from err

    def remove_user_from_group_ldif(self, local_username: str, group_name: str) -> str:
        """LDIF representation for removing a user from a group."""
        ldif_lines = [f"dn: cn={group_name},{self.group_base}"]
        ldif_lines.append("changetype: modify")
        ldif_lines.append("delete: memberUid")
        ldif_lines.append(f"memberUid: {local_username}")
        return "\n".join(ldif_lines)

    def delete_user(self, local_username: str) -> bool:
        try:
            logger.debug(
                f"LDAP entry for user {local_username} will be deleted."
            )
            return self._delete(f"uid={local_username},{self.user_base}")
        except Exception as err:
            msg = (
                f"Failed to delete the LDAP entry for the user {local_username}"
            )
            logger.error(f"{msg}: {err}")
            raise Failure(message=msg) from err

    def map_user(self, userinfo, local_username: str) -> bool:
        """Update the LDAP entry for given `local_username` with mapped oidc uid.
        If user doesn't exist, a Failure exception is raised.
        """
        try:
            changes = {self.attr_oidc_uid: (LDAPModOp.REPLACE, userinfo.unique_id)}
            dn = f"uid={local_username},{self.user_base}"
            return self._change_attributes(dn, changes)

        except LDAPError as err:
            msg = f"Failed to modify the LDAP entry for the user {local_username}"
            logger.error(f"{msg}: {err}")
            raise Failure(message=msg) from err

    def map_user_ldif(self, userinfo, local_username: str) -> str:
        """LDIF representation for updating the LDAP entry for given `local_username` with mapped oidc uid.
        If user doesn't exist, a Failure exception is raised.
        """
        try:
            ldif_lines = [f"dn: uid={local_username},{self.user_base}"]
            ldif_lines.append("changetype: modify")
            ldif_lines.append(f"replace: {self.attr_oidc_uid}")
            ldif_lines.append(f"{self.attr_oidc_uid}: {userinfo.unique_id}")
            return "\n".join(ldif_lines)
        except Exception as err:
            msg = f"Failed to get LDIF to modify the entry for user {local_username} with uid {userinfo.unique_id}"
            logger.error(f"{msg}: {err}")
            raise Failure(message=msg) from err

    def update_user(self, userinfo, local_username: str) -> bool:
        """Update the LDAP entry for given `local_username` with all information in `userinfo`.
        If user doesn't exist, nothing happens.
        """

        try:
            changes = {
                "homeDirectory": (
                    LDAPModOp.REPLACE,
                    f"{self.home_base}/{local_username}",
                ),
                "loginShell": (LDAPModOp.REPLACE, self.shell),
                self.attr_local_uid: (LDAPModOp.REPLACE, local_username),
                self.attr_oidc_uid: (LDAPModOp.REPLACE, userinfo.unique_id),
            }

            if userinfo.family_name is not None:
                changes["sn"] = (LDAPModOp.REPLACE, userinfo.family_name)
            if userinfo.given_name is not None:
                changes["givenName"] = (LDAPModOp.REPLACE, userinfo.given_name)
            if userinfo.full_name is not None:
                changes["cn"] = (LDAPModOp.REPLACE, userinfo.full_name)
            if userinfo.email is not None:
                changes["mail"] = (LDAPModOp.REPLACE, userinfo.email)

            dn = f"uid={local_username},{self.user_base}"
            return self._change_attributes(dn, changes)

        except LDAPError as err:
            msg = f"Failed to modify the entry for user {local_username}"
            logger.error(f"{msg}: {err}")
            raise Failure(message=msg) from err


class User(BaseUser):

    ldap_client: "BonsaiLDAPClient"

    def __init__(self, userinfo, **hooks):
        """
        Arguments:
        userinfo -- (type: UserInfo)
        """
        self.ldap_client = BonsaiLDAPClient()
        super().__init__(userinfo, **hooks)
        self.userinfo = userinfo
        self.unique_id = userinfo.unique_id

        if self.exists():
            username = self.get_username()
            primary_group = self.get_primary_group()
            logger.debug(
                f"This user does actually exist. The name is: {username} and the primary group is: {primary_group}"
            )
            self.set_username(username)
            if primary_group is None:
                raise Failure(message=f"Primary group is missing for user {username}.")
            self.primary_group = Group(primary_group)
        else:
            self.set_username(userinfo.username)
            self.primary_group = Group(userinfo.primary_group)

        self.ssh_keys = [key["value"] for key in userinfo.ssh_keys]
        self.post_create_script = CONFIG.backend.bonsai_ldap.post_create_script

    def exists(self):
        logger.debug(f"Check if user exists.")
        if self.ldap_client.search_user_by_oidc_uid(
            self.unique_id, attributes=[]
        ).found():
            logger.debug(f"User {self.userinfo.username} exists.")
            return True
        logger.debug(f"User {self.userinfo.username} does not exist.")
        return False

    def name_taken(self, name):
        result = self.ldap_client.search_user_by_local_username(
            name, get_unique_id=True
        )

        if result.found():
            oidc_uid = result.get_attribute(self.ldap_client.attr_oidc_uid)
            if self.ldap_client.mode == Mode.PRE_CREATED and oidc_uid is None:
                return False
            return oidc_uid != self.unique_id
        else:
            return False

    def create(self):
        """Create the user on the LDAP server using bonsai."""

        if self.ldap_client.mode == Mode.READ_ONLY:
            if self.exists():
                msg = f"LDAP backend in read_only mode, the entry for user {self.name} can not be modified."
                logger.error(msg)
            else:
                msg = f"LDAP backend in read_only mode, the entry for user {self.name} can not be added."
                logger.error(msg)
            raise Rejection(
                message=f"{msg} Please contact your administrator to create an account for you."
            )

        elif self.ldap_client.mode == Mode.PRE_CREATED:
            if not self.ldap_client.search_user_by_local_username(
                self.name, get_unique_id=False
            ).found():
                msg = f"LDAP backend in pre_created mode - User {self.name} not found in LDAP."
                logger.error(msg)
                msg = f"New entry can not be added in pre_created mode."
                logger.debug(msg)
                raise Rejection(
                    message=f"{msg} Please contact your administrator to pre-create this account for you."
                )
            else:
                msg = f"LDAP backend in pre_created mode - User {self.name} found in LDAP."
                logger.debug(msg)
                self.ldap_client.map_user(self.userinfo, self.name)

        else:  # Mode.FULL_ACCESS
            self.ldap_client.add_user(self.userinfo, self.name, self.primary_group.name)

    def create_tostring(self):
        """Return command (LDIF) for creating user in LDAP.
        If in pre_created mode and a local username exists, only map the user to it.
        """

        if self.ldap_client.mode == Mode.PRE_CREATED:
            if self.ldap_client.search_user_by_local_username(
                self.name, get_unique_id=False
            ):
                return self.ldap_client.map_user_ldif(self.userinfo, self.name)

        return self.ldap_client.add_user_ldif(
            self.userinfo, self.name, self.primary_group.name
        )

    def update(self):
        """Update all relevant information about the user.
        If the user doesn't exist, behaviour is undefined.
        """

        if self.ldap_client.mode == Mode.READ_ONLY:
            msg = f"LDAP backend in read_only mode, entry for user {self.name} cannot be updated."
            logger.warning(msg)

        elif self.ldap_client.mode == Mode.PRE_CREATED:
            msg = f"LDAP backend in pre_created mode, entry for user {self.name} cannot be updated."
            logger.warning(msg)

        else:  # Mode.FULL_ACCESS
            msg = f"LDAP backend in full access mode, entry for user {self.name} can be updated."
            logger.debug(msg)
            self.ldap_client.update_user(self.userinfo, self.name)

    def delete(self):
        """Delete the user on the service.
        If the user doesn't exist, do nothing or raise an error.
        """
        if self.ldap_client.mode == Mode.READ_ONLY:
            msg = f"LDAP backend in read_only mode, entry for user {self.name} cannot be deleted."
            logger.error(msg)
            raise Rejection(message=msg)
        elif self.ldap_client.mode == Mode.PRE_CREATED:
            msg = f"LDAP backend in pre_created mode, entry for user {self.name} cannot be deleted."
            logger.error(msg)
            raise Rejection(message=msg)
        else:  # Mode.FULL_ACCESS
            self.ldap_client.delete_user(self.name)

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

        logger.debug(f"Current groups: {current_groups}")
        logger.debug(f"Supplementary groups: {supplementary_groups_names}")
        logger.debug(f"Groups to add - only found in supplementary groups: {groups_to_add}")
        logger.debug(f"Groups to remove - only found in current groups: {groups_to_remove}")

        return groups_to_add, groups_to_remove

    def mod(self, supplementary_groups=None):
        """Modify the user on the service.

        The state of the user with respect to the provided Arguments after calling this function
        should not depend on the state the user had previously.

        If the user doesn't exist, behaviour is undefined.

        Arguments:
            supplementary_groups (list[Group], optional): the list of groups the user must be part of. Defaults to None.
        """
        groups_to_add, groups_to_remove = self._get_group_lists(supplementary_groups)
        if not groups_to_add and not groups_to_remove:
            logger.debug(
                f"Lists of groups to add and groups to remove are empty for user {self.name}. Nothing to do here."
            )
            return [], []

        if self.ldap_client.mode == Mode.READ_ONLY:
            msg = f"LDAP backend in read_only mode, user {self.name} cannot be added to or removed from a given group."
            logger.warning(msg)
            return [], []
        elif self.ldap_client.mode == Mode.PRE_CREATED:
            msg = "LDAP backend in pre_created mode, group {} does not exist so user {} cannot be added to or removed from that group."
            added_groups = []
            removed_groups = []
            for group in groups_to_add:
                if Group(group).exists():
                    self.ldap_client.add_user_to_group(self.name, group)
                    added_groups.append(group)
                    logger.debug(f"User {self.name} will be added to the group {group}.")
                else:
                    logger.warning(msg.format(group, self.name))
            for group in groups_to_remove:
                if Group(group).exists():
                    self.ldap_client.remove_user_from_group(self.name, group)
                    removed_groups.append(group)
                    logger.debug(f"User {self.name} will be removed from the group {group}.")
                else:
                    logger.warning(msg.format(group, self.name))
            return added_groups, removed_groups
        else:  # Mode.FULL_ACCESS
            for group in groups_to_add:
                msg = f"LDAP backend in full_access mode, user {self.name} will be added to the group {group}."
                logger.debug(msg)
                self.ldap_client.add_user_to_group(self.name, group)
            for group in groups_to_remove:
                msg = f"LDAP backend in full_access mode, local username {self.name} will be removed from the group {group}."
                logger.debug(msg)
                self.ldap_client.remove_user_from_group(self.name, group)
            return groups_to_add, groups_to_remove

    def mod_tostring(self, supplementary_groups=None) -> str:
        """LDIF representation for modifying a user to be added and removed from given groups.

        Arguments:
            supplementary_groups (list[Group], optional): the list of groups the user must be part of. Defaults to None.

        Returns:
            str: LDIF containing all user modifications
        """
        groups_to_add, groups_to_remove = self._get_group_lists(supplementary_groups)
        if not groups_to_add and not groups_to_remove:
            logger.debug(
                f"Lists of groups to add and groups to remove are empty for user {self.name}. Nothing to do here."
            )
            return ""
        ldifs = []
        for group in groups_to_add:
            ldifs.append(self.ldap_client.add_user_to_group_ldif(self.name, group))
        for group in groups_to_remove:
            ldifs.append(self.ldap_client.remove_user_from_group_ldif(self.name, group))
        return "\n\n".join(ldifs)

    def get_groups(self):
        """Get a list of names of all service groups that the user belongs to.

        If the user doesn't exist, return an empty list.
        """
        return self.ldap_client.get_user_groups(self.name)

    def install_ssh_keys(self):
        """Install users SSH keys on the service.

        No other SSH keys should be active after calling this function.

        If the user doesn't exist, behaviour is undefined.
        """
        # TODO: use ldapPublicKey schema (sshPublicKey attribute) for storing ssh key in LDAP
        pass

    def uninstall_ssh_keys(self):
        """Uninstall the users SSH keys on the service.

        This must uninstall all SSH keys installed with `install_ssh_keys`. It may uninstall SSH
        keys installed by other means.

        If the user doesn't exist, behaviour is undefined.
        """
        # TODO: use ldapPublicKey schema (sshPublicKey attribute) for storing ssh key in LDAP
        pass

    def get_username(self):
        """Check if a user exists based on unique_id and return the name"""
        return self.ldap_client.search_user_by_oidc_uid(
            oidc_uid=self.unique_id, attributes=[self.ldap_client.attr_local_uid]
        ).get_attribute(self.ldap_client.attr_local_uid)

    def set_username(self, username):
        """Set local username on the service."""
        self.name = username

    def get_primary_group(self):
        """Check if a user exists based on unique_id and return the primary group name."""
        gid = self.ldap_client.search_user_by_oidc_uid(
            oidc_uid=self.unique_id, attributes=["gidNumber"]
        ).get_attribute("gidNumber")
        return self.ldap_client.search_group_by_gid(gid).get_attribute("cn")

    def get_ldap_entry(self):
        """Get all information about a user based on the unique_id."""
        search_result = self.ldap_client.search_user_by_oidc_uid(
            self.unique_id, attributes=[]
        )
        if not search_result.found():
            raise Failure(message=f"User with unique_id {self.unique_id} not found.")
        logger.debug(f"User entry: {pprint.pformat(search_result.get_attributes())}")
        return search_result.get_attributes()


class Group(BaseGroup):

    ldap_client: "BonsaiLDAPClient"

    def __init__(self, name: str):
        self.ldap_client = BonsaiLDAPClient()
        super().__init__(name)
        self.name = name

    def exists(self):
        """Return whether the group already exists."""
        logger.debug(f"Check if group exists: {self.name}")
        if self.ldap_client.search_group_by_name(self.name).found():
            logger.debug(f"Group {self.name} exists.")
            return True
        logger.debug(f"Group {self.name} does not exist.")
        return False

    def create(self):
        """Create the group on the service.

        If the group already exists, nothing happens.
        """
        if self.exists():
            logger.debug(f"Group {self.name} already exists and cannot be added.")
            return False
        elif self.ldap_client.mode == Mode.READ_ONLY:
            logger.warning(
                f"LDAP backend in read_only mode, new entry cannot be added for group {self.name}."
            )
            return False
        elif self.ldap_client.mode == Mode.PRE_CREATED:
            logger.warning(
                f"LDAP backend in pre_created mode, new entry cannot be added for group {self.name}."
            )
            return False
        else:  # Mode.FULL_ACCESS
            return self.ldap_client.add_group(self.name)

    def create_tostring(self):
        # try to find existing group to get the gidNumber, if group does not exist, gidNext is used
        existing_group = self.ldap_client.search_group_by_name(self.name)

        return self.ldap_client.add_group_ldif(
            self.name, existing_gid=existing_group.get_attribute("gidNumber")
        )

    def get_ldap_entry(self):
        """Get all information about a group based on the group name."""
        search_result = self.ldap_client.search_group_by_name(self.name)
        if not search_result.found():
            raise Failure(message=f"Group with name {self.name} not found.")
        logger.debug(f"Group entry: {search_result.get_attributes()}")
        return search_result.get_attributes()
