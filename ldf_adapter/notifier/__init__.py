from os.path import dirname

from ldf_adapter.utils import create_factory


notifiers = create_factory(
    dir_name=dirname(__file__), parent_module=__name__, class_name="Notifier"
)
