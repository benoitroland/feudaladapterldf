import pytest
import logging
import ldap3
import sys

from ..settings import MockUserInfo
from ldf_adapter.results import Rejection, Failure


logger = logging.getLogger(__name__)


original_init = ldap3.Connection.__init__


def mock_ldap3_connection_init(self, *args, **kwargs):
    if kwargs.get("client_strategy") is ldap3.SAFE_SYNC:
        kwargs["client_strategy"] = ldap3.MOCK_SYNC
    if kwargs.get("auto_bind"):
        del kwargs["auto_bind"]
    original_init(self, *args, **kwargs)
    self.bind()


@pytest.fixture(scope="function")
def ldap_user(mode, userinfo, existing_entries, monkeypatch):
    """Creates a backend user from provided dict data.
    'userinfo' should contain: unique_id, username, primary_group.
    'existing_entries' are LDAP entries to be added beforehand;
        each entry contains a dn and a dict of attributes.
    """
    with monkeypatch.context() as mp:
        mp.setattr("ldap3.Connection.__init__", mock_ldap3_connection_init)
        mp.setattr("ldf_adapter.backend.ldap.CONFIG.backend.ldap.mode", mode)

        import ldf_adapter.backend.ldap

        service_user = ldf_adapter.backend.ldap.User(MockUserInfo(userinfo))
        for entry in existing_entries:
            ldf_adapter.backend.ldap.LDAP.connection.add(
                entry["dn"], object_class=entry["object_class"], attributes=entry["attributes"]
            )
        yield service_user
        # module needs to be reloaded on next test so that LDAP object is recreated
        del sys.modules["ldf_adapter.backend.ldap"]


@pytest.fixture(scope="function")
def ldap_group(mode, name, existing_entries, monkeypatch):
    """Creates a backend group from provided data.
    name: the group name (no constraints on allowed names)
    'existing_entries' are LDAP entries to be added beforehand;
        each entry contains a dn and a dict of attributes.
    """
    with monkeypatch.context() as mp:
        mp.setattr("ldap3.Connection.__init__", mock_ldap3_connection_init)
        mp.setattr("ldf_adapter.backend.ldap.CONFIG.backend.ldap.mode", mode)

        import ldf_adapter.backend.ldap

        service_group = ldf_adapter.backend.ldap.Group(name)
        for entry in existing_entries:
            ldf_adapter.backend.ldap.LDAP.connection.add(
                entry["dn"], object_class=entry["object_class"], attributes=entry["attributes"]
            )
        yield service_group
        del sys.modules["ldf_adapter.backend.ldap"]


@pytest.fixture(scope="function")
def ldap_mod_entry(mode, userinfo, supplementary_group_names, existing_entries, monkeypatch):
    """Creates a backend user and groups from provided data.
    'userinfo' should contain: unique_id, username, primary_group.
    'supplementary_group_names' is a list of group names
    'existing_entries' are LDAP entries to be added beforehand;
        each entry contains a dn and a dict of attributes.
    """
    with monkeypatch.context() as mp:
        mp.setattr("ldap3.Connection.__init__", mock_ldap3_connection_init)
        mp.setattr("ldf_adapter.backend.ldap.CONFIG.backend.ldap.mode", mode)

        import ldf_adapter.backend.ldap

        service_user = ldf_adapter.backend.ldap.User(MockUserInfo(userinfo))
        supplementary_groups = []
        for name in supplementary_group_names:
            supplementary_groups.append(ldf_adapter.backend.ldap.Group(name))
        for entry in existing_entries:
            ldf_adapter.backend.ldap.LDAP.connection.add(
                entry["dn"], object_class=entry["object_class"], attributes=entry["attributes"]
            )
        yield {"user": service_user, "supplementary_groups": supplementary_groups}
        del sys.modules["ldf_adapter.backend.ldap"]


