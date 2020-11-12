import sys

from ..config import CONFIG

__backend__ = f"{__name__}.{CONFIG['ldf_adapter']['backend']}"
__import__(__backend__)

class Backend:
    """Need to put __getattr__ in a classe for Python < 3.7 compatibility.

    See https://stackoverflow.com/questions/2447353/getattr-on-a-module#7668273
    """

    def __getattr__(self, name):
        """Return the `User` and `Group` from the configured backend."""
        if name == 'User':
            return getattr(sys.modules[__backend__], 'User')
        elif name == 'Group':
            return getattr(sys.modules[__backend__], 'Group')
        else:
            raise AttributeError(f"backend module '{__name__}' has no attribute '{name}'")

sys.modules[__name__] = Backend()
