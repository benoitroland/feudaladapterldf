import sys
import pkgutil
import logging

from ..config import CONFIG
from ..results import Failure

logger = logging.getLogger(__name__)

__backend__ = None
try:
    __backend__ = f"{__name__}.{CONFIG['ldf_adapter']['backend']}"
except KeyError: # Meaning: We did _NOT_ read any config, but we are used
                 # as a library
    logger.error("No configuration found; Cannot load backend")
if not __backend__:
    raise Failure(message="No configuration found; Cannot load backend")

__import__(__backend__)

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
