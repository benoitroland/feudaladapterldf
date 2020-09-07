#!/usr/bin/env python3
#
# Author: Joshua Bachmeier <joshua.bachmeier@student.kit.edu>
#

import os
import sys
import json
import logging

from ldf_adapter import User
from ldf_adapter.results import ExceptionalResult

def main():
    logging.basicConfig(
        level=os.environ.get("LOG", "INFO")
        #format='%(asctime)s [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
    )

    logger = logging.getLogger(__name__)

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
