from dataclasses import dataclass, fields
from typing import Optional
import sqlite3
import json
import logging
from pathlib import Path

from ..results import Failure, FatalError
from ..utils import sql_command_create_table, sql_command_insert_to_table, sql_command_update_table

logger = logging.getLogger(__name__)


@dataclass
class PendingUser:
    """Data model for storing information on a user pending approval."""

    unique_id: str
    sub: str
    iss: str
    email: Optional[str]
    full_name: Optional[str]
    username: str
    state: str
    cmd: str
    infodict: dict


@dataclass
class PendingGroup:
    """Data model for storing groups of a user pending approval."""

    name: str
    state: str
    cmd: str
    infodict: dict


@dataclass
class PendingMemberships:
    """Data model for storing group memberships of a user pending approval."""

    unique_id: str
    supplementary_groups: list
    removal_groups: list
    state: str
    cmd: str
    infodict: dict


class PendingDB:
    """Generic class to manage users (and groups) in states associated with the approval workflow."""

    def add_user(self, user: PendingUser) -> bool:
        """Add a new entry for a user. Returns False if entry already exists."""
        return False

    def remove_user(self, unique_id: str) -> None:
        """Remove user entry for unique_id."""
        pass

    def get_user(self, unique_id: str) -> Optional[PendingUser]:
        """Get a user entry that is up for approval by the user's unique_id."""
        return None

    def get_user_by_username(self, username: str) -> Optional[PendingUser]:
        """Get a user entry by the local username."""
        return None

    def reject_user(self, unique_id: str) -> None:
        """Change the state of user given by unique_id from 'pending' to 'rejected'."""
        pass

    def user_is_pending(self, unique_id: str) -> bool:
        """Whether the user deployment was requested and is pending approval."""
        return False

    def user_is_rejected(self, unique_id: str):
        """Whether the user deployment was requested and was rejected."""
        return False

    def username_reserved(self, name: str) -> bool:
        """Whether the name is reserved by another user pending approval."""
        return False

    def add_group(self, group: PendingGroup) -> bool:
        """Add a new entry for a group. Returns False if entry already exists."""
        return False

    def remove_group(self, name: str) -> None:
        """Remove group entry for name."""
        pass

    def get_group(self, name: str) -> Optional[PendingGroup]:
        """Get a group entry that is up for approval by the group's name."""
        return None

    def add_memberships(self, membership: PendingMemberships) -> bool:
        """Add a new entry for a user's pending group memberships. Returns False if entry already exists."""
        return False

    def update_memberships(self, membership: PendingMemberships) -> bool:
        """Update a user's pending group memberships by replacing them with the given memberships.
        Returns False if entry did not exist.
        """
        return False

    def remove_memberships(self, unique_id: str) -> None:
        """Remove all pending group memberships of a given user."""
        pass

    def get_memberships(self, unique_id: str) -> Optional[PendingMemberships]:
        """Get a given user's pending group memberships. Returns None if the user is not found."""
        return None


# register the functions for manipulating custom types in sqlite db
sqlite3.register_adapter(dict, lambda x: json.dumps(x).encode("utf-8"))
sqlite3.register_converter("dict", lambda x: json.loads(x.decode("utf-8")))
sqlite3.register_adapter(list, lambda x: json.dumps(x).encode("utf-8"))
sqlite3.register_converter("list", lambda x: json.loads(x.decode("utf-8")))


