#!/usr/bin/env python3
# vim: tw=100 foldmethod=indent
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=redefined-outer-name, logging-not-lazy, logging-format-interpolation, logging-fstring-interpolation
# pylint: disable=missing-docstring, trailing-whitespace, trailing-newlines, too-few-public-methods
#
# Author: Joshua Bachmeier <joshua.bachmeier@student.kit.edu>
#

import sys
import json
import logging
from ldf_adapter import logsetup
from ldf_adapter.logsetup import jsonlogger

# Must be before the first ldf_adapter import
from feudal_globalconfig import globalconfig

from ldf_adapter import User
from ldf_adapter.results import ExceptionalResult, FatalError
from ldf_adapter.cmdline_params import args

logger = logging.getLogger(__name__)


class PathTruncatingFormatter(logging.Formatter):
    """formatter for logging"""

    def format(self, record):
        pathname = record.pathname
        if len(pathname) > 23:
            pathname = "...{}".format(pathname[-19:])
        record.pathname = pathname
        return super(PathTruncatingFormatter, self).format(record)


def main():
    if args.test:
        logger.info("test mode")
        data = {
            "state_target": "test",
            "user": {
                "userinfo": {
                    "sub": "test",
                    "iss": "test",
                }
            },
        }
    else:
        try:
            data = json.load(sys.stdin)
        except json.decoder.JSONDecodeError as e:
            message = "Cannot decode the input json. Please verify the input!"
            logger.error(message)
            raise FatalError(message=message)

    logger.debug(f"Attempting to reach state '{data['state_target']}'")

    if data["user"]["userinfo"] is None:
        message = "Cannot process null input"
        logger.error(message)
        raise FatalError(message=message)

    try:
        result = User(data).reach_state(data["state_target"])
    except ExceptionalResult as result:
        result = result.attributes
        logger.debug("Reached state '{state}': {message}".format(**result))
        json.dump(result, sys.stdout)
    else:
        result = result.attributes
        logger.debug("Reached state '{state}': {message}".format(**result))
        json.dump(result, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
