'''Parse commandline options'''
#
# Author: Marcus Hardt <hardt@kit.edu>
#
# pylint # {{{
# vim: tw=100 foldmethod=indent
# pylint: disable=bad-continuation, invalid-name, superfluous-parens
# pylint: disable=bad-whitespace, mixed-indentation
# pylint: disable=redefined-outer-name
# pylint: disable=missing-docstring, trailing-whitespace, trailing-newlines, too-few-public-methods
# }}}
import os
import sys
import logging
import argparse

logger = logging.getLogger(__name__)

def parseOptions():
    '''Parse the commandline options'''

    logger.info("reading config")
    path_of_executable      = os.path.realpath(sys.argv[0])
    folder_of_executable    = os.path.split(path_of_executable)[0]
    full_name_of_executable = os.path.split(path_of_executable)[1]
    name_of_executable      = full_name_of_executable.rstrip('.py')
    try:
        config_in_home      = os.environ['HOME']+'/.config/%s.conf' % name_of_executable
    except KeyError:
        pass

    parser = argparse.ArgumentParser(description=name_of_executable)

    parser.add_argument('--config_file', '--config','-c','--conf', 
            default='/etc/feudal/ldf_adapter.conf',
            help='Default: /etc/feudal/ldf_adapter.conf')

    return parser

# reparse args on import
args = parseOptions().parse_args()
