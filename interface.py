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

    config_files = [os.environ['HOME']+'/.config/ldf-interface.conf',
                    folder_of_executable + '/ldf-interface.conf',
                    '/root/configs/ldf-interface.conf']

    parser = configargparse.ArgumentParser(
            default_config_files = config_files,
            description='''ldf-interface''')
    parser.add('-c', '--my-config', is_config_file=True, help='config file path')
    parser.add_argument('--verbose', '-v',
            action="count", default=0,
            help='Verbosity')
    parser.add_argument('--force_registration', 
            action="store_true", default=False,
            help='Force re-registration')
    parser.add_argument('--fake', '-f',
            action="store_true", default=False,
            help='Use fake input data')
    parser.add_argument('--fake_remove', '-fr',
            action="store_true", default=False,
            help='Use fake input data')
    parser.add_argument('--logfile',     '-l', default='ldf-interface.log')
    parser.add_argument('--loglevel',          default='warning')
    parser.add_argument('--rest_user',   '-u', help='username for LDF rest interface', required=True)
    parser.add_argument('--rest_passwd', '-p', help='passwdname for LDF rest interface', required=True)
    parser.add_argument('--ldf_service',       default='sshtest', required=True)


    # options for parsing incoming data:
    parser.add_argument('--state_target'         , action="append")
    # parser.add_argument('--user'                 , action="append")
    parser.add_argument('--name'                 , action="append")
    parser.add_argument('--surName'              , action="append")
    parser.add_argument('--givenName'            , action="append")
    parser.add_argument('--iss'                  , action="append")
    parser.add_argument('--sub'                  , action="append")
    parser.add_argument('--key'                  , action="append")
    parser.add_argument('--groups'               , action="append")
    parser.add_argument('--questionnaire'        , action="append")
    parser.add_argument('--email'                , action="append")
    parser.add_argument('--preferred_username'   , action="append")
    parser.add_argument('--eduPersonEntitlement' , action="append")
    parser.add_argument('--mandatory_parameters' , action="append")
    parser.add_argument('--optional_parameters'  , action="append")
    parser.add_argument('--deploy_parameters'    , action="append")
    parser.add_argument('--remove_parameters'    , action="append")

    parser.add_argument('--primaryGroupIdFmt'    , action="append")
    parser.add_argument('--bwidmOrgIdFmt'        , action="append")
    parser.add_argument('--sshKeyFmt'            , action="append")
    parser.add_argument('--emailFmt'             , action="append")
    parser.add_argument('--surNameFmt'           , action="append")
    parser.add_argument('--givenNameFmt'         , action="append")

    parser.add_argument('--externalIdFmt'        , action="append")
    parser.add_argument('--eppnFmt'              , action="append")
    parser.add_argument('--noveltyFmt'           , action="append")
    parser.add_argument('--preferred_usernameFmt', action="append")

    parser.add_argument('--base_url'             , default="https://bwidm-test.scc.kit.edu/rest/")
    parser.add_argument('--verify_tls'           , default=True    , action="store_false" , help='disable verify')
    parser.add_argument('--issTranslateExpression', action="append")
            
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

    # ensure translation will work
    try:
        for i in range (0, 2):
            args.issTranslateExpression[i] = remove_quotes(args.issTranslateExpression[i])
    except:
        logging.error('FATAL: issTranslateExpression needs to consist of exactly two entries: ["what to replate", "with what"]')
        logging.error('Instead you provided "%s"' % str(args.issTranslateExpression))
        raise

    # if args.verbose > 1:
        # logging.debug(parser.format_values())
    return args
