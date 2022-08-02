import pytest
import typing
from dataclasses import dataclass, fields
import copy

from ldf_adapter.results import Failure, FatalError
from ldf_adapter.approval.models import PendingUser, PendingGroup, PendingMemberships
from ldf_adapter.approval.db.sqlite import (
    DeploymentState,
    pytype_to_sqltype,
    sql_command_create_table,
    sql_command_insert,
    sql_command_update,
    SQLiteConnector,
)


MOCK_USER = PendingUser(
    unique_id="unique_id",
    sub="sub",
    iss="iss",
    email="email@domain",
    full_name="full_name",
    username="username",
    state=DeploymentState.PENDING,
    cmd="cmd",
    infodict={},
)

MOCK_GROUP = PendingGroup(
    name="name",
    state=DeploymentState.PENDING,
    cmd="cmd",
    infodict={},
)

MOCK_MEMBERSHIPS = PendingMemberships(
    unique_id="unique_id",
    supplementary_groups=["group1", "group2"],
    removal_groups=["group3", "group4"],
    state=DeploymentState.PENDING,
    cmd="cmd",
    infodict={},
)


@dataclass
class MyDataModel:
    id: int
    name: str
    age: int
    height: float
    weight: float
    is_married: bool
    children: list
    address: dict
    deployment_state: DeploymentState


MOCK_MY_DATA_MODEL = MyDataModel(
    id=1,
    name="name",
    age=20,
    height=1.8,
    weight=70.0,
    is_married=True,
    children=[],
    address={"street": "street", "city": "city", "zip": "zip"},
    deployment_state=DeploymentState.PENDING,
)

NoneType = None.__class__


@pytest.mark.parametrize(
    "pytype,sqltype",
    [
        (int, "integer"),
        (float, "real"),
        (str, "text"),
        (bytes, "blob"),
        (dict, "dict"),
        (list, "list"),
        (DeploymentState, "DeploymentState"),
        (typing.Dict[int, str], "dict"),
        (typing.List[int], "list"),
        (typing.ByteString, "blob"),
        (typing.Callable, "text"),
        (typing.Any, "text"),
        (typing.Tuple[int, int], "text"),
        (typing.Type, "text"),
        (typing.NamedTuple, "text"),
        (typing.Set[str], "list"),
        (typing.Union[NoneType, int], "integer"),
        (typing.Union[int, NoneType], "integer"),
        (typing.Union[NoneType, int, str], "text"),
        (typing.Optional[int], "integer"),
        (typing.Optional[float], "real"),
        (typing.Optional[str], "text"),
        (typing.Optional[bytes], "blob"),
        (typing.Optional[dict], "dict"),
        (typing.Optional[list], "list"),
        (typing.Optional[DeploymentState], "DeploymentState"),
        (typing.Optional[typing.Dict], "dict"),
        (typing.Optional[typing.List], "list"),
        (typing.Optional[typing.ByteString], "blob"),
        (typing.Optional[typing.Optional[int]], "integer"),
        (type(None), "null"),
        (type("something"), "text"),
        (type(1), "integer"),
        (type(1.0), "real"),
        (type(b"something"), "blob"),
        (type({}), "dict"),
        (type([]), "list"),
        (type(DeploymentState.PENDING), "DeploymentState"),
    ],
)
def test_pytype_to_sqltype(pytype: typing.Type, sqltype: str):
    assert pytype_to_sqltype(pytype) == sqltype


create_my_data_model_table_cmd = """
    create table if not exists my_data_model
    (
        id integer,
        name text,
        age integer,
        height real,
        weight real,
        is_married boolean,
        children list,
        address dict,
        deployment_state DeploymentState,
        primary key (id, address)
    )
"""

create_pending_users_table_cmd = """
    create table if not exists pending_users
    (
        unique_id text,
        sub text,
        iss text,
        email text,
        full_name text,
        username text,
        state DeploymentState,
        cmd text,
        infodict dict,
        primary key (unique_id)
    )
"""

create_pending_groups_table_cmd = """
    create table if not exists pending_groups
    (
        name text,
        state DeploymentState,
        cmd text,
        infodict dict,
        primary key (name)
    )
"""

create_pending_memberships_table_cmd = """
    create table if not exists pending_memberships
    (
        unique_id text,
        supplementary_groups list,
        removal_groups list,
        state DeploymentState,
        cmd text,
        infodict dict,
        primary key (unique_id)
    )
"""


