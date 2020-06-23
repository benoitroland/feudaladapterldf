import sys
import logging

from ..config import CONFIG
logger = logging.getLogger(__name__)

# import all backends, so they are in sys.modules for the getattr redirect
from . import bwidm, local_unix

__backend__ = f"{__name__}.{CONFIG['ldf_adapter']['backend']}"
__import__(__backend__)

class Backend:
    """Need to put __getattr__ in a classe for Python < 3.7 compatibility.

    See https://stackoverflow.com/questions/2447353/getattr-on-a-module#7668273
    """

    def __getattr__(self, name):
        logger.debug('__backend__: %s', __backend__)

        """Return the `User` and `Group` from the configured backend."""
        if name in ['User', 'Group']:
            return getattr(sys.modules[__name__+'.'+__backend__], name)
        else:
            raise AttributeError(f"backend module '{__name__}' has no attribute '{name}'")

# TODO this breaks the import of Backend?
# sys.modules[__name__] = Backend()
