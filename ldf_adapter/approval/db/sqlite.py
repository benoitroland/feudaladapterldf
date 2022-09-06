from dataclasses import fields
from typing import Optional, Type, Union, List, TypeVar
from dataclasses import fields
import sqlite3
import json
import logging
from pathlib import Path

from ldf_adapter.results import Failure, FatalError
from ldf_adapter.config import CONFIG
from ldf_adapter.approval.models import (
    DeploymentState,
    PendingModel,
    PendingUser,
    PendingGroup,
    PendingMemberships,
)
from ldf_adapter.approval.db import generic


logger = logging.getLogger(__name__)


T = TypeVar("T")


def pytype_to_sqltype(pytype: Type) -> str:
    """Return the sql type for any given python type."""

    def get_type_name(pytype):
        try:
            return pytype.__repr__()
        except TypeError:
            return pytype.__name__

    type_name = get_type_name(pytype)
    module_name = pytype.__module__
    # types from typing module supported by sqlite
    if module_name == "typing":
        if type_name.startswith("typing.Optional") or type_name.startswith("typing.Union"):
            # Union only when it's used to represent an optional field
            # in python 3.7, __repr__() for the Optional type returns the Union representation
            # in python >= 3.9, __repr__() for a Union of a type and NoneType returns the Optional representation
            if len(pytype.__args__) == 2 and get_type_name(pytype.__args__[0]) == "NoneType":
                return pytype_to_sqltype(pytype.__args__[1])
            elif len(pytype.__args__) == 2 and get_type_name(pytype.__args__[1]) == "NoneType":
                return pytype_to_sqltype(pytype.__args__[0])
            else:
                return "text"
        elif type_name.startswith("typing.Literal"):
            return "text"
        elif type_name.startswith("typing.Dict"):
            return "dict"
        elif type_name.startswith("typing.List"):
            return "list"
        elif type_name.startswith("typing.Set"):
            return "list"
        elif type_name.startswith("typing.ByteString"):
            return "blob"
        else:
            return "text"  # default type
    if module_name == "builtins":
        # builtin types supported by sqlite
        if type_name == "str":
            return "text"
        if type_name == "int":
            return "integer"
        if type_name == "float":
            return "real"
        if type_name == "bytes":
            return "blob"
        if type_name == "NoneType":
            return "null"
        # additionally defined types with custom adapters and converters
        if type_name == "dict":
            return "dict"
        if type_name == "list":
            return "list"
        if type_name == "bool":
            return "boolean"
    # more additionally defined types with custom adapters and converters from other modules
    if type_name == "DeploymentState":
        return "DeploymentState"
    # default type
    return "text"


def sql_command_create_table(
    data_model: Type[PendingModel], table_name: str, primary_key: Union[str, List[str]]
) -> str:
    """Return an sql command for creating a table for a given data model.

    Args:
        data_model (Type[PendingModel]): dataclass containing the fields that will become the table columns
        table_name (str): the table name
        primary_key (Union[str, List[str]]): name(s) of column(s) to be used as primary key

    Returns:
        str: a string representation of the sql command
    """
    columns_with_types = ", ".join(
        [" ".join([field.name, pytype_to_sqltype(field.type)]) for field in fields(data_model)]
    )
    if isinstance(primary_key, List):
        primary_key = ", ".join(primary_key)
    return (
        f"create table if not exists {table_name}"
        f"({columns_with_types}, primary key ({primary_key}))"
    )


def sql_command_insert(data_model: Type[PendingModel], table_name: str) -> str:
    """Return an sql command for inserting an entry of a given data model into a table.

    The sql command will require the following arguments:
    - the values of the dataclass fields to be inserted

    Args:
        data_model (Type[PendingModel]): dataclass containing the fields that are the same as the table columns
        table_name (str): the table name

    Returns:
        str: a string representation of the sql command
    """
    column_names = ", ".join([field.name for field in fields(data_model)])
    column_values = ",".join(["?" for _ in fields(data_model)])
    return f"insert into {table_name}({column_names}) values ({column_values})"