@pytest.mark.parametrize(
    "data_model,table_name,primary_key,expected_cmd",
    [
        (MyDataModel, "my_data_model", ["id", "address"], create_my_data_model_table_cmd),
        (PendingUser, "pending_users", "unique_id", create_pending_users_table_cmd),
        (PendingGroup, "pending_groups", "name", create_pending_groups_table_cmd),
        (
            PendingMemberships,
            "pending_memberships",
            "unique_id",
            create_pending_memberships_table_cmd,
        ),
    ],
)
def test_sql_command_create_table(data_model, table_name, primary_key, expected_cmd):
    assert (
        "".join(sql_command_create_table(data_model, table_name, primary_key).split()).lower()
        == "".join(expected_cmd.split()).lower()
    )


insert_my_data_model_cmd = """
    insert into my_data_model
    (id, name, age, height, weight, is_married, children, address, deployment_state)
    values (?,?,?,?,?,?,?,?,?)
"""

insert_pending_users_cmd = """
    insert into pending_users
    (unique_id, sub, iss, email, full_name, username, state, cmd, infodict)
    values (?,?,?,?,?,?,?,?,?)
"""

insert_pending_groups_cmd = """
    insert into pending_groups
    (name, state, cmd, infodict)
    values (?,?,?,?)
"""

insert_pending_memberships_cmd = """
    insert into pending_memberships
    (unique_id, supplementary_groups, removal_groups, state, cmd, infodict)
    values (?,?,?,?,?,?)
"""


@pytest.mark.parametrize(
    "data_model,table_name,expected_cmd",
    [
        (MyDataModel, "my_data_model", insert_my_data_model_cmd),
        (PendingUser, "pending_users", insert_pending_users_cmd),
        (PendingGroup, "pending_groups", insert_pending_groups_cmd),
        (PendingMemberships, "pending_memberships", insert_pending_memberships_cmd),
    ],
)
def test_sql_command_insert(data_model, table_name, expected_cmd):
    assert (
        "".join(sql_command_insert(data_model, table_name).split()).lower()
        == "".join(expected_cmd.split()).lower()
    )


update_my_data_model_cmd = """
    update my_data_model
    set name = ?, age = ?, height = ?, weight = ?
    where id = ? and address = ?
"""

update_pending_users_cmd = """
    update pending_users
    set state = ?
    where unique_id = ?
"""

update_pending_groups_cmd = """
    update pending_groups
    set state = ?, cmd = ?, infodict = ?
    where name = ?
"""

update_pending_memberships_cmd = """
    update pending_memberships
    set unique_id = ?
    where unique_id = ?
"""

update_pending_users_cmd2 = """
    update pending_users
    set unknown_field = ?
    where unique_id = ?
"""

update_pending_users_cmd3 = """
    update pending_users
    set unique_id = ?
    where unknown_key = ?
"""


@pytest.mark.parametrize(
    "table_name,columns,key,expected_cmd",
    [
        (
            "my_data_model",
            ["name", "age", "height", "weight"],
            ["id", "address"],
            update_my_data_model_cmd,
        ),
        ("pending_users", ["state"], "unique_id", update_pending_users_cmd),
        ("pending_groups", ["state", "cmd", "infodict"], ["name"], update_pending_groups_cmd),
        ("pending_memberships", ["unique_id"], "unique_id", update_pending_memberships_cmd),
        ("pending_users", ["unknown_field"], "unique_id", update_pending_users_cmd2),
        ("pending_users", ["unique_id"], "unknown_key", update_pending_users_cmd3),
    ],
)
def test_sql_command_update(table_name, columns, key, expected_cmd):
    assert (
        "".join(sql_command_update(table_name, columns, key).split()).lower()
        == "".join(expected_cmd.split()).lower()
    )


def new_init(self: SQLiteConnector, location: str) -> None:
    self.location = ":memory:"


@pytest.fixture(scope="function")
def mock_connector():
    SQLiteConnector.__init__ = new_init
    connector = SQLiteConnector("")
    connector.connect()
    yield connector


