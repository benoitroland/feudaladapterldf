# vim: tw=100 foldmethod=indent
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=redefined-outer-name, logging-not-lazy, logging-format-interpolation, logging-fstring-interpolation
# pylint: disable=missing-docstring, trailing-whitespace, trailing-newlines, too-few-public-methods

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("ldf_adapter")  # => This is the key to allow logging from other modules
jsonlogger = logging.getLogger("jsonlog.ldf_adapter")


class PathTruncatingFormatter(logging.Formatter):
    """formatter for logging"""

    def format(self, record):
        pathname = record.pathname
        if len(pathname) > 23:
            pathname = "...{}".format(pathname[-19:])
        record.pathname = pathname
        return super(PathTruncatingFormatter, self).format(record)


def setup_logging():
    """setup logging"""

    # Remove all other logging handlers
    for h in logger.handlers:
        logger.removeHandler(h)

    # Use a nice formatter
    for h in logger.handlers:
        logger.removeHandler(h)

    # formatter = logging.Formatter("[%(asctime)s]%(levelname)8s - %(message)s")
    # if loglevel=="DEBUG":
    formatter = PathTruncatingFormatter(
        "[%(asctime)s] {%(pathname)23s:%(lineno)-3d}%(levelname)8s - %(message)s"
    )

    # set preliminary loglevel from ENV:
    loglevel_env = os.environ.get("LOG")
    stream_handler = logging.StreamHandler()
    if loglevel_env is not None:
        logger.setLevel(loglevel_env)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # Setup logfile
    # pylint: disable=import-outside-toplevel
    from .config import CONFIG

    # Ensure log_file exists and is writeable
    logfile = CONFIG.messages.log_file
    dirname = os.path.dirname(logfile)

    loglevel_env = os.environ.get("LOG", "WARNING")
    loglevel = CONFIG.messages.log_level or loglevel_env
    logger.setLevel(loglevel)

    if not os.path.isdir(os.path.dirname(logfile)) and os.path.dirname(logfile) != "":
        try:
            os.mkdir(dirname, 755)
        except FileExistsError as e:
            # ignore this error
            print(f"Warning file exists: {e}")
        except IOError as e:
            print(f"Error creating dir for logfile: {e}")
            raise
    if not os.path.isfile(logfile):
        try:
            open(logfile, "a").close()
        except IOError as e:
            print(f"Error creating dir for logfile: {e}")
            raise

    # Setup logging to logfile
    file_handler = RotatingFileHandler(logfile, maxBytes=100**6, backupCount=2)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(loglevel)
    logger.addHandler(file_handler)

    # Reconsider logging to console:
    log_to_console = CONFIG.messages.log_to_console
    if log_to_console.lower() in ("false", "no"):
        print(f"removing console logger")
        logger.removeHandler(stream_handler)
    elif log_to_console.lower() in ("true", "yes"):
        print(f"adding console logger")
        logger.setLevel(loglevel)
        stream_handler.setLevel(loglevel_env)
        print(f"console loglevel: {loglevel_env}")
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    else:
        stream_handler.setLevel(loglevel_env)

    logger.debug(
        f"Running: ----------------------------------------------------------------------------------------------------"
    )
    logger.debug(f'         {" ".join(sys.argv)} ')

    # JSON LOGGER
    # FIXME: jsonlogger name
    jsonlogfile = f"{logfile.rstrip('.log')}-json.log"
    jsonlogger = logging.getLogger("jsondata")
    jsonfile_handler = RotatingFileHandler(jsonlogfile, maxBytes=100**6, backupCount=2)
    jsonfile_handler.setFormatter(formatter)
    jsonfile_handler.setLevel(loglevel)
    jsonlogger.setLevel(loglevel)
    jsonlogger.addHandler(jsonfile_handler)

    return (logger, jsonlogger)


(logger, jsonlogger) = setup_logging()
