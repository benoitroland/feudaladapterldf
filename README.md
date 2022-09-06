# FEUDAL Client Adapter



This code implements the adapter for FEUDAL to communicate with various services, called "backends".

Distributed with the adapter are backends for [BWIDM](ldf_adapter/backend/bwidm.py) and [UNIX](ldf_adapter/backend/local_unix.py).

# Installation
## From PyPi
 - `pip install feudalAdapter`

## From Source
- Git clone: `git clone git@git.scc.kit.edu:feudal/feudalAdapterLdf.git`
- Build package: `cd feudalAdapterLDF; ./setup.py sdist`
- Install package: `pip install dist/feudalAdapter-$version.tar.gz`

# Configuration
The config file contains both the generic config, as well as for specific backends.
## Configuration Template
See [feudal_adapter_template.conf](feudal_adapter_template.conf)

## Config file search path
The config file feudal_adapter.conf will be searched in several places. Once
it is found no further config files will be considered:

- If the commandline argument `--config` is specified, that location is used.

- If the `feudal_globalconf` mechanism is used, it is used. In case there is
    also a commandline argument specified, the `globaldconf` has precedence

- If those dont work: the environment variable `FEUDAL_ADAPTER_CONFIG` is used

- If that does not work, these files will be tried by default:

- `feudal_adapter.conf`
- `$HOME/.config/feudal_adapter.conf`
- `$HOME/.config/feudal/feudal_adapter.conf`
- `/etc/feudal/feudal_adapter.conf`


# Input and Output

The FeudalAdapter is designed to work with feudalClient and hence expects
specific json on stdin, and produces specific json on stdout. 

