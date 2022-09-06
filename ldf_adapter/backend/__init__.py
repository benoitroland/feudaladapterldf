from os.path import dirname

from ldf_adapter.config import CONFIG
from ldf_adapter.utils import create_factory


users = create_factory(dir_name=dirname(__file__), parent_module=__name__, class_name="User")
groups = create_factory(dir_name=dirname(__file__), parent_module=__name__, class_name="Group")

User = users.get_type(CONFIG.ldf_adapter.backend)
Group = groups.get_type(CONFIG.ldf_adapter.backend)