@pytest.mark.parametrize(
    "data_model,table_name,primary_key",
    [
        (PendingUser, "pending_users", ["unique_id"]),
        (PendingGroup, "pending_groups", ["name"]),
        (PendingMemberships, "pending_memberships", ["unique_id"]),
        (MyDataModel, "my_data_model", ["id", "address"]),
    ],
)
def test_create_tables(mock_connector, data_model, table_name, primary_key):
    # test create when primary key not a known field
    with pytest.raises(SystemExit) as excinfo:
        mock_connector.create(data_model, table_name, "unknown_key")
    assert excinfo.value.code == FatalError.exit_code

    # test successful create
    mock_connector.create(data_model, table_name, primary_key)
    c = mock_connector.connection.cursor()

    # Check if table exists
    c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
    assert c.fetchone()[0] == table_name

    # check if table has the correct columns
    c.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in c.fetchall()]
    assert columns == [f.name for f in fields(data_model)]

    # check if table has the correct primary key
    c.execute(f"PRAGMA table_info({table_name});")
    primary_key_set = [row[1] for row in c.fetchall() if row[5] != 0]
    assert primary_key_set == primary_key

    # check if table create can be run again without error
    mock_connector.create(data_model, table_name, primary_key)


@pytest.fixture(scope="function")
def mock_connector_with_users():
    SQLiteConnector.__init__ = new_init
    connector = SQLiteConnector("")
    connector.connect()
    connector.create(data_model=PendingUser, table_name="pending_users", primary_key="unique_id")
    yield connector


@pytest.mark.parametrize(
    "data_model,table_name,primary_key,mock_object",
    [
        (PendingUser, "pending_users", ["unique_id"], MOCK_USER),
        (PendingGroup, "pending_groups", ["name"], MOCK_GROUP),
        (PendingMemberships, "pending_memberships", ["unique_id"], MOCK_MEMBERSHIPS),
        (MyDataModel, "my_data_model", ["id", "address"], MOCK_MY_DATA_MODEL),
    ],
)
def test_insert(mock_connector, data_model, table_name, primary_key, mock_object):
    entry = tuple(getattr(mock_object, field.name) for field in fields(data_model))

    # test insert when table does not exist
    with pytest.raises(Failure):
        mock_connector.insert(data_model, table_name, entry)
    mock_connector.create(data_model, table_name, primary_key)

    # test insert wrong number of columns
    with pytest.raises(Failure):
        wrong_entry = entry + ("wrong",)
        mock_connector.insert(data_model, table_name, wrong_entry)

    # check that insert works
    assert mock_connector.insert(data_model, table_name, entry) == True

    # check that inserted entry is the same as the mock object
    c = mock_connector.connection.cursor()
    c.execute(f"SELECT * FROM {table_name};")
    result = c.fetchall()
    assert len(result) == 1
    assert result[0] == entry

    # check that insert return False if entry already exists
    assert mock_connector.insert(data_model, table_name, entry) == False


@pytest.mark.parametrize(
    "data_model,table_name,primary_key,mock_object",
    [
        (PendingUser, "pending_users", ["unique_id"], MOCK_USER),
        (PendingGroup, "pending_groups", ["name"], MOCK_GROUP),
        (PendingMemberships, "pending_memberships", ["unique_id"], MOCK_MEMBERSHIPS),
        (MyDataModel, "my_data_model", ["id", "address"], MOCK_MY_DATA_MODEL),
    ],
)
def test_select(mock_connector, data_model, table_name, primary_key, mock_object):
    mock_connector.create(data_model, table_name, primary_key)
    entry = tuple(getattr(mock_object, field.name) for field in fields(data_model))
    if isinstance(primary_key, list):
        primary_key_value = tuple([getattr(mock_object, key) for key in primary_key])
    else:
        primary_key_value = (getattr(mock_object, primary_key),)

    # check that select returns None when not found
    assert mock_connector.select(data_model, table_name, primary_key, primary_key_value) is None

    # check that select returns the correct object when found
    mock_connector.insert(data_model, table_name, entry)
    assert (
        mock_connector.select(data_model, table_name, primary_key, primary_key_value) == mock_object
    )