The was initially defined [here (feudalScripts)](https://git.scc.kit.edu/feudal/feudalScripts/)

An extension is implemented, to work with [Motley Cue](https://github.com/dianagudu/motley_cue), 
therefore, we feudalAdapterLDF supports additional targets. Most of these
targets do not require the full userinfo to be passed along:

| Target         | Description                                            | Input required | Optional input |
|----------------|--------------------------------------------------------|----------------|----------------|
| `deployed`     | Make sure the user exists on the system                | Full userinfo  | ssh-keys       |
| `not_deployed` | Make sure the user is not on the system                | sub+iss        |                |
| `get_status`   | Get the current status of the user without changing it |                |                |

A more detailed view of all the supported user states, as well as actions leading to these states, can be found in [states.md](states.md).


# Development

## Debugging

For development you can use the included json files in the examples folder
and pass them on stdin:
```sh
cd [...]/feudalAdapterLDF
export PYTHONPATH=`pwd`
export LOG=DEBUG

cat examples/marcus-deploy.json | ./ldf_adapter/interface.py
```

## Debugging with FeudalClient:

For debugging, run the feudalClient with:

```sh
LOG=DEBUG feudalClient -c ~/.config/feudal/client.json --debug-scripts
```

## Development

feudalAdapter can also be used as a library; For that you can use the
feudal_globalconfig to keep it from parsing your commandline paramenters:

```python
from feudal_globalconfig import globalconfig
globalconfig.config['CONFIGFILE']="/etc/feudal/feudal_adapter_mailping.conf"
globalconfig.config['parse_commandline_args']=False
from ldf_adapter import User
```


# Supported Backends
Backends are simply python modules. The supported backends are in the
[backends](ldf_adapter/backend/) folder.

The backend is configured in the main config file, and may create and use
its own sections therein.

```conf
[ldf_adapter]
backend = my_backend

[backend.my_backend]
foo = bar
# Configuration for your backend goes here
```

Supported backends:
- local UNIX
- [LDAP](LDAP.md)
- bwIDM

## Development

To add a new backend:
- extend the `User` and `Group` classes in the [generic backend](ldf_adapter/backend/generic.py) by implementing all the required abstract methods
- the extended classes **must** also be named `User` and `Group`
- place the classes in a python file in [ldf_adapter/backend](ldf_adapter/backend) (e.g. `my_backend.py`)
- the name of the backend will be the name of the file, and it will be loaded dynamically when used (e.g. `my_backend`)
- use the new backend by setting the `backend` in the `[ldf_adapter]` section in the config file to your new backend name
  ```
  [ldf_adapter]
  backend = my_backend
  ```
- if you need to add any configuration for your backend, add a new section in the config file:
  ```
  [backend.my_backend]
  key1 = value1
  key2 = value2
  ```
- define types and default values for the configuration in [ldf_adapter/config.py](ldf_adapter/config.py) (check out the comments on adding a new section)
- you will then be able to use these configuration values in your backend with:
  ```
  from ldf_adapter.config import CONFIG
  print("key1: ", CONFIG.backend.my_backend.key1)
  print("key2: ", CONFIG.backend.my_backend.key2)
  ```


# Approval workflow

The `feudalAdapter` also supports a so-called *approval workflow*, which allows site admins to oversee all deployment requests from users, and accept or reject them manually. This workflow uses additional user states (`pending`, `rejected`), as well as a local database for storing deployment requests.

How it works:
- on a request to reach the `deployed` state, a local user (+ its groups) is "reserved" by storing this deployment request in the local database
- the response to this request is a "pending" user
- the site admin is notified of this request (currently supported notification systems: `email`)
  - for local_unix backend, notification contains all necessary `useradd`, `usermod` commands
  - for ldap backend, notification contains LDIF representation
- the site admin can then accept or reject this request by manually adding the user or, if supported, using "accepted"/"rejected" as state_target
- users are not notified of acceptance/rejection
- subsequent deployment requests for existing users check if there have been changes to the userinfo (e.g. group memberships) and notify the admin only when updates are necessary.


## Configuration

Enable and configure the approval in the config file:
```
[approval]
enabled = True

### user db location -- default: /var/lib/feudal/pending_users.db
# currently, only sqlite is used as db for pending requests.
# user_db_location = /var/lib/feudal/pending_users.db

### notifier -- default: email
# how to notify admins of incoming deployment requests; supported: email
# to test that the configuration works, try `feudal-adapter --test`
notifier = email
```

The `email` notifier will need to be configured, as it will not work out of the box. You'll need an SMTP server for sending emails. If your organisation does not provide one, you can use `gmail` (requires you to create and provide an app password).

A few more configs:
- `sent_from`: the address that the emails will be sent from
- `admin_email`: the email of the site admin that will approve the requests
- `templates_dir`: the folder where the email templates are located. Please make sure that the folder exists and contains all the files from [templates](templates). When installing `feudalAdapter` via pip, this folder is installed at `etc/feudal/templates`, relative to your python path. You are free to modify the content of the files.

To test that your email notification system works, run:
```
feudal-adapter --test
```


# Unit Tests
There are unit tests, located under [tests](tests) (The package structure in `tests` corresponds to
that of the main package). To run the tests, just do:

```sh
tox
```

# Integration with Feudal:
- Edit the FEUDAL Client config file (e.g. `~/.config/feudal/client.yaml`) to include:
```yaml
    services:
        "mclientservice":
            "name": "Demo Adapter"
            "description": "Works so well"
            "command": "feudal-adapter --conf /etc/feudal/feudal_adapter.conf"
```
------------------------------------------------------------------------

# This goes away sooner or later

# RegApp REST Interface
The rest interface of the LDAP facade supports the calls documented here.

For configuration we use these environment variables

```
USER="username"
PASS="password"
ENDP="https://bwidm-test.scc.kit.edu/rest"
```

## Create user
```
curl --basic -u $USER:$PASS \
    -H "Content-Type: application/json" \
    -X POST -d '{"externalId":"marcus-test-1"}' \
    $ENDP/external-user/create

Benutzer anlegen:

Zum Anlegen reicht eine externalId. Mehr Werte sind im Grunde nicht
notwendig. Allerdings kann man mit diesem Benutzer dann noch nicht viel
anstellen. Die externalId stellt immer das prim??re
Identifizierungsmerkmal dar. Sie ist nicht ??nderbar.

```

## Update user
Use this call to update the user object and to rewrite the generic store in the LDF.

```
curl --basic -u $USER:$PASS \
    -H "Content-Type: application/json" 
    -X POST -d ' \
{"externalId":"test0002","eppn":"test0002@hdf.de","email":"test-diezweite@kit.edu","genericStore": { "ssh_key": "[{'value': 'ssh-rsa AA[..]0R', 'name': 'unity_key'}]" },"surName":"Testfamilie","givenName":"Hans","primaryGroup":{"id":1002637},"attributeStore":{"urn:oid:0.9.2342.19200300.100.1.1":"test0002","http://bw idm.de/bwidmOrgId":"hdf"}}
' \
    $ENDP/external-user/update
```

The above, but reformatted:
```
curl --basic -u $USER:$PASS 
    -H "Content-Type: application/json" 
    -X POST -d ' 
        {
          "externalId": "test0002",
          "eppn": "test0002@hdf.de",
          "email": "test-diezweite@kit.edu",
          "genericStore": {
            "ssh_key": "[{'value': 'ssh-rsa AA[..]0R', 'name': 'unity_key'}]"
          },
          "surName": "Testfamilie",
          "givenName": "Hans",
          "primaryGroup": {
            "id": 1002637
          },
          "attributeStore": {
            "urn:oid:0.9.2342.19200300.100.1.1": "test0002",
            "http://bw idm.de/bwidmOrgId": "hdf"
          }
        }
    ' 
    $ENDP/external-user/update
```


## register user for service
```
curl --basic -u $USER:$PASS\
    $ENDP/external-reg/register/externalId/test0002/ssn/sshtest
```


Benutzer für einen Dienst registrieren:
curl --basic -u $USER:$PASS $ENDP/external-reg/register/externalId/test0002/ssn/sshtest

Dabei ist es notwendig, dass die vom Dienst geforderten Attribute gesetzt sind. Das ist bei LDAP basierten Diensten normalerweise:
* EPPN
* E-Mail-Adresse
* primaryGroup
* surName, givenName (optional)
* attributeStore:
** urn:oid:0.9.2342.19200300.100.1.1 (Unix UserId - Anmeldename)
** http://bwidm.de/bwidmOrgId (soll "hdf", bzw. konfigurierbar sein)

Der Anmeldename des Benutzers setzt sich nachher aus orgId und UserId zusammen. Also z.B. hdf_test0002

## Find user by unix user name
```
curl --basic -u $USER:$PASS $ENDP/external-user/find/attribute/urn:oid:0.9.2342.19200300.100.1.1/marcus
```

Will return multiple entries for different externalId . This is because multiple externalId can be
mapped to the same unix account.
### Example output
```
[
  {
    "id": 1007486,
    "createdAt": 1531327592699,
    "updatedAt": 1533732759215,
    "version": 7,
    "attributeStore": {
      "urn:oid:0.9.2342.19200300.100.1.1": "marcus",
      "http://bwidm.de/bwidmOrgId": "hdf"
    },
    "genericStore": {
      "ssh_key": "[{'value': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2013', 'name': 'unity_key'}]"
    },
    "eppn": "Hardt@unity-hdf",
    "email": "no@email.provided",
    "givenName": "Marcus",
    "surName": "Hardt",
    "uidNumber": 900094,
    "emailAddresses": [],
    "primaryGroup": {
      "id": 1002637,
      "createdAt": 1525327969976,
      "updatedAt": 1525327969976,
      "version": 0,
      "name": "hdf-test",
      "gidNumber": 500573,
      "parents": [],
      "users": null
    },
    "secondaryGroups": [],
    "userStatus": "ACTIVE",
    "externalId": "hdf_61230996-664f-4422-9caa-76cf086f0d6c@unity-hdf"
  },
  {
    "id": 1013939,
    "createdAt": 1536046109021,
    "updatedAt": 1542101421071,
    "version": 8,
    "attributeStore": {
      "urn:oid:0.9.2342.19200300.100.1.1": "marcus",
      "http://bwidm.de/bwidmOrgId": "hdf"
    },
    "genericStore": {
      "ssh_key": "[{'value': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2013-unity', 'name': 'unity_key'}, {'value': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCh3jF9KUaJXqbnaqaHwGmgXIes0nQMqYFx1N3sa4nfbhyBipjSfCyv3yGHO8yciPIjWGTwPUD+HhczXSOJMGruBwwHCKq2vhrdsWJy/bsCs1iBQN9d0oUyPtn+48UcY6ceZfwGcM3KIOxxMu/nzvgZXme53TXSAWH6VASrCjBSSZ/9JvDaxrgVudOW6a3LE6AZMDsi4YEhdP7FTn4wpFVyCpkIttETX26qDAbD2UuR0KNa42yyDdbzu+3ZAoYmkyCcthgsesEm692r+F6TJnBLFVVAtGiQ21cwM8wKgYUDVMZknBo8QKiLvYhvs3zuCVVKBANYqMCOeO2Z3dQem00t root@tuna2013', 'name': 'marcus'}]"
    },
    "eppn": "hardt@unity-hdf",
    "email": "marcus.hardt@kit.edu",
    "givenName": "Marcus",
    "surName": "Hardt",
    "uidNumber": 900105,
    "emailAddresses": [],
    "primaryGroup": {
      "id": 1009662,
      "createdAt": 1533559253589,
      "updatedAt": 1533559253589,
      "version": 0,
      "name": "mytestcollab",
      "gidNumber": 500593,
      "parents": [],
      "users": null
    },
    "secondaryGroups": [],
    "userStatus": "ACTIVE",
    "externalId": "hdf_ec0c370f-39a6-4c15-a94e-cf56367e2414@unity-hdf"
  }
]
```

## Find user by external id

```
curl --basic -u $USER:$PASS $ENDP/external-user/find/externalId/hdf_61230996-664f-4422-9caa-76cf086f0d6c@unity-hdf
```
### Example output
```
{
  "id": 1007486,
  "createdAt": 1531327592699,
  "updatedAt": 1533732759215,
  "version": 7,
  "attributeStore": {
    "urn:oid:0.9.2342.19200300.100.1.1": "marcus",
    "http://bwidm.de/bwidmOrgId": "hdf"
  },
  "genericStore": {
    "ssh_key": "[{'value': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4vjkJr6H6eXKE9+dj4epCrcSUQRFih1603/SjJKIA3cpWt0O5TC4qJCQwOcvFXdjCu0Y1YUKrUlmV0D9fezbqNrSEZ30gT5YLhawUT6LukMTKfNLxa5wM7jzAlmhJ4obadTE5G5qpAGz5SbgHRfPdTlctpqmmFeyN/Rw4lgzoJ8+zHFyp2VPB7rCaUdsS+48lkVhYtlIDBogdRLAZp8MpSeHZFjHfpq+XDhHXdKnEtETV2+IQfMxRBj6Bpw7wwWpIkSQuf4VDHTAhb6+KjcBg/TBc46CekKzF6gtKImZZNVIzEXuAW2prHmQRh72+oQFMqhVcnRmDOWGwBEvXzT0R marcus@tuna2013', 'name': 'unity_key'}]"
  },
  "eppn": "Hardt@unity-hdf",
  "email": "no@email.provided",
  "givenName": "Marcus",
  "surName": "Hardt",
  "uidNumber": 900094,
  "emailAddresses": [],
  "primaryGroup": {
    "id": 1002637,
    "createdAt": 1525327969976,
    "updatedAt": 1525327969976,
    "version": 0,
    "name": "hdf-test",
    "gidNumber": 500573,
    "parents": [],
    "users": null
  },
  "secondaryGroups": [],
  "userStatus": "ACTIVE",
  "externalId": "hdf_61230996-664f-4422-9caa-76cf086f0d6c@unity-hdf"
}
```

## Group Management:
In all shortness:

Gibt rudimentäre Infos über die Gruppe aus:
```
https://bwidm-test.scc.kit.edu/rest/group-admin/find/id/<id>
https://bwidm-test.scc.kit.edu/rest/group-admin/find/name/<name>
```


Gibt genauere Infos raus. Z.B. auch die Member und übergeordnete Gruppen:
```
https://bwidm-test.scc.kit.edu/rest/group-admin/find-detail/id/<id>
https://bwidm-test.scc.kit.edu/rest/group-admin/find-detail/name/<name>
```


Legt eine Gruppe an:
```
https://bwidm-test.scc.kit.edu/rest/group-admin/create/<ssn>/<name>
```

<ssn> - Der Service Short Name, des Dienstes, dem die Gruppe zugeordnet ist.

Fügt ein Benutzer einer Gruppe dazu, oder nimmt ihn raus:
```
https://bwidm-test.scc.kit.edu/rest/group-admin/add/groupId/<groupId>/userId/<userId>
https://bwidm-test.scc.kit.edu/rest/group-admin/add/groupId/<groupId>/userId/<userId>
```
<userId> - Datenbank Id des Benutzers
<groupId> - Datenbank Id der Gruppe


# LDAP Configuration
```
BindDN: uid=fileservice-read,ou=admin,ou=login-test,dc=bwidm-test,dc=de
BindPW: $PASS
Base: ou=login-test,dc=bwidm-test,dc=de
```
# Feudal systemd service

To enable a feudal service this might be helpful:
```
systemctl --user --now enable feudalClient@0
```