@pytest.fixture(scope="function")
def ldap_connection(uid_min, uid_max, gid_min, gid_max, monkeypatch):
    with monkeypatch.context() as mp:
        mp.setattr("ldap3.Connection.__init__", mock_ldap3_connection_init)
        mp.setattr("ldf_adapter.backend.ldap.CONFIG.backend.ldap.mode", "full_access")
        mp.setattr("ldf_adapter.backend.ldap.CONFIG.backend.ldap.uid_min", uid_min)
        mp.setattr("ldf_adapter.backend.ldap.CONFIG.backend.ldap.uid_max", uid_max)
        mp.setattr("ldf_adapter.backend.ldap.CONFIG.backend.ldap.gid_min", gid_min)
        mp.setattr("ldf_adapter.backend.ldap.CONFIG.backend.ldap.gid_max", gid_max)
        import ldf_adapter.backend.ldap

        yield ldf_adapter.backend.ldap.LDAP
        del sys.modules["ldf_adapter.backend.ldap"]


USERINFO = {
    "unique_id": "subuid@issuer.domain",
    "primary_group": "testgroup",
    "username": "testuser",
    "ssh_keys": {},
}

USERINFO_BIG = {
    "unique_id": "subuid@issuer.domain",
    "primary_group": "testgroup",
    "username": "testuser",
    "ssh_keys": {},
    "family_name": "family_name",
    "given_name": "given_name",
    "full_name": "full_name",
    "email": "email@domain",
}

LDAP_USER_ENTRY = {
    "dn": "uid=testuser,ou=users,dc=example",
    "object_class": ["top", "inetOrgPerson", "posixAccount"],
    "attributes": {
        "uid": "testuser",
        "uidNumber": 1000,
        "gidNumber": 1000,
        "homeDirectory": "/home/testuser",
        "loginShell": "/bin/sh",
        "gecos": "subuid@issuer.domain",
        "username": "testuser",
    },
}

LDAP_USER2_ENTRY = {
    "dn": "uid=testuser,ou=users,dc=example",
    "object_class": ["top", "inetOrgPerson", "posixAccount"],
    "attributes": {
        "uid": "testuser",
        "uidNumber": 1000,
        "gidNumber": 1000,
        "homeDirectory": "/home/testuser",
        "loginShell": "/bin/sh",
        "gecos": "another_uid@issuer.domain",
        "username": "testuser",
    },
}

LDAP_TESTGROUP_ENTRY = {
    "dn": "cn=testgroup,ou=groups,dc=example",
    "object_class": ["posixGroup"],
    "attributes": {"cn": "testgroup", "gidNumber": 1000, "memberUid": ["testuser"]},
}

LDAP_TESTGROUP2_ENTRY = {
    "dn": "cn=testgroup2,ou=groups,dc=example",
    "object_class": ["posixGroup"],
    "attributes": {"cn": "testgroup2", "gidNumber": 1001, "memberUid": ["testuser"]},
}

LDAP_GROUP1_ENTRY = {
    "dn": "cn=group1,ou=groups,dc=example",
    "object_class": ["posixGroup"],
    "attributes": {
        "cn": "group1",
        "gidNumber": 1002,
    },
}

LDAP_GROUP2_ENTRY = {
    "dn": "cn=group2,ou=groups,dc=example",
    "object_class": ["posixGroup"],
    "attributes": {
        "cn": "group2",
        "gidNumber": 1003,
    },
}

LDAP_PRECREATED_USER_ENTRY = {
    "dn": "uid=testuser,ou=users,dc=example",
    "object_class": ["top", "inetOrgPerson", "posixAccount"],
    "attributes": {
        "uid": "testuser",
        "uidNumber": 1000,
        "gidNumber": 1000,
        "homeDirectory": "/home/testuser",
        "loginShell": "/bin/sh",
        "username": "testuser",
    },
}

LDAP_PRECREATED_TESTGROUP_ENTRY = {
    "dn": "cn=testgroup,ou=groups,dc=example",
    "object_class": ["posixGroup"],
    "attributes": {
        "cn": "testgroup",
        "gidNumber": 1000,
    },
}


@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize("mode", ["read_only"])
@pytest.mark.parametrize("existing_entries", [[], [LDAP_USER_ENTRY]])
def test_create_user_read_only_fail(ldap_user, existing_entries):
    """In read_only mode, create always fails, even if user exists."""
    assert ldap_user.exists() == (len(existing_entries) > 0)
    with pytest.raises(Rejection):
        ldap_user.create()


