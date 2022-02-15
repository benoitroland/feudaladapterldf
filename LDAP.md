# LDAP Backend
- local accounts are managed in an LDAP
- the mappings between federated and local accounts are also stored in the LDAP
    - each user entry has an attribute containing a unique id derived from the OIDC information
    - the attribute is configurable
- the LDAP must support the following schemas: inetOrgPerson, posixAccount, posixGroup

## Use cases
The following use cases are supported with the LDAP backend:

1. **Read-only** access to the LDAP
    - local user management is fully controlled by LDAP admins, including mapping
    - the LDAP backend only retrieves the local user information from the LDAP
    - Requirements:
        - the local accounts need to exist in the LDAP
        - the local accounts need to already be mapped to the federated accounts
        - if mapping of VOs to local groups is supported, the local groups also need to exist
            - the group names need to be derived from the VO names
            - the groups need to already contain the users as members
    
2. **Pre-created** users in the LDAP
    - local user management by local admins, mapping management by FEUDAL
    - the LDAP backend is responsible for mapping existing accounts to federated accounts and adding users to any existing local groups
    - ideally with *pooled* username generation
    - Requirements:
        - write access to LDAP s.t. attribute containing mapping can be modified
        - the local accounts need to exist in the LDAP
        - if mapping of VOs to local groups is supported, the local groups also need to exist

