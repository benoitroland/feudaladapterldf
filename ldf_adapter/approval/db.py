import sys
from dataclasses import dataclass
from typing import Optional, List
import sqlite3
import logging

from ..results import Failure

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


@dataclass
class PendingGroup:
    """Data model for storing groups of a user pending approval."""

    name: str
    state: str
    cmd: str


@dataclass
class PendingMembership:
    """Data model for storing a group membership of a user pending approval."""

    unique_id: str
    name: str
    state: str
    cmd: str


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

    def add_membership(self, membership: PendingMembership) -> bool:
        """Add a new entry for a user's membership in a group. Returns False if entry already exists."""
        return False

    def remove_memberships(self, unique_id: str) -> None:
        """Remove all group memberships of a given user."""
        pass

    def get_memberships(self, unique_id: str) -> List[PendingMembership]:
        """Get a given user's group memberships. Returns an empty list if the user is not found."""
        return []


class SqlitePendingDB(PendingDB):
    """Implementation of PendingDB with sqlite3."""

    def __init__(self, location: str) -> None:
        """Initialise sqlite-based DB for managing users and groups pending approval.

        Args:
            location (str): path to file where DB is stored. Will be created if it does not exist.
        """
        try:
            self.connection = sqlite3.connect(location)
            with self.connection:  # con.commit() is called automatically afterwards on success
                # create tables
                self.connection.execute(
                    """create table if not exists pending_users
                            (
                                unique_id text primary key,
                                sub text,
                                iss text,
                                email text,
                                full_name text,
                                username text,
                                state text,
                                cmd text
                            )
                    """
                )
                self.connection.execute(
                    """create table if not exists pending_groups
                            (name text primary key, state text, cmd text)"""
                )
                self.connection.execute(
                    """create table if not exists pending_memberships
                            (
                                unique_id text, name text, state text, cmd text,
                                primary key (unique_id, name)
                            )
                    """
                )
        except sqlite3.Error as ex:
            message = f"Pending DB initialisation failed: {ex}"
            logger.error(message)
            sys.exit(2)

    def add_user(self, user: PendingUser) -> bool:
        """Add a new entry for a user. Returns False if entry already exists."""
        sql_insert = (
            "insert into pending_users"
            "(unique_id, sub, iss, email, full_name, username, state, cmd)"
            " values (?,?,?,?,?,?,?,?)"
        )
        try:
            with self.connection:
                self.connection.execute(
                    sql_insert,
                    (
                        user.unique_id,
                        user.sub,
                        user.iss,
                        user.email,
                        user.full_name,
                        user.username,
                        user.state,
                        user.cmd,
                    ),
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
        sql_insert = "insert into pending_groups(name, state, cmd) values (?,?,?)"
        try:
            with self.connection:
                self.connection.execute(sql_insert, (group.name, group.state, group.cmd))
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

    def add_membership(self, membership: PendingMembership) -> bool:
        """Add a new entry for a user's membership in a group. Returns False if entry already exists."""
        sql_insert = "insert into pending_memberships(unique_id, name, state, cmd) values (?,?,?,?)"
        try:
            with self.connection:
                self.connection.execute(
                    sql_insert,
                    (membership.unique_id, membership.name, membership.state, membership.cmd),
                )
                logger.debug(
                    "Deployment pending for user [%s]. Run cmd to add user to groups: [%s]",
                    membership.unique_id,
                    membership.cmd,
                )
            return True
        except sqlite3.IntegrityError as ex:
            logger.info(
                "Membership of user %s to group %s already exists in pending db.",
                membership.unique_id,
                membership.name,
            )
            return False
        except sqlite3.Error as ex:
            msg = f"Failed to add group membership for user {membership.unique_id} in group {membership.name} to pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def remove_memberships(self, unique_id: str) -> None:
        """Remove all group memberships of a given user."""
        sql_del = "delete from pending_memberships where unique_id=?"
        try:
            with self.connection:
                self.connection.execute(sql_del, [unique_id])
        except sqlite3.Error as ex:
            msg = f"Failed to remove memberships of user {unique_id} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)

    def get_memberships(self, unique_id: str) -> List[PendingMembership]:
        """Get a given user's group memberships."""
        sql_get = "select * from pending_memberships where unique_id=?"
        try:
            result = []
            with self.connection:
                result = self.connection.execute(sql_get, [unique_id]).fetchall()
            return [PendingMembership(*row) for row in result]
        except sqlite3.Error as ex:
            msg = f"Failed to get memberships of user {unique_id} from pending db"
            logger.error("%s: %s", msg, ex)
            raise Failure(message=msg)