@pytest.mark.parametrize(
    "mode,userinfo,existing_entries",
    [
        ("pre_created", USERINFO, []),
    ],
)
def test_create_user_precreated_doesnt_exist(ldap_user):
    """In pre_created mode, create fails if entry for username does not exist."""
    assert not ldap_user.exists()
    with pytest.raises(Rejection):
        ldap_user.create()


@pytest.mark.parametrize(
    "mode,userinfo,existing_entries",
    [
        ("pre_created", USERINFO, [LDAP_PRECREATED_USER_ENTRY, LDAP_PRECREATED_TESTGROUP_ENTRY]),
    ],
)
def test_create_user_precreated_exists(ldap_user):
    """In pre_created mode, create succeeds if entry for username exists by mapping entry to unique_id.
    Will not check if entry already mapped to something else, since ldf_adapter user checks if
    user exists or if name_taken beforehand.
    """
    assert not ldap_user.exists()
    ldap_user.create()
    assert ldap_user.exists()


@pytest.mark.parametrize(
    "mode,userinfo,existing_entries",
    [
        ("full_access", USERINFO, []),
    ],
)
def test_create_user_full_access_group_doesnt_exist(ldap_user):
    """primary group must exist, otherwise create fails."""
    assert not ldap_user.exists()
    with pytest.raises(Failure):
        ldap_user.create()


@pytest.mark.parametrize(
    "mode,userinfo,existing_entries",
    [
        ("full_access", USERINFO, [LDAP_PRECREATED_TESTGROUP_ENTRY]),
    ],
)
def test_create_user_full_access_success(ldap_user):
    assert not ldap_user.exists()
    ldap_user.create()
    assert ldap_user.exists()


@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize("mode", ["read_only", "pre_created", "full_access"])
@pytest.mark.parametrize(
    "existing_entries,username",
    [
        ([], None),
        ([LDAP_USER_ENTRY], "testuser"),
    ],
)
def test_create_user_get_username(ldap_user, username):
    assert ldap_user.get_username() == username


@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize("mode", ["read_only", "pre_created", "full_access"])
@pytest.mark.parametrize(
    "existing_entries,groupname",
    [
        ([], None),
        ([LDAP_USER_ENTRY], None),
        ([LDAP_USER_ENTRY, LDAP_PRECREATED_TESTGROUP_ENTRY], "testgroup"),
        ([LDAP_USER_ENTRY, LDAP_TESTGROUP_ENTRY], "testgroup"),
    ],
)
def test_get_primary_group(ldap_user, groupname):
    assert ldap_user.get_primary_group() == groupname


@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize("mode", ["read_only", "pre_created", "full_access"])
@pytest.mark.parametrize("existing_entries", [[]])
def test_name_taken_no_existing_entries(ldap_user):
    assert not ldap_user.name_taken("testuser")


@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize("mode", ["read_only", "pre_created", "full_access"])
@pytest.mark.parametrize("existing_entries", [[LDAP_USER_ENTRY]])
def test_name_taken_by_user(ldap_user):
    assert not ldap_user.name_taken("testuser")


@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize("mode", ["read_only", "pre_created", "full_access"])
@pytest.mark.parametrize("existing_entries", [[LDAP_USER2_ENTRY]])
def test_name_taken_by_another(ldap_user):
    assert ldap_user.name_taken("testuser")


@pytest.mark.parametrize(
    "mode,userinfo,existing_entries",
    [
        ("pre_created", USERINFO, [LDAP_PRECREATED_USER_ENTRY]),
    ],
)
def test_name_taken_precreated_not_mapped(ldap_user):
    assert not ldap_user.name_taken("testuser")


@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize("mode", ["read_only"])
@pytest.mark.parametrize(
    "existing_entries,groups",
    [
        ([], []),
        ([LDAP_USER_ENTRY], []),
        ([LDAP_USER_ENTRY, LDAP_PRECREATED_TESTGROUP_ENTRY], []),
        ([LDAP_USER_ENTRY, LDAP_TESTGROUP_ENTRY], ["testgroup"]),
        (
            [LDAP_USER_ENTRY, LDAP_TESTGROUP_ENTRY, LDAP_TESTGROUP2_ENTRY],
            ["testgroup", "testgroup2"],
        ),
    ],
)
def test_get_groups(ldap_user, groups):
    assert set(ldap_user.get_groups()) == set(groups)