def sql_command_update(table_name: str, columns: List[str], key: Union[str, List[str]]) -> str:
    """Return an sql command for updating a set of fields for an entry in a given table.

    The sql command will require the following arguments, in this order:
    - the new values for each column
    - the key value(s) of the entry to be updated

    Args:
        table_name (str): the table name
        columns (list[str]): the columns to update
        key (list | str): the key to search on for update; a column name or a list of column names

    Returns:
        str: a string representation of the sql command
    """
    column_names = ", ".join([f"{col} = ?" for col in columns])
    condition = " and ".join([f"{k} = ?" for k in key]) if isinstance(key, list) else f"{key} = ?"
    return f"update {table_name} set {column_names} where {condition}"


def sql_command_remove(table_name: str, key: Union[str, List[str]]) -> str:
    """Return an sql command for removing an entry from a table.

    The sql command will require the following arguments:
    - the values for given key(s) of the entry to be removed

    Args:
        table_name (str): the table name
        key (list | str): the key to search on for removal; a column name or a list of column names

    Returns:
        str: a string representation of the sql command
    """
    condition = " and ".join([f"{k} = ?" for k in key]) if isinstance(key, list) else f"{key} = ?"
    return f"delete from {table_name} where {condition}"


def sql_command_select(table_name: str, key: Union[str, List[str]]) -> str:
    """Return an sql command for selecting an entry from a table.

    The sql command will require the following arguments:
    - the values for given key(s) of the entry to be selected

    Args:
        table_name (str): the table name
        key (list | str): the key to search on for selection; a column name or a list of column names

    Returns:
        str: a string representation of the sql command
    """
    condition = " and ".join([f"{k} = ?" for k in key]) if isinstance(key, list) else f"{key} = ?"
    return f"select * from {table_name} where {condition}"


# register the functions for manipulating custom types in sqlite db
sqlite3.register_adapter(dict, lambda x: json.dumps(x).encode("utf-8"))
sqlite3.register_converter("dict", lambda x: json.loads(x.decode("utf-8")))

sqlite3.register_adapter(list, lambda x: json.dumps(x).encode("utf-8"))
sqlite3.register_converter("list", lambda x: json.loads(x.decode("utf-8")))

sqlite3.register_adapter(DeploymentState, lambda x: x.name.encode("utf-8"))
sqlite3.register_converter(
    "DeploymentState", lambda x: DeploymentState.from_string(x.decode("utf-8"))
)

sqlite3.register_adapter(bool, int)
sqlite3.register_converter("boolean", lambda v: bool(int(v)))


