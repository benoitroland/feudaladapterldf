# FEUDAL Client Adapter


# **NOTE: THIS BRANCH INCLUDES THE "EXISTING USERNAME WINS APPROACH" THAT STILL NEEDS TO BE TESTED**

This code implements the adapter for FEUDAL to communicate with various services, called "backends".

Distributed with the adapter are backends for [BWIDM](ldf_adapter/backend/bwidm.py) and [UNIX](ldf_adapter/backend/local_unix.py).

## Usage
### Installation
- Install [feudalClient](https://git.scc.kit.edu/feudal/feudalClient)
- Build package: `./setup.py sdist`
- Install package: `pip install dist/ldf_adapter-$version.tar.gz`
- Edit the FEUDAL Client config file (e.g. `~/.config/feudal/client.json`) to include:
   ```js
   {
       "services": {
           "suppe": {
               "name": "Der ADAPTER",
               "description": "Er ist sehr gut",
               "command": "ldf_adapter"
           }
       },
   }
   ```

### Configuration
See [config.py:reload](ldf_adapter/config.py) for a list of config file locations.

The config file contains both the generic config, as well as for specific backends.

An example config file explaining the options can be found in [ldf_adapter.conf](ldf_adapter.conf)

### Running
Lastly, simply start the FEUDAL client:

```sh
feudalClient -c ~/.config/feudal/client.json
```

### Further help
If you encounter problem, you can find information about the behaviour of the adapter and the backends in the rather verbose inline doc. Just take a look at the inline doc. The [ldf_adapter Module](ldf_adapter/__init__.py) is probably a good starting point, or the [backend Module](ldf_adapter/backend).

## Development
For Documentation, just take a look at the inline doc.

To get started, run `pip install -r devel-requirements.txt` (you probably want to do this inside a virtualenv).

Then, set the command of the service in feudalClients `client.json` to the full path to [interface.py](interface.py) inside your cloned repo.

For debugging, run the feudalClient with:

```sh
LOG=DEBUG feudalClient -c ~/.config/feudal/client.json --debug-scripts
```

### Backends
Backends are simply python modules. There is an [example backend](ldf_adapter/backend/example.py) explaining what the module needs to implement.
To create a new backend named `my_backend`:

```sh
cd ldf_adapter/backend
cp example.py my_backend.py
```

And fill out the methods in the classes in `my_backend.py` (don't rename the classes!).

Then, you can activate the module using

```conf
[ldf_adapter]
backend = my_backend

[ldf_adapter.my_backend]
foo = bar
# Configuration for your backend goes here

[ldf_adapter.my_backend.login_info]
login_host = example.org
login_help = To login, ask your mama for help.
# Here goes a bunch of arbitrary static information to be included in the credentials section
# in the feudalClient webinterface
```

in [ldf_adapter.conf](ldf_adapter.conf).

### Unit Tests
There are unit tests, located under [tests](tests) (The package structure in `tests` corresponds to
that of the main package). To run the tests, just do:

```sh
./setup.py test
```


# LDF REST Interface
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