# }}}
def get_jObject():# {{{
    data = ""
    if args.fake:# {{{
    # jObject 
        jObject = json.loads(str('''    {
        "state_target": "deployed",
        "user": {
            "email": "marcus@lalala.de",
                "groups": [
                    "/myExampleColab",
                    "/hdfdev",
                    "/"
                ],
            "userinfo": {
                "eduPersonEntitlement": [
                    "urn:test:hdf:group:root#unity.helmholtz-data-federation.de",
                    "urn:test:hdf:group:root:myExampleColab#unity.helmholtz-data-federation.de"
                ],
                "email": "marcus.hardt@kit.edu",
                "email_verified": "true",
                "groups": [
                    "/myExampleColab",
                    "/hdfdev",
                    "/"
                ],
                "name": "Marcus Hardt",
                "preferred_username": "marcus",
                "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2013",
                "sub": "61230996-664f-4422-9caa-76cf086f0d6c",
                "iss": "https://unity.helmholtz-data-federation.de/oauth2"
            }
        },
        "key": {
            "name": "Kee",
            "key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2018"
        },
        "questionnaire": null
    }'''))
        return jObject# }}}
    if args.fake_remove:# {{{
    # jObject 
        jObject = json.loads(str('''    {
        "state_target": "not_deployed",
        "user": {
            "email": "marcus@lalala.de",
                "groups": [
                    "/myExampleColab",
                    "/hdfdev",
                    "/"
                ],
            "userinfo": {
                "eduPersonEntitlement": [
                    "urn:test:hdf:group:root#unity.helmholtz-data-federation.de",
                    "urn:test:hdf:group:root:myExampleColab#unity.helmholtz-data-federation.de"
                ],
                "email": "marcus.hardt@kit.edu",
                "email_verified": "true",
                "groups": [
                    "/myExampleColab",
                    "/hdfdev",
                    "/"
                ],
                "name": "Marcus Hardt",
                "preferred_username": "marcus",
                "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2013",
                "sub": "61230996-664f-4422-9caa-76cf086f0d6c",
                "iss": "https://unity.helmholtz-data-federation.de/oauth2"
            }
        },
        "key": {
            "name": "Kee",
            "key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2018"
        },
        "questionnaire": null
    }'''))
        return jObject# }}}
    # if len(sys.argv) == 2:
    #     data = sys.argv[1]
    # else:
    data = sys.stdin.read()
    Json = data
    # Json = str(data)+ '=' * (4 - len(data) % 4)
    try:
        jObject = json.loads(str(Json))
        # logging.debug('json decoding worked fine')
    except json.decoder.JSONDecodeError as e:
        logging.error('cannot decode your json: %s' % str(e))
        logging.error('this is your json: "%s"' % str((Json)))
        exit (13)
    except Exception as e:
        try:
            jObject = json.loads(str(Json))
            logging.debug('json decoding worked fine in 4th attempt')
        except:
            logging.error('There is no way out of this hell: %s' % str(e))
            logging.error('this is your json: "%s"' % str((Json)))
            exit (14)

    return jObject
# }}}
def find_keys_in_input(inData, search_list, key_name):# {{{
    '''seach inData for list and return key on the first found list item'''
    # logging.debug('search list: {}'.format(str(search_list)))
    if search_list is None:
        # logging.debug ("Defaulting to finding the key by the name itself: %s"%key_name)

        search_list = [key_name]
    for entry in search_list:
        if entry == 'key':
            key = inData['key'].get('key')
        else:
            key = inData.get(entry)
        if key is not None:
            # logging.info('found {} in inData: {}'.format(entry, key))
            return key
        
        key = inData['user'].get(entry)
        if key is not None:
            # logging.info('found {} in inData["user"]: {}'.format(entry, key))
            return key

        key = inData['user']['userinfo'].get(entry)
        if key is not None:
            # logging.info('found {} in inData["user"]["userinfo"]: {}'.format(entry, key))
            return key
    return None
# }}}
def generate_surName_givenName_from_name(data):# {{{
    try:
        fullName = data['user']['userinfo']['name']
    except AttributeError:
        logging.debug('Cannot find a "name" claim in userinfo. No surName and givenName can be derived')
    (givenName, surName) = fullName.split(' ')
    if args.verbose>1:
        logging.info('Converted >>%s<< to surName: "%s" givenName "%s"' % (fullName, surName, givenName))
    # And store it so it will be found by later software:
    data['user']['surName']   = surName
    data['user']['givenName'] = givenName
    return data
    # }}}
def sanitize_newlines (data):#{{{
    # remove newlines from ssh keys:

    # unity key:
    try:
        data['user']['userinfo']['ssh_key'] = data['user']['userinfo']['ssh_key'].rstrip('\n')
    except KeyError:
        pass
    # feudal key:
    try:
        data['key']['key'] = data['key']['key'].rstrip('\n')
    except KeyError:
        pass
    return data
