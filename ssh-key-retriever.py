#!/usr/bin/env python3
# pylint # {{{
# vim: tw=100 foldmethod=marker
# pylint: disable=bad-continuation, invalid-name, superfluous-parens
# pylint: disable=bad-whitespace, mixed-indentation
# pylint: disable=redefined-outer-name, logging-not-lazy, logging-format-interpolation
# pylint: disable=missing-docstring, trailing-whitespace, trailing-newlines, too-few-public-methods
# }}}

import sys
import os
import json
import base64
import logging
import re
import requests
import configargparse
import simplejson

def remove_quotes(data):# {{{
    return data.lstrip('"').lstrip("'").rstrip('"').rstrip("'")
# }}}
def parseOptions():# {{{
    '''Parse the commandline options'''

    path_of_executable = os.path.realpath(sys.argv[0])
    folder_of_executable = os.path.split(path_of_executable)[0]

    config_files = [os.environ['HOME']+'/.config/ssh-key-retriever.conf',
                    folder_of_executable + '/ssh-key-retriever.conf',
                    '/root/configs/ssh-key-retriever.conf']

    parser = configargparse.ArgumentParser(
            default_config_files = config_files,
            description='''ssh-key-retriever''')
    parser.add('-c', '--my-config', is_config_file=True, help='config file path')
    parser.add_argument('--verbose', '-v',
            action="count", default=0,
            help='Verbosity')
    parser.add_argument('--logfile',     '-l', default='ldf-interface.log')
    parser.add_argument('--loglevel',          default='warning')
    parser.add_argument('--rest_user',   '-u', help='username for LDF rest interface', required=True)
    parser.add_argument('--rest_passwd', '-p', help='passwdname for LDF rest interface', required=True)
    parser.add_argument('--ldf_service',       default='sshtest', required=True)
    parser.add_argument('--base_url'         , default="https://bwidm-test.scc.kit.edu/rest/")
    parser.add_argument('--verify_tls'           , default=True    , action="store_false" , help='disable verify')

    args = parser.parse_args()

    # consistently remove all quotes from all input parameters:
    for arg in vars(args):
        typeOfArg = type(getattr(args, arg))
        # print ("\narg: %s -- %s"%(arg, typeOfArg))
        # print ("  before: %s: %s" %(arg, getattr(args, arg)))
        if isinstance (getattr(args, arg),  str):
            setattr(args, arg, remove_quotes(getattr(args, arg)))
            # print ("  after:  %s: %s\n\n\n" %(arg, getattr(args, arg)))
        elif isinstance(getattr(args, arg),  list):
            newlist = []
            for entry in getattr(args, arg):
                entry =  remove_quotes(entry)
                newlist.append(entry)
            setattr(args, arg, newlist)
            # print ("  after:  %s: %s\n\n\n" %(arg, getattr(args, arg)))

    # sanitise parameters
    args.base_url = args.base_url.rstrip('/"')
    args.base_url = args.base_url.lstrip('"')

    # if args.verbose > 1:
        # logging.debug(parser.format_values())
    return args
# }}}

# args are global
args = parseOptions()

def get_sshkeys(externalId='hdf_61230996-664f-4422-9caa-76cf086f0d6c@unity-hdf'):# {{{
    externalId = remove_quotes(externalId)
    url = args.base_url + '/external-user/find/externalId/' + str(externalId)
    resp = requests.get (url, verify=args.verify_tls, auth=(args.rest_user, args.rest_passwd))
    if resp.status_code != 200:
        logging.error ('Could not retrieve ssh-keys for user {externalId}.  Most likely the user is not found'.format(**locals()))
        return None

    try:
        resp_json = resp.json()
    except json.JSONDecodeError:
        logging.error ('Could not decode json that I obtained from rest server')

    # print ("\n"+json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': ')))

    sshkeys = resp_json['genericStore']['key']
    if args.verbose:
        logging.debug('just obtained keys: %s' % str(sshkeys))
    return sshkeys
    # }}}
def main():

    # setup logging{{{
    import logging.config
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
    })
    logformat = "{%(asctime)s %(filename)s:%(funcName)s:%(lineno)d} %(levelname)s - %(message)s"
    loglevel = logging.getLevelName(args.loglevel.upper())
    logging.basicConfig(level=loglevel, format=logformat, filename=args.logfile)
    logging.debug('\n\n\n ssh-key-retriever-v.0.0.1')
    #}}}
    sshkeys = get_sshkeys()
    return sshkeys

if __name__ == "__main__":
    keys = main()
    print (keys)