3. **Full-access** to LDAP
    - local user management fully controlled by FEUDAL, including mapping and uids
    - Requirements:
        - write access to LDAP s.t. new user and group entries can be added (and modified)
        - support for [nextuidgid schema](#nextuidgid-schema) in LDAP, for managing available POSIX UIDs and GIDs

## Backend configuration
The LDAP backend is configured in the main config file, in the section **\[backend.ldap\]**. See [feudal_adapter_template.conf](feudal_adapter_template.conf) for examples.

### Modes

First, the mode in which the FEUDAL adapter is run must be configured. There are three modes available, corresponding to the three use cases above:
- read_only
- pre_created
- full_access

Example:
```
[backend.ldap]
mode = read_only
```

### Authentication

Next, the host and port where one can connect to the LDAP can be configured. Example with default values:

```
host = localhost
port = 1389
```

The LDAP backend supports two types of authentication to the LDAP:
- simple authentication: by the means of a username (in a dn form) and a password
- anonymous bind: no username and password required

For example, simple authentication can be configured like so:
```
admin_user = cn=admin,dc=example
admin_password = adminpassword
```

When not specified, anonymous bind is used.

SASL authentication is not supported yet.

### Namespaces

LDAP directories have a hierarchical tree structure, representing the hierarchy of organisational units within an organisation, with users and groups stored in the tree leaves. The subtrees that can be managed by FEUDAL can be configured via `user_base` and `group_base`, e.g.:  

```
user_base = ou=users,dc=example
group_base = ou=groups,dc=example
```

These "namespaces" can include any number of ou/o/dc entries separated by commas. They are used when searching in LDAP (as a search base), but also when adding new users or groups (as a suffix in the fully qualified DN of a user/group).

### Mapping attributes

The mapping between local and federated accounts is stored in the LDAP: each user entry has two attributes, one containing the local username, and the other containing a unique ID derived from the OIDC information. These attributes can be configured as follows:

```
attribute_oidc_uid = gecos
attribute_local_uid = uid
```

### Additional configurations

These configurations are only used by the **full-access** mode, when creating new users or groups.

You can configure additional fields that relate to POSIX users, such as `shell` or `home_base` (the base directory for home directories), e.g.:

```
shell = /bin/sh
home_base = /home
```

POSIX UIDs and GIDs assigned to newly created users and groups can be limited to certain ranges, e.g.:

```
uid_min = 2000
uid_max = 3000
gid_min = 2000
gid_max = 3000
```

## LDAP configuration

By design, FEUDAL aims to change local user management policies as little as possible. This is enabled by the flexible backend configuration explained in the previous section. Nevertheless, some adjustments might be required to the LDAP.

### nextuidgid schema

In **full-access** mode, the LDAP needs to support the **nextuidgid** schema, which allows tracking of available UID and GID values for POSIX users and groups. The schema is specified below in LDIF format and must be added to the LDAP:

```ldif
# extended LDIF
# LDAPv3

dn: cn=debops,cn=schema,cn=config
objectClass: olcSchemaConfig
cn: debops
olcObjectIdentifier: {0}DebOps 1.3.6.1.4.1.53622
olcObjectIdentifier: {1}DebOpsLDAP DebOps:42

dn: cn=nextuidgid,cn=schema,cn=config
objectClass: olcSchemaConfig
cn: nextuidgid
olcObjectIdentifier: {0}nextUidGid DebOpsLDAP:3
olcObjectIdentifier: {1}nextUidGidObject nextUidGid:1
olcObjectClasses: {0}( nextUidGidObject:1 NAME 'uidNext' DESC 'LDAP object whi
 ch tracks the next available UID number' SUP top STRUCTURAL MUST ( cn $ uidNu
 mber ) MAY description )
olcObjectClasses: {1}( nextUidGidObject:2 NAME 'gidNext' DESC 'LDAP object whi
 ch tracks the next available GID number' SUP top STRUCTURAL MUST ( cn $ gidNu
 mber ) MAY description )
```

### LDAP entries examples

The **read_only** and **pre_created** modes require the LDAP admin to create the local accounts (and groups) in advance. Even more, in **read_only** mode, the LDAP entries need to contain the mapping information to the federated user.

For example, let's consider a federated EGI user with the following OIDC userinfo (only relevant fields shown):
```json
{
    ...
    "eduperson_entitlement": [
        "urn:mace:egi.eu:group:eosc-synergy.eu:role=member#aai.egi.eu",
        "urn:mace:egi.eu:group:eosc-synergy.eu:role=vm_operator#aai.egi.eu",
        "urn:mace:egi.eu:group:mteam.data.kit.edu:role=vm_operator#aai.egi.eu",
        "urn:mace:egi.eu:group:mteam.data.kit.edu:role=member#aai.egi.eu"
    ],
    "eduperson_unique_id": "c2370093c19496aeb46103cce3ccdc7b183f54ac9ba9c859dea94dfba23aacd5@egi.eu",
    "email": "diana.gudu@kit.edu",
    "family_name": "Gudu",
    "given_name": "Diana",
    "name": "Diana Gudu",
    "preferred_username": "dgudu",
    "sub": "c2370093c19496aeb46103cce3ccdc7b183f54ac9ba9c859dea94dfba23aacd5@egi.eu",
    ...
}
```

Below, examples for the entries that need to be created in the LDAP:

1. In **pre-created** mode, a user entry for the `preferred_username`, as well as some group entries:
    ```ldif
    dn: uid=dgudu,ou=users,dc=egi,dc=eu
    objectClass: top
    objectClass: inetOrgPerson
    objectClass: posixAccount
    uid: dgudu
    sn: dgudu
    cn: dgudu
    loginShell: /bin/bash
    uidNumber: 1000
    gidNumber: 1000
    homeDirectory: /home/dgudu

    dn: cn=egi-eu_mteam-data-kit-edu,ou=groups,dc=egi,dc=eu
    objectClass: top
    objectClass: posixGroup
    cn: egi-eu_mteam-data-kit-edu
    gidNumber: 1000

    dn: cn=egi-eu_eosc-synergy-eu,ou=groups,dc=egi,dc=eu
    objectClass: top
    objectClass: posixGroup
    cn: egi-eu_eosc-synergy-eu
    gidNumber: 1001
    ```
2. In **read-only** mode, the mapping also needs to be added to the user entry, and the user needs to be added to the groups:
    ```ldif
    dn: uid=dgudu,ou=users,dc=egi,dc=eu
    objectClass: top
    objectClass: inetOrgPerson
    objectClass: posixAccount
    uid: dgudu
    sn: dgudu
    cn: dgudu
    loginShell: /bin/bash
    uidNumber: 1000
    gidNumber: 1000
    homeDirectory: /home/dgudu
    gecos: c2370093c19496aeb46103cce3ccdc7b183f54ac9ba9c859dea94dfba23aacd5%40egi.eu@https%3A%2F%2Faai.egi.eu%2Foidc%2F

    dn: cn=egi-eu_mteam-data-kit-edu,ou=groups,dc=egi,dc=eu
    objectClass: top
    objectClass: posixGroup
    cn: egi-eu_mteam-data-kit-edu
    gidNumber: 1000
    memberUid: dgudu

    dn: cn=egi-eu_eosc-synergy-eu,ou=groups,dc=egi,dc=eu
    objectClass: top
    objectClass: posixGroup
    cn: egi-eu_eosc-synergy-eu
    gidNumber: 1001
    memberUid: dgudu
    ```