#}}}
def get_params_from_input(inData, args):# {{{
    params = {}
    for conf_item in args.mandatory_parameters:
        if args.verbose>2:
            logging.debug('getting value for {}'.format(conf_item))
        try:
            value = find_keys_in_input(inData, getattr(args, conf_item), conf_item)
        except AttributeError:
            logmsg = "Fatal: the parameter '%s' is not supported by this interface program." % conf_item
            logmsg += "Please add it in the 'parseOptions' function"
            logging.error (logmsg)
            return ("failed", logmsg)
        if value is None:
            logmsg = 'Fatal: A mandatory config value was not found in input, while processing "%s"'%conf_item
            logging.error (logmsg)
            return ("failed", logmsg)
        params[conf_item] = value
        if args.verbose>1:
            logging.debug('    got mandatory value for {:13s}: {}'.format(conf_item, value))

    for conf_item in args.optional_parameters:
        if args.verbose>2:
            logging.debug('getting value for {}'.format(conf_item))
        try:
            value = find_keys_in_input(inData, getattr(args, conf_item), conf_item)
        except AttributeError:
            logmsg =  "Fatal: a specified parameter is not supported by this interface program."
            logmsg += "Please add it in the 'parseOptions' function"
            logging.error (logmsg)
            return ("failed", logmsg)
        params[conf_item] = value
        if args.verbose>1:
            logging.debug('    got optional value for  {:13s}: {}'.format(conf_item, value))

    # replace the iss string:
    iTE = args.issTranslateExpression
    if len(iTE) != 2:
        log =  'FATAL: issTranslateExpression needs to consist of exactly two entries: ["what to replate", "with what"]'
        log += 'Instead you provided "%s"' % iTE
        logging.error (logmsg)
        return ("failed", logmsg)

    # in case user provides https?:// in iTE, we just remove it:
    iTE[0] = re.sub('^https?://', '', iTE[0])
    # then we also remove it in the actual value, too
    params['iss'] = re.sub('^https?://', '', params['iss'])
    params['iss'] = re.sub(iTE[0], iTE[1], params['iss'])

    return ("success", params)
# }}}
def dump_config_to_log(inData, params):# {{{
    if args.verbose>3:
        logging.debug ('Incoming state_target:   {}'.format(params['state_target']))
        # logging.debug ('Incoming user Object:    {}'.format(user))
        logging.debug ('Incoming usersub@iss:    {}@{}'.format(params['sub'],params['iss']))
        logging.debug ('  preferred_username:    {}'.format(params['preferred_username']))
        logging.debug ('Incoming questionnaire:  {}'.format(params['questionnaire']))
        logging.debug ('Incoming oidc_email:     {}'.format(params['email']))
        logging.debug ('Incoming oidc_groups:    {}'.format(params['groups']))
        # logging.debug ('Incoming key:            {}'.format(key))

        logging.debug ('config rest: rest_user:  {}'.format(args.rest_user))
        logging.debug ('config rest: rest_passwd:{}'.format(args.rest_passwd))
# }}}
def user_exists(externalId):# {{{
    externalId = remove_quotes(externalId)
    url = args.base_url + '/external-user/find/externalId/' + str(externalId)
    resp = requests.get (url, verify=args.verify_tls, auth=(args.rest_user, args.rest_passwd))

    if resp.status_code != 200:
        #print("\nthere was a problem in communication with the server.")
        #print("the server said: %s (%s)" \
        #        % (resp.status_code, resp.reason))
        #print ("")
        pass
    if resp.status_code == 403:
        return False
    try:
        resp_json=resp.json()
    except Exception as e:
        # print ("\nJSONDecodeError: {0}".format(e))
        # print ("terminating")
        logmsg = 'Error: ' + str(e) + '\nserver said: '
        logmsg += resp.text
        logging.error (logmsg)
        return False
    
    if args.verbose>2:
        logging.debug("\n"+json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': ')))

    if externalId == resp_json['externalId']:
        return True
    
    return False
# }}}
def create_initial_user(externalId):# {{{
    externalId = remove_quotes(externalId)
    url = args.base_url + '/external-user/create'
    headers ={'Content-Type': 'application/json'}
    data = json.dumps({'externalId':externalId})

    resp = requests.post (url, verify=args.verify_tls, auth=(args.rest_user, args.rest_passwd),\
            headers = headers, data = data)

    if resp.status_code == 200:
        resp_json=resp.json()
        if args.verbose:
            logging.info('update successful: %s' % str(json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': '))))
        if resp_json['result'] != 'success':
            logging.warning('update successful, but no "result=success" received; Check with REST admin')
        if args.verbose>1:
            logging.debug("\n\n"+json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': ')))
        return ("success", "")
    logging.debug('Obtained this return code: >>%s<<\n%s' % (resp.status_code, resp.json()))

    logging.warning("\nthere was an unexpected status.")
    logging.warning("the server said: %s (%s)" % (resp.status_code, resp.reason))
    
    if resp.status_code == 405:
        logging.info("Got 405... User probably already exists")
        return ("success", "")
    
    return ("failed", "There was an unexpected status. the server said: %s (%s)" % (resp.status_code, resp.reason))

