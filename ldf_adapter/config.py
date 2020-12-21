import os
import sys

from configparser import ConfigParser
from pathlib import Path
import logging

if 'pytest' not in sys.modules:
    from ldf_adapter.cmdline_params import args

CONFIG = ConfigParser()

def reload():
    """Reload configuration from disk.

    Config locations, by priority:
    --config option (defaults to /etc/feudal/ldf_adapter.conf)
    $LDF_ADAPTER_CONFIG
    ./ldf_adapter.conf
    ~/.config/feudal/ldf_adapter.conf

    processing is stopped, once a give file is found
    """

    logging.basicConfig(
        level=os.environ.get("LOG", "INFO")
        # format='%(asctime)s [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
    )
    logger = logging.getLogger(__name__)
    files = []

    if 'pytest' not in sys.modules:
        files += [ Path(args.config_file) ]

    filename = os.environ.get("LDF_ADAPTER_CONFIG")
    if filename:
        files += Path(filename)

    files += [
        Path('ldf_adapter.conf'),
        Path.home()/'.config'/'ldf_adapter.conf',
        Path.home()/'.config'/'feudal'/'ldf_adapter.conf',
    ]
    logger.debug("Using these config files: {} to find a suitable one".format(files))

    for f in files:
        if f.exists():
            files_read = CONFIG.read(f)
            logger.info(F"Read config from {files_read}")
            break

# Load config on import
reload()
