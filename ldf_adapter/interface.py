#!/usr/bin/env python3
#
# Author: Joshua Bachmeier <joshua.bachmeier@student.kit.edu>
#

import os
import sys
import json
import logging

# Must be before the first ldf_adapter import
from feudal_globalconfig import globalconfig

from ldf_adapter import User
from ldf_adapter.results import ExceptionalResult

logger = logging.getLogger('')

class PathTruncatingFormatter(logging.Formatter):
    '''formatter for logging'''
    def format(self, record):
        pathname = record.pathname
        if len(pathname) > 23:
            pathname = '...{}'.format( pathname[-19:])
        record.pathname = pathname
        return super(PathTruncatingFormatter, self).format(record)

def main():

    # Setup logging:
    for h in logger.handlers:
        logger.removeHandler(h)


    loglevel=os.environ.get("LOG", "INFO")
    if loglevel=="DEBUG":
        logformat = '%(asctime)s [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
        formatter  = PathTruncatingFormatter(logformat)
    else:
        logformat  = '[%(levelname)s] [%(filename)s] %(message)s'
        formatter = logging.Formatter(logformat)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.setLevel(loglevel)

    data = json.load(sys.stdin)

    logger.debug(f"Attempting to reach state '{data['state_target']}'")

    if data['user']['userinfo'] is None:
        logger.error(f"Cannot process null input")
        sys.exit(2)

    try:
        result = User(data).reach_state(data['state_target'])
    except ExceptionalResult as result:
        result = result.attributes
        logger.debug("Reached state '{state}': {message}".format(**result))
        json.dump(result, sys.stdout)
    else:
        result = result.attributes
        logger.debug("Reached state '{state}': {message}".format(**result))
        json.dump(result, sys.stdout)

    return 0

if __name__ == '__main__':
    sys.exit(main())