# }}}
def update_user(data): # {{{

    url = args.base_url + '/external-user/update'
    headers ={'Content-Type': 'application/json'}
    # logging.info('will update the user, using this data: %s' %\
    #                 json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))
    # print ('''{{"externalId": "{externalId}"}}'''.format(**data))

    # sanitise sshKey:
    postData = \
'''{{"externalId":"{externalId}",
"eppn":"{eppn}",
"email":"{email}",
"genericStore": {{
    "key":"{sshKey}"
    }},
"surName":"{surName}",
"givenName":"{givenName}",
"primaryGroup":{{
    "id":"{primaryGroupId}"
    }},
"attributeStore": {{
    "urn:oid:0.9.2342.19200300.100.1.1":"{preferred_username}",
    "http://bwidm.de/bwidmOrgId":"{bwidmOrgId}"
    }}
}}'''.format(**data)

    try:
        postData_json=json.loads(postData)
    except json.decoder.JSONDecodeError as e:
        logging.error('FATAL: your json is invalid')
        logging.error(str(e))
        logging.error('For reference, this is your json:\n'+postData)
        return ("failed", "Invalid json, check server log")

    json_data = json.dumps(postData_json)
    if args.verbose>1:
        logging.debug('postData_json %s\n'%\
            json.dumps(postData_json, sort_keys=True, indent=4, separators=(',', ': ')))

    resp = requests.post (url, verify=args.verify_tls, auth=(args.rest_user, args.rest_passwd),\
            headers = headers, data = json_data)

    if resp.status_code == 200:
        resp_json = resp.json()
        if args.verbose:
            logging.info('update successful: %s' % str(json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': '))))
        if resp_json['result'] != 'success':
            logging.warning('update successful, but no "result=success" received; Check with REST admin')
        return ("success", "")
    try:
        logmsg = 'Obtained this return code: >>%s<<\n%s' % (resp.status_code, resp.json())
    except:
        logmsg = 'Obtained this return code: >>%s<<\n%s' % (resp.status_code, resp.text)
    logging.debug(logmsg)
    return ("failed", logmsg)
# }}}
def register_user_for_service(externalId, serviceName):# {{{
    url = args.base_url + '/external-reg/register/externalId/' + str(externalId) + '/ssn/' + str(serviceName)
    logging.debug('registering with this url: %s' % str(url))
    resp = requests.get (url, verify=args.verify_tls, auth=(args.rest_user, args.rest_passwd))
    
    if resp.status_code == 200:
        resp_json = resp.json()
        if args.verbose:
            logging.info('registration successful: %s' % str(json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': '))))
        try:
            if resp_json['result'] != 'success':
                logging.warning('registration successful, but no "result=success" received; Check with REST admin')
        except KeyError:
            pass
        return ("success", "")

    msg = "something went wrong registering {} for service {}".format(externalId, serviceName)
    logging.error(msg)
    logmsg = msg
    try:
        msg = resp.json()
    except json.decoder.JSONDecodeError:
        msg = resp.text
    logging.error(msg)
    logmsg += '\n' + msg
    return ("failed", logmsg)
# }}}
def deregister_user_from_service(externalId, serviceName):# {{{
    url = args.base_url + '/external-reg/deregister/externalId/' + str(externalId) + '/ssn/' + str(serviceName)
    logging.debug('deregistering with this url: %s' % str(url))
    resp = requests.get (url, verify=args.verify_tls, auth=(args.rest_user, args.rest_passwd))
    
    if resp.status_code == 200:
        resp_json = resp.json()
        if args.verbose:
            logging.info('deregistration successful: %s' % str(json.dumps(resp_json, sort_keys=True, indent=4, separators=(',', ': '))))
        if resp_json['result'] != 'success':
            logging.warning('deregistration successful, but no "result=success" received; Check with REST admin')
        return ("success", "")
    if resp.status_code == 204:
        logging.info('deregistration apparently successful, but got no result')
        return ("success", "")

    msg = "something went wrong deregistering: {} from service {}".format(externalId, serviceName)
    logging.error(msg)
    logmsg = msg
    msg = "code: %d" %resp.status_code
    logging.error(msg)
    logmsg += '\n' + msg
    try:
        msg = resp.json()
    except json.decoder.JSONDecodeError:
        msg = resp.text
    except simplejson.errors.JSONDecodeError:
        msg = resp.text
    logging.error(msg)
    logmsg += '\n' + msg
    return ("failed", logmsg)
