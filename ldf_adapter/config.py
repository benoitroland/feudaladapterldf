import os
import sys

from feudal_globalconfig import globalconfig
from configparser import ConfigParser
from pathlib import Path
import logging

from .results import Failure

PARSE_CMDLINE_PARAMETERS = True
if 'pytest' in sys.modules:
    PARSE_CMDLINE_PARAMETERS = False
else:
    try:
        PARSE_CMDLINE_PARAMETERS = globalconfig.config['parse_commandline_args']
    except KeyError as e:
        pass

if PARSE_CMDLINE_PARAMETERS:
    from ldf_adapter.cmdline_params import args

CONFIG = ConfigParser()


def reload():
    """Reload configuration from disk.

    Config locations, by priority:
    --config option (defaults to /etc/feudal/ldf_adapter.conf)
    $LDF_ADAPTER_CONFIG
    ./ldf_adapter.conf
    ~/.config/feudal/ldf_adapter.conf
    /etc/feudal/ldf_adapter.conf

    processing is stopped, once a give file is found
    """

    logging.basicConfig(
        level=os.environ.get("LOG", "INFO")
        # format='%(asctime)s [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
    )
    logger = logging.getLogger(__name__)
    files = []

    # If the program has arguments with a config_file: prefer it:
    if PARSE_CMDLINE_PARAMETERS:
        files.insert(0, Path(args.config_file))

    # If the caller of the library has provided a configfile: prefer it:
    logger.debug(F"Files: {files}")
    try:
        globalconf_conf_file = Path(globalconfig.config['CONFIGFILE'])
        logger.debug(F"Trying config of globalconfig: {globalconfig.config['CONFIGFILE']}")
        if globalconf_conf_file.exists():
            files.insert(0, globalconf_conf_file)
    except KeyError:
        pass
    
    # Finally, check the environment (last means highes priority)
    filename = os.environ.get("LDF_ADAPTER_CONFIG")
    if filename:
        files.append(Path(filename))

    # default files
    files += [
        Path('ldf_adapter.conf'),
        Path.home()/'.config'/'ldf_adapter.conf',
        Path.home()/'.config'/'feudal'/'ldf_adapter.conf',
        Path('/etc/feudal/ldf_adapter.conf')
    ]

    config_loaded = False
    for f in files:
        if f.exists():
            files_read = CONFIG.read(f)
            logger.debug(F"Using this config file: {files_read}")
            config_loaded = True
            break
    if not config_loaded:
        logger.warning("Could not find any config file")
        logger.debug("Trying to copy config from globalconfig")
        logger.debug(F"type of CONFIG: {type(CONFIG)}")
        # try:
        #     logger.debug(F"type of globalconfig.config['CONFIG']: {type(globalconfig.config['CONFIG'])}")
        # except KeyError:
        # raise Failure(message="Could not find any config (neither file not in globalconfig)")
        logger.error("Could not find any config (neither file not in globalconfig")
        exit(4)

# Load config on import
reload()
