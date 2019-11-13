import os
from configparser import ConfigParser
from pathlib import Path


CONFIG = ConfigParser()

def reload():
    """Reload configuration from disk.

    Config locations, by priority:
    $LDF_ADAPTER_CONFIG
    ./ldf_adapter.conf
    ~/.config/feudal/ldf_adapter.conf
    /etc/feudal/ldf_adapter.conf
    """
    files = []

    filename = os.environ.get("LDF_ADAPTER_CONFIG")
    if filename:
        files += [Path(filename)]

    files += [
        Path('ldf_adapter.conf'),
        Path.home()/'.config'/'ldf_adapter.conf',
        Path('/')/'etc'/'feudal'/'ldf_adapter.conf'
    ]

    files_read = CONFIG.read(files)

# Load config on import
reload()