# }}}
def assert_all_variables_defined_in_format(entry, params):# {{{
    ''' make sure the format string "entry" can be filled using data in params'''
    for unformatted_variable in re.findall('{[a-zA-Z0-9.-/]*}', entry):
        variable = re.sub('[{}]', '', unformatted_variable)
        try:
            if params[variable] is None or params[variable] == "None" or params[variable] == "null" or params[variable] == "":
                if variable in args.mandatory_parameters:
                    logging.error ("Error: Mandatory variable: {} is undefined!".format(variable))
                    return False
                if args.verbose>1:
                    logging.info("Optional variable: {} is undefined!".format(variable))
                return False 
        except KeyError:
            logging.error ('Error: Variable unknown: "{}" while parsing {}'.format(variable, entry))
            return False
    return True
# }}}
def get_all_variables_from_list(parameterList, params):# {{{
    entry   = ''
    outData = {}
    # print ("\n\nparameterlist; >>%s<<" % parameterList)
    for entry_name in parameterList:
        ''' first get the entry name, and try to obtain the format string for it'''
        # print ("\n\nentry_name: >>%s<<"%entry_name)
        try:
            entry_value = getattr(args, entry_name+'Fmt')
        except AttributeError:
            logmsg = 'FATAL: "%s" is not a supported parameter. This needs to be fixed in the code in "parseOptions"' % entry_name
            logging.error (logmsg)
            return ("failed", logmsg)
        try: # Make sure we can iterate over entry_value
            iter(entry_value)
        except TypeError:
            logmsg = 'FATAL: there is no format string for "%sFmt". You need to define it in your config.' % entry_name
            logging.error (logmsg)
            return ("failed", logmsg)
        # print ("\n\nentry_value: >>%s<<"%entry_value)
        for entry in entry_value:
            ''' For each entry in the list of possible formats, try it out and break, once the first one worked'''
            # make sure that none of the fields used in entry are undefined, "None" or "":
            if not assert_all_variables_defined_in_format(entry, params):
                continue
                
            # Then use the format
            outData[entry_name] = entry.format(**params)
            # print ("\n\n entry: >>%s<<   \nformatted: >>%s<<" % (entry, entry.format(**params)))
            # logging.debug("params: "+json.dumps(params, sort_keys=True, indent=4, separators=(',', ': ')))
            break
        if outData.get(entry_name) is None:
            logmsg = "FATAL: Could not obtain values for %s" % entry_name
            logging.error (logmsg)
            return ("failed", logmsg)
        if args.verbose>1:
            logging.info('{:23s}: {:23s}: {}'.format(entry_name, entry,  outData[entry_name]))
    return ("success", outData )
# }}}

# args are global
args = parseOptions()

def main():
    # https://bwidm-test.scc.kit.edu/rest/external-reg/find/externalId/marcus-test-10
    # setup logging{{{
    import logging.config
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
    })
    logformat = "{%(asctime)s %(filename)s:%(funcName)s:%(lineno)d} %(levelname)s - %(message)s"
    loglevel = logging.getLevelName(args.loglevel.upper())
    logging.basicConfig(level=loglevel, format=logformat, filename=args.logfile)
    logging.debug('\n\n\nfum_ldf-interface v.0.0.1')

    if args.verbose > 3:
        import http.client as http_client
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        # logging.getLogger().setLevel(logging.ERROR)
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info('verbosity: %d' % args.verbose)# }}}

    # get data from stdin from the FEUDAL side{{{
    inData  = get_jObject()
    inData  = generate_surName_givenName_from_name(inData)
    inData  = sanitize_newlines(inData)
    (state, params)  = get_params_from_input(inData, args)
    if state != "success":
        return ("failed", params)

    (state, info_data) = get_all_variables_from_list(['email', 'eppn'], params)
    logging.debug('Got request to %s user:  ({email} - {eppn})'.format(**info_data) % inData['state_target'])

    if args.verbose>1:
        logging.debug("inData: "+json.dumps(inData, sort_keys=True, indent=4, separators=(',', ': ')))
    if args.verbose>1:
        logging.debug("params: "+json.dumps(params, sort_keys=True, indent=4, separators=(',', ': ')))