@pytest.mark.parametrize(
    "mode,userinfo,existing_entries",
    [
        ("full_access", USERINFO, []),
        ("full_access", USERINFO, [LDAP_USER_ENTRY]),
    ],
)
def test_delete_user_sucecss(ldap_user, existing_entries):
    """works no matter if user exists or not"""
    assert ldap_user.exists() == bool(len(existing_entries))
    ldap_user.delete()
    assert not ldap_user.exists()


@pytest.mark.parametrize("mode", ["read_only", "pre_created"])
@pytest.mark.parametrize(
    "userinfo,existing_entries",
    [
        (USERINFO, [LDAP_USER_ENTRY]),
        (USERINFO, []),
    ],
)
def test_delete_user_rejected(ldap_user):
    """rejected no matter if user exists or not"""
    with pytest.raises(Rejection):
        ldap_user.delete()


@pytest.mark.parametrize("mode", ["read_only", "pre_created"])
@pytest.mark.parametrize(
    "userinfo,existing_entries",
    [
        (USERINFO, [LDAP_USER_ENTRY]),
        (USERINFO, []),
    ],
)
def test_update_user_ignored(ldap_user, existing_entries):
    """in read-only and per-created mode, nothing happens."""
    assert ldap_user.exists() == bool(len(existing_entries))
    ldap_user.update()
    assert ldap_user.exists() == bool(len(existing_entries))


@pytest.mark.parametrize(
    "mode,userinfo,existing_entries",
    [
        ("full_access", USERINFO, []),
    ],
)
def test_update_full_access_doesnt_exist(ldap_user):
    assert not ldap_user.exists()
    ldap_user.update()
    assert not ldap_user.exists()


@pytest.mark.parametrize(
    "mode,userinfo,existing_entries",
    [
        ("full_access", USERINFO, [LDAP_USER_ENTRY]),
        ("full_access", USERINFO_BIG, [LDAP_USER_ENTRY]),
    ],
)
def test_update_full_access_new_attribute(ldap_user, userinfo):
    assert ldap_user.exists()
    ldap_user.update()
    assert ldap_user.exists()
    attributes = ldap_user.get_ldap_entry()
    assert attributes.get("sn") == userinfo.get("family_name")
    assert attributes.get("givenName") == userinfo.get("given_name")
    assert attributes.get("cn") == userinfo.get("full_name")
    assert attributes.get("mail") == userinfo.get("email")


@pytest.mark.parametrize("mode", ["read_only", "pre_created"])
@pytest.mark.parametrize("name", ["testgroup"])
@pytest.mark.parametrize(
    "existing_entries",
    [
        [LDAP_TESTGROUP_ENTRY],
        [],
    ],
)
def test_create_group_ignore(ldap_group, existing_entries):
    assert ldap_group.exists() == bool(len(existing_entries))
    ldap_group.create()
    assert ldap_group.exists() == bool(len(existing_entries))


@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("name", ["testgroup"])
@pytest.mark.parametrize(
    "existing_entries",
    [
        [LDAP_TESTGROUP_ENTRY],
        [],
    ],
)
def test_create_group_success(ldap_group, existing_entries):
    assert ldap_group.exists() == bool(len(existing_entries))
    ldap_group.create()
    assert ldap_group.exists()


@pytest.mark.parametrize("mode", ["read_only", "pre_created"])
@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize(
    "existing_entries",
    [
        [LDAP_USER_ENTRY],
        [],
    ],
)
@pytest.mark.parametrize("supplementary_group_names", [[], ["group1", "group2"]])
def test_mod_user_ignore(ldap_mod_entry):
    """nothing happens"""
    added, removed = ldap_mod_entry["user"].mod(ldap_mod_entry["supplementary_groups"])
    assert added == []
    assert removed == []


