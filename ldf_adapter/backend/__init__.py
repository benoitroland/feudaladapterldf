import sys

from ..config import CONFIG

def __getattr__(name):
    """Return the `User` and `Group` from the configured backend."""
    __backend__ = f"{__name__}.{CONFIG['ldf_adapter']['backend']}"
    __import__(__backend__)

    if name == 'User':
        return getattr(sys.modules[__backend__], 'User')
    elif name == 'Group':
        return getattr(sys.modules[__backend__], 'Group')
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
