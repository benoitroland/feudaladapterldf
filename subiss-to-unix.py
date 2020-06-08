#!/usr/bin/env python3
# pylint 
# vim: tw=100
# pylint: disable=bad-continuation, invalid-name, superfluous-parens
# pylint: disable=bad-whitespace, mixed-indentation
# pylint: disable=redefined-outer-name, logging-not-lazy, logging-format-interpolation
# pylint: disable=missing-docstring, trailing-whitespace, trailing-newlines, too-few-public-methods

import sys
import os
import re
import json
import requests
import logging
import argparse
from pathlib import Path
from configparser import ConfigParser
from configparser import ExtendedInterpolation
import urllib.parse as ul

# CONFIG = ConfigParser()
CONFIG = ConfigParser(interpolation=ExtendedInterpolation())
CONFIG.optionxform = lambda option: option

# Logging
logformat='[%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
logging.basicConfig(level=os.environ.get("LOG", "WARN"), format = logformat)
logger = logging.getLogger(__name__)

# Functions
def load_config():
    """Reload configuration from disk.

    Config locations, by priority (all values are merged. The last one
        overwrites earlier ones)
    """
    files = []
    try:
        files += [ Path(args.pathconf_file) ]
    except:
        pass

    logger.info("reading config")

    files += [
        Path('./subiss-to-unix.conf'),
        Path(Path.home(),'.config','subiss-to-unix.conf'),
        Path('/etc/subiss-to-unix.conf')
    ]

    for f in files:
        if f.exists():
            logger.info("Using this config file: {}".format(f))
            CONFIG.read(f)
            break

def remove_quotes(data):
    return data.lstrip('"').lstrip("'").rstrip('"').rstrip("'")

def parseOptions():
    '''Parse the commandline options'''

    path_of_executable = os.path.realpath(sys.argv[0])
    folder_of_executable = os.path.split(path_of_executable)[0]
    full_name_of_executable = os.path.split(path_of_executable)[1]
    name_of_executable = full_name_of_executable.rstrip('.py')

    parser = argparse.ArgumentParser()

    parser.add_argument('--rest_user',   '-u',             help='username for LDF rest interface')
    parser.add_argument('--rest_passwd', '-p',             help='passwdname for LDF rest interface')
    parser.add_argument('--iss'                  , action="append")
    parser.add_argument('--bwidmOrgId'           , default="hdf")
    parser.add_argument('--base_url'             , default="https://bwidm-test.scc.kit.edu/rest/")
    parser.add_argument('--verify_tls'           , default=True    , action="store_false" , help='disable verify')
    parser.add_argument('--issTranslateExpression', default='{"unity-hdf": "unity.helmholtz-data-federation.de/oauth2",  "kit": "https://oidc.scc.kit.edu/auth/realms/kit"}')
    parser.add_argument(dest='sub_iss'  , help='Content of $REMOTE_USER. For testing use "test-offline" and "test-id"')
    parser.add_argument('--verbose', '-v'        , default=False   , action="store_true" )
    parser.add_argument('--debug',   '-d'        , default=False   , action="store_true" )
    args = parser.parse_args()

    # sanitize some args:
    args.base_url   = args.base_url.rstrip('/')
    args.bwidmOrgId = remove_quotes(args.bwidmOrgId)

    # ensure translation will work as JSON
    try:
        args.issTranslateExpressionJSON = json.loads(args.issTranslateExpression)
        try:
            for key in args.issTranslateExpressionJSON.keys():
                args.issTranslateExpressionJSON[key] = remove_quotes(args.issTranslateExpressionJSON[key])
        except:
            sys.stderr.write('FATAL: issTranslateExpression needs to be a one line json object that lists keys and values: \n')
            sys.stderr.write('{"unity-hdf": "unity.helmholtz-data-federation.de/oauth2", "test": "https://test.com"}')
            sys.stderr.write('Instead you provided "%s"\n' % str(args.issTranslateExpression))
            raise
    except:
        raise

    return args

args = parseOptions()
load_config()

if args.sub_iss == 'test-offline':
    sys.stdout.write('hdf_marcus\n')
    exit(0) 

if args.sub_iss == 'test-id':
    args.sub_iss = "6c611e2a-2c1c-487f-9948-c058a36c8f0e@https://login.helmholtz-data-federation.de/oauth2"
    sys.stderr.write("using test id: %s\n" % args.sub_iss)
if args.sub_iss == 'test-marcus':
    args.sub_iss = "6c611e2a-2c1c-487f-9948-c058a36c8f0e@https://login.helmholtz-data-federation.de/oauth2"
    sys.stderr.write("using test id: %s\n" % args.sub_iss)
if args.sub_iss == 'test-borja-old':
    args.sub_iss = "d9f4d895-6051-4717-883e-4b2676ad0d0d@https://login.helmholtz-data-federation.de/oauth2"
    sys.stderr.write("using test id: %s\n" % args.sub_iss)
if args.sub_iss == 'test-borja-new':
    args.sub_iss = "309ed509-c56a-4894-b163-5993bd08cbc2@https://login.helmholtz-data-federation.de/oauth2"
    sys.stderr.write("using test id: %s\n" % args.sub_iss)

externalId = args.sub_iss
vals = args.sub_iss.split('@')
sub = '@'.join(vals[0:-1]) # First few components are sub, may contain '@'
iss = vals[-1] # Last component is issuer may NOT contain '@'
externalId = ul.quote_plus(sub) + \
            '@n' + \
            ul.quote_plus(iss)

url = args.base_url + '/external-user/find/externalId/' + ul.quote_plus(str(externalId))
rest_user = CONFIG['main'].get('rest_user', 'xxx')
rest_pass = CONFIG['main'].get('rest_pass', 'xxx')
base_url = CONFIG['main'].get('base_url', '')

if args.verbose:
    logger.debug(F"URL: {url}")

resp = requests.get (url, verify=args.verify_tls, auth=(rest_user, rest_pass))

if resp.status_code != 200:
    sys.stderr.write('Error %d reading from remote: \n%s\n'% (resp.status_code, str(resp.text)))
    exit(1)

resp_json=resp.json()
try:
    username = resp_json['attributeStore']['urn:oid:0.9.2342.19200300.100.1.1']
    bwIdmOrgId = resp_json['attributeStore']['http://bwidm.de/bwidmOrgId']

    sys.stdout.write('%s_%s\n' % (bwIdmOrgId, username))
except KeyError as e:
    if args.verbose:
        # sys.stderr.write('Error interpreting remote json object: Key Error: %s not found\n' % str(e))
        sys.stderr.write('Error: I could not find the username in the database. Most likely the user is not registered for this service\n')
        sys.stderr.write('This is the json data received\n')
        sys.stderr.write(json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': ')))
        sys.stderr.write('\n')

if args.debug:
    sys.stderr.write('This is the json data received\n')
    sys.stderr.write(json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': ')))
    sys.stderr.write('\n')