class SQLiteConnector:
    def __init__(self, location: str) -> None:
        self.location = location
        Path(self.location).parent.mkdir(exist_ok=True)

    def exists(self) -> bool:
        return Path(self.location).exists()

    def connect(self) -> None:
        """Connect to the DB.
        Initialise self.connection object.
        """
        try:
            self.connection = sqlite3.connect(self.location, detect_types=sqlite3.PARSE_DECLTYPES)
        except sqlite3.Error as ex:
            message = f"Could not connect to sqlite db at location {self.location}: {ex}"
            logger.error(message)
            raise FatalError(message=message)

    def create(
        self, data_model: Type[PendingModel], table_name: str, primary_key: Union[str, List[str]]
    ) -> None:
        """Create a table for a given data model.

        Args:
            data_model (Type[PendingModel]): dataclass containing the fields that will become the table columns
            table_name (str): the table name
            primary_key (Union[str, List[str]]): name(s) of column(s) to be used as primary key
        """
        try:
            with self.connection:  # con.commit() is called automatically afterwards on success
                logger.debug("Creating table: %s", table_name)
                self.connection.execute(
                    sql_command_create_table(
                        data_model=data_model, table_name=table_name, primary_key=primary_key
                    )
                )
                logger.debug("Successfully created table '%s'.", table_name)
        except sqlite3.Error as ex:
            message = f"Failed to create table {table_name}: {ex}"
            logger.error(message)
            raise FatalError(message=message)

    def insert(self, data_model: Type[PendingModel], table_name: str, entry: tuple) -> bool:
        """Insert an entry of a given data model into a table.

        Args:
            data_model (Type[PendingModel]): dataclass containing the fields that are the same as the table columns
            table_name (str): the table name
            entry (tuple): the values of the dataclass fields to be inserted

        Returns:
            bool: False if an entry already existed for given key, True if a new entry was inserted.
        """
        try:
            with self.connection:
                logger.debug("Inserting to table: %s", table_name)
                self.connection.execute(
                    sql_command_insert(data_model=data_model, table_name=table_name),
                    entry,
                )
                logger.debug("Successfully inserted to table '%s': %s", table_name, entry)
            return True
        except sqlite3.IntegrityError as ex:
            if ex.args[0].startswith("UNIQUE constraint failed: "):
                logger.info(f"Entry {entry} already exists in table {table_name}.")
                return False
            raise ex
        except sqlite3.Error as ex:
            message = f"Failed to insert entry to table {table_name}: {ex}"
            logger.error(message)
            raise Failure(message=message)

    def update(
        self, table_name: str, columns: List[str], key: Union[str, List[str]], entry: tuple
    ) -> None:
        """Update an entry in a table.

        Args:
            table_name (str): the table name
            columns (list[str]): the columns to update
            key (str | list[str]): the key to search on for update
            entry (tuple): the values of the columns to be updated, and the value(s) of the key(s)
                           to be used for search, in this order
        """
        try:
            with self.connection:
                logger.debug("Updating entry in table: %s", table_name)
                self.connection.execute(
                    sql_command_update(table_name=table_name, columns=columns, key=key),
                    entry,
                )
                logger.debug("Successfully updated entry in table '%s': %s", table_name, entry)
        except sqlite3.Error as ex:
            message = f"Failed to update table {table_name}: {ex}"
            logger.error(message)
            raise Failure(message=message)

    def select(
        self,
        data_model: Type[T],
        table_name: str,
        key: Union[str, List[str]],
        value: tuple,
    ) -> Optional[T]:
        """Get an entry from a table.

        Args:
            data_model (Type[T]): data type of the entry to be returned
            table_name (str): the table name
            key (Union[str, List[str]]): name(s) of column(s) to be used as search key
            value (tuple): the value(s) of key(s) for which to search

        Returns:
            Optional[T]: the (first) entry found or None if no entry was found
        """
        try:
            with self.connection:
                logger.debug("Getting from table: %s", table_name)
                result = self.connection.execute(
                    sql_command_select(table_name=table_name, key=key), value
                ).fetchall()
                logger.debug(
                    "Successfully got entry from table '%s' for value %s.", table_name, value
                )
                if len(result) == 0:
                    return None
                if len(result) > 1:
                    logger.warning(
                        "Multiple entries found in table %s for value: %s", table_name, value
                    )
                return data_model(*result[0])
        except sqlite3.Error as ex:
            message = f"Failed to get entry from table {table_name} for value {value}: {ex}"
            logger.error(message)
            raise Failure(message=message)

    def delete(self, table_name: str, key: Union[str, List[str]], value: tuple) -> None:
        """Remove an entry from a table.

        Args:
            table_name (str): the table name
            key (Union[str, List[str]]): name(s) of column(s) to be used search key
            value (tuple): value(s) of key(s) for entry to be removed
        """
        try:
            with self.connection:
                logger.debug("Removing from table: %s", table_name)
                self.connection.execute(sql_command_remove(table_name=table_name, key=key), value)
                logger.debug("Successfully removed entry %s from table '%s'.", value, table_name)
        except sqlite3.Error as ex:
            message = f"Failed to remove entry {value} from table {table_name}: {ex}"
            logger.error(message)
            raise Failure(message=message)


