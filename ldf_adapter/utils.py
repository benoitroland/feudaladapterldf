import copy
from typing import Type, Union, List
from dataclasses import fields


def dictdiff(old, new):
    """Return the difference between two dicts.

    Returns a dictionary mapping the keys from `old` and `new` to tuples `(old_value, new_value)`.
    A value of `None` in one of the elements of the tuple indicates that the key was not present in
    the respective dictionary.

    Does not distinguishing between missing keys and values of `None`.

    Arguments:
    old -- The first dictionary (type: dict)
    new -- The other dictionary (type: dict)
    """

    def _dictdiff(old, new):
        for k in new:
            if isinstance(new.get(k), dict) and isinstance(old.get(k), dict):
                subdiff = dict(_dictdiff(old[k], new[k]))
                if subdiff:
                    yield (k, subdiff)
            elif old.get(k) != new.get(k):
                yield (k, (old.get(k), new.get(k)))

    return dict(_dictdiff(old, new))


def log_dictdiff(diff, log_function=print, prefix=""):
    """Print the given dict-difference.

    Arguments:
    diff -- The dict diff as returned by `dictdiff` (type: dict)
    log_function -- The function to be used for printing (type: lambda str: None)
    """
    for k, v in diff.items():
        if isinstance(v, dict):
            log_dictdiff(v, log_function, "{}/".format(k))
        else:
            (old, new) = v
            if old:
                log_function("Updating {}{} from '{}' to '{}'".format(prefix, k, old, new))
            else:
                log_function("Setting {}{} to '{}'".format(prefix, k, new))


def dictmerge(lhs, rhs):
    """Merge two dicts recusively."""
    res = copy.deepcopy(lhs)
    for k in rhs:
        if isinstance(rhs[k], dict) and k in res and isinstance(res[k], dict):
            res[k] = dictmerge(res[k], rhs[k])
        else:
            res[k] = rhs[k]

    return res


def pytype_to_sqltype(pytype: Type) -> str:
    """Return the sql type for any given python type."""
    if pytype is None:
        return "null"
    # types from typing module supported by sqlite
    if pytype.__module__ == "typing":
        if pytype.__str__().startswith("typing.Optional"):
            pytype = pytype.__args__[0]  # extract the builtin type from the args
        elif pytype.__str__().startswith("typing.Literal"):
            return "text"
        elif pytype.__str__().startswith("typing.Dict"):
            return "dict"
        elif pytype.__str__().startswith("typing.List"):
            return "list"
        elif pytype.__str__().startswith("typing.ByteString"):
            return "blob"
        else:
            return "text"  # default type
    # builtin types supported by sqlite
    if pytype.__name__ == "str":
        return "text"
    if pytype.__name__ == "int":
        return "integer"
    if pytype.__name__ == "float":
        return "real"
    if pytype.__name__ == "bytes":
        return "blob"
    # additionally defined types with custom adapters and converters
    if pytype.__name__ == "dict":
        return "dict"
    if pytype.__name__ == "list":
        return "list"
    if pytype.__name__ == "DeploymentState":
        return "DeploymentState"
    # default type
    return "text"


def sql_command_create_table(
    data_model: Type, table_name: str, primary_key: Union[str, List[str]]
) -> str:
    """Return an sql command for creating a table for a given data model.

    Args:
        data_model (Type): dataclass containing the fields that will become the table columns
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


def sql_command_insert_to_table(data_model: Type, table_name: str) -> str:
    """Return an sql command for inserting an entry of a given data model into a table.

    Args:
        data_model (Type): dataclass containing the fields that are the same as the table columns
        table_name (str): the table name

    Returns:
        str: a string representation of the sql command
    """
    column_names = ", ".join([field.name for field in fields(data_model)])
    column_values = ",".join(["?" for _ in fields(data_model)])
    return f"insert into {table_name}({column_names}) values ({column_values})"


def sql_command_update_table(data_model: Type, table_name: str, key: str) -> str:
    """Return an sql command for updating an entry of a given data model from a table.

    Args:
        data_model (Type): dataclass containing the fields that are the same as the table columns
        table_name (str): the table name
        key (str): the key to search on for update

    Returns:
        str: a string representation of the sql command
    """
    column_names = ", ".join([f"{field.name} = ?" for field in fields(data_model)])
    return f"update {table_name} set {column_names} where {key} = ?"
