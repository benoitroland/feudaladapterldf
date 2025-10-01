USER_INFO_ALICE = {
    "unique_id": "subuid@issuer.domain",
    "username": "alice.hertzog",
    "given_name": "alice",
    "family_name": "hertzog",
    "full_name": "alice hertzog",
    "email": "alice.hertzog@kit.edu",
    "primary_group": "punch4nfdi",
    "ssh_keys": {}
}

USER_INFO_TOM = {
    "unique_id": "another_uid@issuer.domain",
    "username": "tom.sawyer",
    "given_name": "tom",
    "family_name": "sawyer",
    "full_name": "tom sawyer",
    "email": "tom.sawyer@kit.edu",
    "primary_group": "punch4nfdi",
    "ssh_keys": {}
}

LDAP_USER = {
    "dn": "uid=alice.hertzog,ou=users,ou=punch4nfdi,dc=fels,dc=de",
    "objectClass": ["top", "inetOrgPerson", "posixAccount"],
    "uidNumber": 1000,
    "gidNumber": 1000,
    "homeDirectory": "/home/alice.hertzog",
    "loginShell": "/bin/sh",
    "uid": "alice.hertzog",
    "name": "alice.hertzog",
    "gecos": "subuid@issuer.domain",
    "givenName": "alice",
    "sn": "hertzog",
    "cn": "alice hertzog",
    "mail": "alice.hertzog@kit.edu"
}

LDAP_USER_NOT_MAPPED = {
    "dn": "uid=alice.hertzog,ou=users,ou=punch4nfdi,dc=fels,dc=de",
    "objectClass": ["top", "inetOrgPerson", "posixAccount"],
    "uidNumber": 1000,
    "gidNumber": 1000,
    "homeDirectory": "/home/alice.hertzog",
    "loginShell": "/bin/sh",
    "uid": "alice.hertzog",
    "name": "alice.hertzog",

    "givenName": "alice",
    "sn": "hertzog",
    "cn": "alice hertzog",
    "mail": "alice.hertzog@kit.edu"
}

LDAP_USER_NO_PRIMARY_GROUP = {
    "dn": "uid=alice.hertzog,ou=users,ou=punch4nfdi,dc=fels,dc=de",
    "objectClass": ["top", "inetOrgPerson", "posixAccount"],
    "uidNumber": 1000,
    "gidNumber": 1006,
    "homeDirectory": "/home/alice.hertzog",
    "loginShell": "/bin/sh",
    "uid": "alice.hertzog",
    "name": "alice.hertzog",
    "gecos": "subuid@issuer.domain",
    "givenName": "alice",
    "sn": "hertzog",
    "cn": "alice hertzog",
    "mail": "alice.hertzog@kit.edu"
}

LDAP_GROUP_PUNCH = {
    "dn": "cn=punch4nfdi,ou=groups,ou=punch4nfdi,dc=fels,dc=de",
    "cn": "punch4nfdi",
    "objectClass": ["posixGroup"],
    "gidNumber": 1000,
    "memberUid": ["alice.hertzog"]
}

LDAP_GROUP_EARTH = {
    "dn": "cn=nfdi4earth,ou=groups,ou=nfdi4earth,dc=fels,dc=de",
    "cn": "nfdi4earth",
    "objectClass": ["posixGroup"],
    "gidNumber": 1001,
    "memberUid": ["alice.hertzog"]
}

LDAP_GROUP_CHEM = {
    "dn": "cn=nfdi4chem,ou=groups,ou=nfdi4chem,dc=fels,dc=de",
    "cn": "nfdi4chem",
    "objectClass": ["posixGroup"],
    "gidNumber": 1002,
    "memberUid": ["tom.sawyer"]
}

LDAP_GROUP_BIO = {
    "dn": "cn=nfdi4biodiversity,ou=groups,ou=nfdi4biodiversity,dc=fels,dc=de",
    "cn": "nfdi4biodiversity",
    "objectClass": ["posixGroup"],
    "gidNumber": 1003,
    "memberUid": ["tom.sawyer"]
}

LDIF_ALICE = "dn: uid=alice.hertzog,ou=users,ou=punch4nfdi,dc=fels,dc=de"

LDIF_ALICE_PRE_CREATED = """dn: uid=alice.hertzog,ou=users,ou=punch4nfdi,dc=fels,dc=de
changetype: modify
replace: gecos
gecos: subuid@issuer.domain"""

LDIF_PUNCH = "dn: cn=punch4nfdi,ou=groups,ou=punch4nfdi,dc=fels,dc=de"

LDIF_CHEM_ADD = """dn: cn=nfdi4chem,ou=groups,ou=punch4nfdi,dc=fels,dc=de
changetype: modify
add: memberUid
memberUid: alice.hertzog"""

LDIF_EARTH_DELETE = """dn: cn=nfdi4earth,ou=groups,ou=punch4nfdi,dc=fels,dc=de
changetype: modify
delete: memberUid
memberUid: alice.hertzog"""

LDIF_PUNCH_DELETE = """dn: cn=punch4nfdi,ou=groups,ou=punch4nfdi,dc=fels,dc=de
changetype: modify
delete: memberUid
memberUid: alice.hertzog"""