class PendingDB(generic.PendingDB):
    """Implementation of PendingDB with sqlite3."""

    def __init__(self) -> None:
        """Initialise sqlite-based DB for managing users and groups pending approval."""
        self.connector = SQLiteConnector(CONFIG.approval.user_db_location)
        if not self.connector.exists():
            self.connector.connect()
            logger.debug(
                "No sqlite DB found at %s, creating it...", CONFIG.approval.user_db_location
            )
            self.connector.create(
                data_model=PendingUser, table_name="pending_users", primary_key="unique_id"
            )
            self.connector.create(
                data_model=PendingGroup, table_name="pending_groups", primary_key="name"
            )
            self.connector.create(
                data_model=PendingMemberships,
                table_name="pending_memberships",
                primary_key="unique_id",
            )
        else:
            logger.debug(
                "Existing sqlite DB found at %s. Loading pending data from it.",
                CONFIG.approval.user_db_location,
            )
            self.connector.connect()

    def add_user(self, user: PendingUser) -> bool:
        """Add a new entry for a user. Returns False if entry already exists."""
        return self.connector.insert(
            data_model=PendingUser,
            table_name="pending_users",
            entry=tuple(getattr(user, field.name) for field in fields(PendingUser)),
        )

    def remove_user(self, unique_id: str) -> None:
        """Remove user entry for unique_id."""
        self.connector.delete(table_name="pending_users", key="unique_id", value=(unique_id,))

    def get_user(self, unique_id: str) -> Optional[PendingUser]:
        """Get a user entry that is up for approval by the user's unique_id."""
        return self.connector.select(
            data_model=PendingUser,
            table_name="pending_users",
            key="unique_id",
            value=(unique_id,),
        )

    def get_user_by_username(self, username: str) -> Optional[PendingUser]:
        """Get an entry by the local username."""
        return self.connector.select(
            data_model=PendingUser,
            table_name="pending_users",
            key="username",
            value=(username,),
        )

    def reject_user(self, unique_id: str) -> None:
        """Change the state of user given by unique_id to REJECTED."""
        self.connector.update(
            table_name="pending_users",
            columns=["state"],
            key="unique_id",
            entry=(DeploymentState.REJECTED, unique_id),
        )

    def notify_user(self, unique_id: str) -> None:
        """Change the state of user given by unique_id to NOTIFIED."""
        self.connector.update(
            table_name="pending_users",
            columns=["state"],
            key="unique_id",
            entry=(DeploymentState.NOTIFIED, unique_id),
        )

    def add_group(self, group: PendingGroup) -> bool:
        """Add a new entry for a group. Returns False if entry already exists."""
        return self.connector.insert(
            data_model=PendingGroup,
            table_name="pending_groups",
            entry=tuple(getattr(group, field.name) for field in fields(PendingGroup)),
        )

    def remove_group(self, name: str) -> None:
        """Remove group entry for name."""
        self.connector.delete(table_name="pending_groups", key="name", value=(name,))

    def get_group(self, name: str) -> Optional[PendingGroup]:
        """Get an entry that is up for approval by the group's name."""
        return self.connector.select(
            data_model=PendingGroup, table_name="pending_groups", key="name", value=(name,)
        )

    def notify_group(self, name: str) -> None:
        """Change the state of group given by name to NOTIFIED."""
        self.connector.update(
            table_name="pending_groups",
            columns=["state"],
            key="name",
            entry=(DeploymentState.NOTIFIED, name),
        )

    def add_memberships(self, membership: PendingMemberships) -> bool:
        """Add a new entry for a user's pending group memberships. Returns False if entry already exists."""
        return self.connector.insert(
            data_model=PendingMemberships,
            table_name="pending_memberships",
            entry=tuple(getattr(membership, field.name) for field in fields(PendingMemberships)),
        )

    def update_memberships(self, membership: PendingMemberships) -> None:
        """Update a user's pending group memberships by replacing them with the given memberships."""
        columns = [field.name for field in fields(PendingMemberships) if field.name != "unique_id"]
        self.connector.update(
            table_name="pending_memberships",
            columns=columns,
            key="unique_id",
            entry=tuple([getattr(membership, col) for col in columns] + [membership.unique_id]),
        )

    def remove_memberships(self, unique_id: str) -> None:
        """Remove all pending group memberships of a given user."""
        self.connector.delete(table_name="pending_memberships", key="unique_id", value=(unique_id,))

    def get_memberships(self, unique_id: str) -> Optional[PendingMemberships]:
        """Get a given user's pending group memberships."""
        return self.connector.select(
            data_model=PendingMemberships,
            table_name="pending_memberships",
            key="unique_id",
            value=(unique_id,),
        )

    def notify_memberships(self, unique_id: str) -> None:
        """Change the state of user's memberships given by unique_id to NOTIFIED."""
        self.connector.update(
            table_name="pending_memberships",
            columns=["state"],
            key="unique_id",
            entry=(DeploymentState.NOTIFIED, unique_id),
        )