@pytest.mark.parametrize("mode", ["pre_created", "full_access"])
@pytest.mark.parametrize("userinfo", [USERINFO])
@pytest.mark.parametrize(
    "existing_entries,removed_from",
    [
        ([LDAP_TESTGROUP_ENTRY, LDAP_GROUP1_ENTRY, LDAP_GROUP2_ENTRY], ["testgroup"]),
        (
            [LDAP_USER_ENTRY, LDAP_TESTGROUP_ENTRY, LDAP_GROUP1_ENTRY, LDAP_GROUP2_ENTRY],
            ["testgroup"],
        ),
        (
            [
                LDAP_USER_ENTRY,
                LDAP_PRECREATED_TESTGROUP_ENTRY,
                LDAP_GROUP1_ENTRY,
                LDAP_GROUP2_ENTRY,
            ],
            [],
        ),
    ],
)
@pytest.mark.parametrize("supplementary_group_names", [["group1", "group2"], []])
def test_mod_user_success(ldap_mod_entry, userinfo, removed_from):
    added, removed = ldap_mod_entry["user"].mod(ldap_mod_entry["supplementary_groups"])

    assert set(added) == set([grp.name for grp in ldap_mod_entry["supplementary_groups"]])
    assert set(removed) == set(removed_from)

    for group in ldap_mod_entry["supplementary_groups"]:
        members = group.get_ldap_entry().get("memberUid") or []
        assert userinfo["username"] in members
        assert userinfo["username"] in members


@pytest.mark.parametrize("uid_min,uid_max", [(1000, 2000), (2000, 3000)])
@pytest.mark.parametrize("gid_min,gid_max", [(1000, 2000)])
def test_connection_nextuid(ldap_connection, uid_min):
    assert ldap_connection.get_next_uid() == uid_min
    assert ldap_connection.get_next_uid() == uid_min + 1
    assert ldap_connection.get_next_uid() == uid_min + 2


@pytest.mark.parametrize("uid_min,uid_max", [(1000, 2000)])
@pytest.mark.parametrize("gid_min,gid_max", [(1000, 2000), (2333, 3121)])
def test_connection_nextgid(ldap_connection, gid_min):
    assert ldap_connection.get_next_gid() == gid_min
    assert ldap_connection.get_next_gid() == gid_min + 1
    assert ldap_connection.get_next_gid() == gid_min + 2


@pytest.mark.parametrize("uid_min,uid_max", [(1000, 2000)])
@pytest.mark.parametrize("gid_min,gid_max", [(1000, 2000)])
def test_connection_nextuid_all_taken(ldap_connection, monkeypatch):
    with monkeypatch.context() as mp:
        mp.setattr(ldap_connection, "is_uid_taken", lambda *x: True)
        with pytest.raises(Failure):
            ldap_connection.get_next_uid()


@pytest.mark.parametrize("uid_min,uid_max", [(1000, 2000)])
@pytest.mark.parametrize("gid_min,gid_max", [(1000, 2000)])
def test_connection_nextgid_all_taken(ldap_connection, monkeypatch):
    with monkeypatch.context() as mp:
        mp.setattr(ldap_connection, "is_gid_taken", lambda *x: True)
        with pytest.raises(Failure):
            ldap_connection.get_next_gid()


@pytest.mark.parametrize("uid_min,uid_max", [(1000, 1000)])
@pytest.mark.parametrize("gid_min,gid_max", [(1000, 1000)])
def test_connection_nextuid_out_of_range(ldap_connection):
    ldap_connection.get_next_uid()
    with pytest.raises(Failure):
        ldap_connection.get_next_uid()


@pytest.mark.parametrize("uid_min,uid_max", [(1000, 1000)])
@pytest.mark.parametrize("gid_min,gid_max", [(1000, 1000)])
def test_connection_nextgid_out_of_range(ldap_connection):
    ldap_connection.get_next_gid()
    with pytest.raises(Failure):
        ldap_connection.get_next_gid()


@pytest.mark.parametrize("uid_min,uid_max", [(2000, 1000)])
@pytest.mark.parametrize("gid_min,gid_max", [(2000, 1000)])
def test_connection_nextuid_bad_range(ldap_connection):
    with pytest.raises(Failure):
        ldap_connection.get_next_uid()


@pytest.mark.parametrize("uid_min,uid_max", [(2000, 1000)])
@pytest.mark.parametrize("gid_min,gid_max", [(2000, 1000)])
def test_connection_nextgid_bad_range(ldap_connection):
    with pytest.raises(Failure):
        ldap_connection.get_next_gid()
