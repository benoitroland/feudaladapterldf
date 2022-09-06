import copy
from typing import Type
from os.path import basename, isfile, join
import glob
from dataclasses import dataclass

from ldf_adapter.results import FatalError


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


def to_bool(bool_str):
    """Convert a string to bool.
    Raise a FatalError if the string cannot be converted.
    """
    if bool_str.lower() in ["true", "yes", "yes, do as i say!"]:
        return True
    if bool_str.lower() in ["false", "no"]:
        return False
    raise FatalError(f"Error converting to bool: unrecognised boolean value {bool_str}.")


def to_int(int_str):
    """Convert a string to int.
    Raise a FatalError if the string cannot be converted.
    """
    try:
        return int(int_str)
    except ValueError:
        raise FatalError(f"Error converting to int: unrecognised integer value {int_str}.")


def to_list(list_str):
    """Convert a string containing comma-separated strings to list of strings.
    Raise a FatalError if the string cannot be converted.
    """
    try:
        return list(set(list_str.split()))
    except ValueError:
        raise FatalError(f"Error converting to list: unrecognised list value {list_str}.")


def dynamic_import(fq_module_name: str, class_name: str) -> Type:
    """Import a class dynamically.

    Args:
        fq_module_name: The fully qualified name of the module to import.
        class_name: The name of the class to import.
    Returns:
        The imported class.
    """
    module = __import__(fq_module_name, fromlist=[class_name])
    try:
        return getattr(module, class_name)
    except AttributeError:
        raise FatalError(message=f"Module {fq_module_name} does not contain class {class_name}")


@dataclass
class BuilderConfig:
    fq_module_name: str
    class_name: str


class ObjectFactory:
    """Generic factory interface for creating all kinds of objects."""

    def __init__(self):
        self._builders = {}
        self._configs = {}

    def register_builder(self, key, fq_module_name, class_name):
        """Register a Builder based on a key value. This only saves the builder configuration."""
        self._configs[key] = BuilderConfig(fq_module_name, class_name)

    def _create_builder(self, key):
        """Create a Builder for a key value. The builder configuration needs to have been
        registered. Only at this point, the module containing the class is dynamically loaded.
        """
        config = self._configs.get(key)
        if config is None:
            raise FatalError(message=f"No builder registered for key {key}")
        object_type = dynamic_import(config.fq_module_name, config.class_name)
        self._builders[key] = ObjectBuilder(object_type)

    def _get_builder(self, key):
        """Return the Builder for a given key. Create it if it's registered but does not exist."""
        builder = self._builders.get(key)
        if not builder:
            self._create_builder(key)
            builder = self._builders.get(key)
            if not builder:
                raise FatalError(message=f"No builder created for key {key}")
        return builder

    def get(self, key, **kwargs):
        """Create and return the concrete object instance based on the key, with given arguments."""
        builder = self._get_builder(key)
        return builder(**kwargs)

    def get_type(self, key):
        """Return the type of the concrete object based on the key."""
        builder = self._get_builder(key)
        return builder._type


class ObjectBuilder:
    """Generic builder for creating all kinds of objects of given type."""

    def __init__(self, object_type: Type):
        self._instance = None
        self._type = object_type

    def __call__(self, **config):
        if not self._instance:
            self._instance = self._type(**config)
        return self._instance


def create_factory(dir_name: str, parent_module: str, class_name: str) -> ObjectFactory:
    """Create a factory for a given class name by registering object builders for
    all sub-modules in a given directory.

    E.g.
        create_factory(".../ldf_adapter/approval/db", "ldf_adapter.approval.db", "PendingDB")
    will register builders for all sub-modules in the directory ".../ldf_adapter/approval/db"
    and create a factory for the class "PendingDB" in the module "ldf_adapter.approval.db".
    The builders will be registered with the factory using the name of the sub-module as key.

    The sub-modules are not loaded at this time, rather on demand.

    Args:
        dir_name (str): name of directory containing modules that provide implementations of the class.
        parent_module (str): name of the parent module.
        class_name (str): name of class to provide objects for.

    Returns:
        ObjectFactory: factory for the given class.
    """
    factory = ObjectFactory()
    for file in glob.glob(join(dir_name, "*.py")):
        if isfile(file) and not file.endswith("__init__.py") and not file.endswith("generic.py"):
            module_name = basename(file)[:-3]
            fq_module_name = f"{parent_module}.{module_name}"
            factory.register_builder(module_name, fq_module_name, class_name)
    return factory