@pytest.mark.parametrize(
    "data_model,table_name,primary_key,mock_object,column,value,second_value",
    [
        (PendingUser, "pending_users", ["unique_id"], MOCK_USER, "cmd", "cmd", "another_unique_id"),
        (PendingGroup, "pending_groups", ["name"], MOCK_GROUP, "cmd", "cmd", "another_name"),
        (
            PendingMemberships,
            "pending_memberships",
            ["unique_id"],
            MOCK_MEMBERSHIPS,
            "cmd",
            "cmd",
            "another_unique_id",
        ),
        (
            MyDataModel,
            "my_data_model",
            ["id", "address"],
            MOCK_MY_DATA_MODEL,
            "name",
            "name",
            "another_id",
        ),
    ],
)
def test_select_on_column(
    mock_connector, data_model, table_name, primary_key, mock_object, column, value, second_value
):
    mock_connector.create(data_model, table_name, primary_key)

    # check that select returns None when not found
    assert mock_connector.select(data_model, table_name, column, (value,)) is None

    # check that select returns the correct object when found
    entry = tuple(getattr(mock_object, field.name) for field in fields(data_model))
    mock_connector.insert(data_model, table_name, entry)
    assert mock_connector.select(data_model, table_name, column, (value,)) == mock_object

    # check that select returns first entry when multiple entries are found
    mock_object2 = copy.copy(mock_object)
    mock_object2.__setattr__(
        primary_key[0] if isinstance(primary_key, list) else primary_key, second_value
    )
    second_entry = tuple(getattr(mock_object2, field.name) for field in fields(data_model))
    mock_connector.insert(data_model, table_name, second_entry)
    assert mock_connector.select(data_model, table_name, column, (value,)) == mock_object


@pytest.mark.parametrize(
    "data_model,table_name,primary_key,mock_object",
    [
        (PendingUser, "pending_users", ["unique_id"], MOCK_USER),
        (PendingGroup, "pending_groups", ["name"], MOCK_GROUP),
        (PendingMemberships, "pending_memberships", ["unique_id"], MOCK_MEMBERSHIPS),
        (MyDataModel, "my_data_model", ["id", "address"], MOCK_MY_DATA_MODEL),
    ],
)
def test_delete(mock_connector, data_model, table_name, primary_key, mock_object):
    if isinstance(primary_key, list):
        primary_key_value = tuple([getattr(mock_object, key) for key in primary_key])
    else:
        primary_key_value = (getattr(mock_object, primary_key),)

    # test delete when table does not exist
    with pytest.raises(Failure):
        mock_connector.delete(table_name, primary_key, primary_key_value)

    mock_connector.create(data_model, table_name, primary_key)

    # test delete when entry does not exist
    mock_connector.delete(table_name, primary_key, primary_key_value)

    # test delete when entry exists
    entry = tuple(getattr(mock_object, field.name) for field in fields(data_model))
    mock_connector.insert(data_model, table_name, entry)
    mock_connector.delete(table_name, primary_key, primary_key_value)
    mock_connector.connection.cursor().execute(f"SELECT * FROM {table_name};")
    result = mock_connector.connection.cursor().fetchall()
    assert len(result) == 0


@pytest.mark.parametrize(
    "data_model,table_name,primary_key,mock_object,column,value",
    [
        (PendingUser, "pending_users", "unique_id", MOCK_USER, "cmd", "cmd2"),
        (PendingGroup, "pending_groups", "name", MOCK_GROUP, "cmd", "cmd2"),
        (PendingMemberships, "pending_memberships", "unique_id", MOCK_MEMBERSHIPS, "cmd", "cmd2"),
        (MyDataModel, "my_data_model", ["id", "address"], MOCK_MY_DATA_MODEL, "name", "name2"),
    ],
)
def test_update(mock_connector, data_model, table_name, primary_key, mock_object, column, value):
    if isinstance(primary_key, list):
        primary_key_value = tuple([getattr(mock_object, key) for key in primary_key])
    else:
        primary_key_value = (getattr(mock_object, primary_key),)
    entry = (value,) + primary_key_value

    # test update when table does not exist
    with pytest.raises(Failure):
        mock_connector.update(table_name, [column], primary_key, entry)

    mock_connector.create(data_model, table_name, primary_key)

    # test update when entry does not exist -> does not fail, but does not modify anything
    mock_connector.update(table_name, [column], primary_key, entry)

    # test update wrong number of columns
    with pytest.raises(Failure):
        mock_connector.update(table_name, [column, column], primary_key, entry)

    # test update wrong number of values
    with pytest.raises(Failure):
        mock_connector.update(table_name, [column], primary_key, entry[:-1])

    # test update when entry exists
    insert_entry = tuple(getattr(mock_object, field.name) for field in fields(data_model))
    mock_connector.insert(data_model, table_name, insert_entry)
    mock_connector.update(table_name, [column], primary_key, entry)
    result = (
        mock_connector.connection.cursor().execute(f"SELECT {column} FROM {table_name};").fetchall()
    )
    assert len(result) == 1
    assert result[0][0] == value