class SqlitePendingDB(PendingDB):
    """Implementation of PendingDB with sqlite3."""

    def __init__(self, location: str) -> None:
        """Initialise sqlite-based DB for managing users and groups pending approval.

        Args:
            location (str): path to file where DB is stored. Will be created if it does not exist.
        """
        if not Path(location).exists():
            logger.debug("No sqlite DB found at %s, creating it...", location)
            Path(location).parent.mkdir(exist_ok=True)
            create_users_table_cmd = sql_command_create_table(
                data_model=PendingUser, table_name="pending_users", primary_key="unique_id"
            )
            create_groups_table_cmd = sql_command_create_table(
                data_model=PendingGroup, table_name="pending_groups", primary_key="name"
            )
            create_memberships_table_cmd = sql_command_create_table(
                data_model=PendingMemberships,
                table_name="pending_memberships",
                primary_key="unique_id",
            )
            try:
                self.connection = sqlite3.connect(location, detect_types=sqlite3.PARSE_DECLTYPES)
                with self.connection:  # con.commit() is called automatically afterwards on success
                    logger.debug("Creating table: %s", create_users_table_cmd)
                    self.connection.execute(create_users_table_cmd)
                    logger.debug("Successfully created table 'pending_users'.")

                    logger.debug("Creating table: %s", create_groups_table_cmd)
                    self.connection.execute(create_groups_table_cmd)
                    logger.debug("Successfully created table 'pending_groups'.")

                    logger.debug("Creating table: %s", create_memberships_table_cmd)
                    self.connection.execute(create_memberships_table_cmd)
                    logger.debug("Successfully created table 'pending_memberships'.")
            except sqlite3.Error as ex:
                message = f"Pending DB initialisation failed: {ex}"
                logger.error(message)
                raise FatalError(message=message)
        else:
            logger.debug("Existing sqlite DB found at %s. Loading pending data from it.", location)
            self.connection = sqlite3.connect(location, detect_types=sqlite3.PARSE_DECLTYPES)

    def add_user(self, user: PendingUser) -> bool:
        """Add a new entry for a user. Returns False if entry already exists."""
        try:
            with self.connection:
                self.connection.execute(
                    sql_command_insert_to_table(data_model=PendingUser, table_name="pending_users"),
                    tuple(getattr(user, field.name) for field in fields(PendingUser)),
                )
                logger.debug(
                    "Deployment pending for user [%s] with username [%s]. Run cmd to deploy: [%s]",
                    user.unique_id,
                    user.username,
                    user.cmd,
                )
            return True
        except sqlite3.IntegrityError as ex:
            logger.info("User %s already exists in pending db.", user.unique_id)
            return False
        except sqlite3.Error as ex:
            msg = f"Failed to add user {user.unique_id} to pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def remove_user(self, unique_id: str) -> None:
        """Remove user entry for unique_id."""
        sql_del = "delete from pending_users where unique_id=?"
        try:
            with self.connection:
                self.connection.execute(sql_del, [unique_id])
        except sqlite3.Error as ex:
            msg = f"Failed to remove user {unique_id} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def get_user(self, unique_id: str) -> Optional[PendingUser]:
        """Get a user entry that is up for approval by the user's unique_id."""
        sql_get = "select * from pending_users where unique_id=?"
        try:
            with self.connection:
                result = self.connection.execute(sql_get, [unique_id]).fetchall()
                if len(result) == 0:
                    return None
                if len(result) > 1:
                    logger.warning("Multiple entries found in user db for unique_id: %s", unique_id)
                return PendingUser(*result[0])
        except sqlite3.Error as ex:
            msg = f"Failed to get user {unique_id} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def get_user_by_username(self, username: str) -> Optional[PendingUser]:
        """Get an entry by the local username."""
        sql_get = "select * from pending_users where username=?"
        try:
            with self.connection:
                result = self.connection.execute(sql_get, [username]).fetchall()
                if len(result) == 0:
                    return None
                if len(result) > 1:
                    logger.warning("Multiple entries found in user db for username: %s", username)
                return PendingUser(*result[0])
        except sqlite3.Error as ex:
            msg = f"Failed to get user by username {username} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def reject_user(self, unique_id: str) -> None:
        """Change the state of user given by unique_id from 'pending' to 'rejected'."""
        sql_update = "update pending_users set state='rejected' where unique_id=?"
        try:
            with self.connection:
                self.connection.execute(sql_update, [unique_id])
                logger.debug("Deployment request for user [%s] was rejected.", unique_id)
        except sqlite3.Error as ex:
            msg = f"Failed to change state of user {unique_id} to rejected."
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def add_group(self, group: PendingGroup) -> bool:
        """Add a new entry for a group. Returns False if entry already exists."""
        try:
            with self.connection:
                self.connection.execute(
                    sql_command_insert_to_table(
                        data_model=PendingGroup, table_name="pending_groups"
                    ),
                    tuple(getattr(group, field.name) for field in fields(PendingGroup)),
                )
                logger.debug(
                    "Deployment pending for group [%s]. Run cmd to deploy: [%s]",
                    group.name,
                    group.cmd,
                )
            return True
        except sqlite3.IntegrityError as ex:
            logger.info("Group %s already exists in pending db.", group.name)
            return False
        except sqlite3.Error as ex:
            msg = f"Failed to add group {group.name} to pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def remove_group(self, name: str) -> None:
        """Remove group entry for name."""
        sql_del = "delete from pending_groups where name=?"
        try:
            with self.connection:
                self.connection.execute(sql_del, [name])
        except sqlite3.Error as ex:
            msg = f"Failed to remove group {name} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def get_group(self, name: str) -> Optional[PendingGroup]:
        """Get an entry that is up for approval by the group's name."""
        sql_get = "select * from pending_groups where name=?"
        try:
            with self.connection:
                result = self.connection.execute(sql_get, [name]).fetchall()
                if len(result) == 0:
                    return None
                if len(result) > 1:
                    logger.warning("Multiple entries found in group db for name: %s", name)
                return PendingGroup(*result[0])
        except sqlite3.Error as ex:
            msg = f"Failed to get group {name} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def add_memberships(self, membership: PendingMemberships) -> bool:
        """Add a new entry for a user's pending group memberships. Returns False if entry already exists."""
        try:
            with self.connection:
                self.connection.execute(
                    sql_command_insert_to_table(
                        data_model=PendingMemberships, table_name="pending_memberships"
                    ),
                    tuple(getattr(membership, field.name) for field in fields(PendingMemberships)),
                )
                logger.debug(
                    "Deployment pending for user [%s]. Run cmd to add user to groups: [%s]",
                    membership.unique_id,
                    membership.cmd,
                )
            return True
        except sqlite3.IntegrityError as ex:
            logger.info(
                "Memberships entry of user %s already exists in pending db.", membership.unique_id
            )
            return False
        except sqlite3.Error as ex:
            msg = f"Failed to add group memberships for user {membership.unique_id} to pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def update_memberships(self, membership: PendingMemberships) -> bool:
        """Update a user's pending group memberships by replacing them with the given memberships.
        Returns False if entry did not exist.
        """
        try:
            with self.connection:
                self.connection.execute(
                    sql_command_update_table(
                        data_model=PendingMemberships,
                        table_name="pending_memberships",
                        key="unique_id",
                    ),
                    tuple(
                        [getattr(membership, field.name) for field in fields(PendingMemberships)]
                        + [membership.unique_id]
                    ),
                )
                logger.debug(
                    "Updated deployment pending for user [%s]. Run cmd to add user to groups: [%s]",
                    membership.unique_id,
                    membership.cmd,
                )
            return True
        except sqlite3.IntegrityError as ex:
            logger.info(
                "Memberships entry of user %s didn't exist in pending db.", membership.unique_id
            )
            logger.debug(ex)
            return False
        except sqlite3.Error as ex:
            msg = f"Failed to add group memberships for user {membership.unique_id} to pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def remove_memberships(self, unique_id: str) -> None:
        """Remove all pending group memberships of a given user."""
        sql_del = "delete from pending_memberships where unique_id=?"
        try:
            with self.connection:
                self.connection.execute(sql_del, [unique_id])
        except sqlite3.Error as ex:
            msg = f"Failed to remove memberships of user {unique_id} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def get_memberships(self, unique_id: str) -> Optional[PendingMemberships]:
        """Get a given user's pending group memberships."""
        sql_get = "select * from pending_memberships where unique_id=?"
        try:
            result = []
            with self.connection:
                result = self.connection.execute(sql_get, [unique_id]).fetchall()
                if len(result) == 0:
                    return None
                if len(result) > 1:
                    logger.warning(
                        "Multiple entries found in membership db for user: %s", unique_id
                    )
                return PendingMemberships(*result[0])
        except sqlite3.Error as ex:
            msg = f"Failed to get memberships of user {unique_id} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)