# }}}

    desiredState = inData['state_target'] # one of "deployed" "removed" "rejected" "failed"

    if desiredState == 'deployed':# {{{
        # Derive all the variables required for LDAP Facade:
        (state, outData) = get_all_variables_from_list(args.deploy_parameters, params)
        if args.verbose>1:
            logging.debug("outdata: "+json.dumps(outData, sort_keys=True, indent=4, separators=(',', ': ')))
        if state != "success":
            logging.error('Failed to initialise deployment variables for user:  ({email} - {eppn})'.format(**info_data))
            return("failed", outData)

        # And go create the user
        # fake some input data
        if args.fake or args.fake_remove:
            outData['externalId'] = 'marcus-test-10'
            outData['preferred_username'] = 'marcus-test-10'

        # save state, whether user existed
        user_existed_before = user_exists (outData['externalId'])

        # create initial user{{{
        if not user_existed_before:
            logging.info('User didn\'t exist. Will create')
            (state, message) = create_initial_user(outData['externalId'])
            if state != "success":
                logmsg = 'Failed to create the initial user:  ({email} - {eppn})'.format(**info_data)
                if args.verbose > 0:
                    logmsg += 'FATAL: Failed to create an initial user with this data:\n%s' %\
                            json.dumps(outData, sort_keys=True, indent=4, separators=(',', ': '))
                logging.error(logmsg)
                if args.verbose:
                    message = message + '\n' + logmsg
                return (desiredState,message)

            logging.info('Initial user created')
        else:
            logging.info('Skipping initial creation of user, since he existed already')
        # }}}
        # update the user{{{
        logging.info('Will update user now')
        (state, message) = update_user(outData)
        if state != "success":
            logmsg = 'Failed to create the full user:  ({email} - {eppn})'.format(**info_data)
            if args.verbose > 0:
                logmsg += 'FATAL: Failded to create the full user with this data:\n%s' %\
                        json.dumps(outData, sort_keys=True, indent=4, separators=(',', ': '))
            logging.error(logmsg)
            if args.verbose:
                message = message + '\n' + logmsg
        return (desiredState, message)
        logging.info("user created / updated successfully")
        # }}}
        # register user for service{{{
        if not user_existed_before or args.force_registration: 
            # FIXME: This is a hack: we only register users, if they
            # didn't exit before; This should be fixed once LDF REST provides this functionality
            logging.info('registering user:  ({email} - {eppn})'.format(**info_data))
            (state, message) = register_user_for_service(outData['externalId'], args.ldf_service)
            if state != "success":
                return ('failed', message)
        else:
            logging.info('skipping registration of user, since he existed already; Note: This is a hack and needs to be fixed')
        return (desiredState, message)
    # }}}}}}
    elif desiredState == 'not_deployed':    # undeploy user{{{
        (state, outData) = get_all_variables_from_list(args.remove_parameters, params)
        if args.verbose>2:
            logging.debug("outdata: "+json.dumps(outData, sort_keys=True, indent=4, separators=(',', ': ')))
        if state != "success":
            return ("failed", outData)

        # fake userdata
        if args.fake or args.fake_remove:
            outData['externalId'] = 'marcus-test-10'
            outData['preferred_username'] = 'marcus-test-10'

        # do the actual undeployment
        (state, message) = deregister_user_from_service(outData['externalId'],  args.ldf_service)
        if state != "success":
            logmsg = 'Failed to undeploy user:  ({email} - {eppn})'.format(**info_data)
            if args.verbose > 0:
                logmsg += 'FATAL: Failded undeployment with this data:\n%s' %\
                        json.dumps(outData, sort_keys=True, indent=4, separators=(',', ': '))
            return ("failed", message+logmsg)
        return (desiredState, message)
    return ('failed', 'undefined desired state_target')
# }}}

if __name__ == "__main__":
    (state, message) = main()
    message = 'what do you mean, message?'
    logging.debug('state: %s' % state)
    logging.debug('            message: >>%s<<' % message)
    return_json = '{"state": "%s", "message": "%s", "credential": "these are your credentials<br/> asdf"}' % (state, message)
    logging.debug('return_json: >>%s<<' % return_json)
    print (return_json)
