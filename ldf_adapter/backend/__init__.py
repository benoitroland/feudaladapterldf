import sys
import pkgutil
import logging

from ..config import CONFIG

for module_info in pkgutil.iter_modules(sys.modules[__name__].__path__):
    module_path = f"{__name__}.{module_info.name}"
    __import__(module_path)

class Backend:
    """Need to put __getattr__ in a class for Python < 3.7 compatibility.

    This class acts as a module.

    See https://stackoverflow.com/questions/2447353/getattr-on-a-module#7668273
    """
    __backend__ = CONFIG['ldf_adapter']['backend']

    def __getattr__(self, name):
        """Return the `User` and `Group` from the configured backend."""
        if name in ['User', 'Group']:
            return getattr(sys.modules[f"{__name__}.{self.__backend__}"], name)
        else:
            raise AttributeError(f"backend module '{__name__}' has no attribute '{name}'")

# Replace this very module (`ldf_adapter.backend`) with the pseudo-module above, which has the
# effect of this ldf_adapter.backend acting as the actually configured backend module.
sys.modules[__name__] = Backend()
