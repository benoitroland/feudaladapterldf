# tox -c tox.ini -e report-bonsai-[info,debug]
import pytest
import os, re
import logging
from unittest.mock import MagicMock, patch
from ldf_adapter.backend.bonsai_ldap import BonsaiLDAPClient, User, Group, LDAPEntry
from ldf_adapter.backend.bonsai_ldap import Mode
from ldf_adapter.results import Rejection, Failure
from tests.bonsai.bonsai_magic import UserInfo, bonsai_magic, entry_error, entry_exception, wait
from tests.bonsai.bonsai_data import USER_INFO_ALICE, USER_INFO_TOM
from tests.bonsai.bonsai_data import LDAP_USER, LDAP_USER_NOT_MAPPED, LDAP_USER_NO_PRIMARY_GROUP
from tests.bonsai.bonsai_data import LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM, LDAP_GROUP_BIO
from tests.bonsai.bonsai_data import LDIF_ALICE, LDIF_ALICE_PRE_CREATED
from tests.bonsai.bonsai_data import LDIF_PUNCH, LDIF_CHEM_ADD, LDIF_EARTH_DELETE, LDIF_PUNCH_DELETE
from bonsai import TimeoutError, LDAPError

logger = logging.getLogger(__name__)

# test user exist
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info, user_exist", [(USER_INFO_ALICE, True), (USER_INFO_TOM, False)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_user_exist(bonsai_magic, mode, user_info, user_exist):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert user.exists() == user_exist

    wait()

# test create user - read only
@pytest.mark.parametrize("mode", ["read_only"])
@pytest.mark.parametrize("user_info, user_exist", [(USER_INFO_ALICE, True), (USER_INFO_TOM, False)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_create_user_read_only(bonsai_magic, mode, user_info, user_exist):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.READ_ONLY
    assert user.exists() == user_exist

    with pytest.raises(Rejection) as exc_info:
        user.create()
    assert "Please contact your administrator" in exc_info.value.message

    wait()

# test create user - pre created
@pytest.mark.parametrize("mode", ["pre_created"])
@pytest.mark.parametrize("user_info, user_exist", [(USER_INFO_ALICE, True), (USER_INFO_TOM, False)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_create_user_pre_created(bonsai_magic, mode, user_info, user_exist):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.PRE_CREATED
    assert user.exists() == user_exist

    if user_exist:
        user.create()

    else:
        with pytest.raises(Rejection):
            user.create()

    wait()

# test create user - full access
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_TOM])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_create_user_full_access(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.FULL_ACCESS

    assert not user.exists()
    user.create()

    wait()

# test get_username
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_get_username(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert user.get_username() == "alice.hertzog"

    wait()

# test get_primary_group
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_get_primary_group(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert user.get_primary_group() == "punch4nfdi"

    wait()

# test name_taken - existing user
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_name_taken_existing_user(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert not user.name_taken("alice.hertzog")

    wait()

# test name_taken - non existing user
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[]])
@pytest.mark.parametrize("ldap_group_entry", [[]])
def test_name_taken_non_existing_user(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert not user.name_taken("alice.hertzog")

    wait()

# test name_taken - another user
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_TOM])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_name_taken_another_user(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert not user.name_taken("tom.sawyer")
    assert user.name_taken("alice.hertzog")

    wait()

# test name_taken - pre created - not mapped
@pytest.mark.parametrize("mode", ["pre_created"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER_NOT_MAPPED]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_name_taken_pre_created_not_mapped(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert not user.name_taken("alice.hertzog")

    wait()

# test alice belongs to groups
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM, LDAP_GROUP_BIO)])
def test_alice_belongs_to_groups(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert set(user.get_groups()) == set(["punch4nfdi","nfdi4earth"])

    wait()

# test tom belongs to groups
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_TOM])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM, LDAP_GROUP_BIO)])
def test_tom_belongs_to_groups(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert set(user.get_groups()) == set(["nfdi4chem","nfdi4biodiversity"])

    wait()


# test delete user - non full access
@pytest.mark.parametrize("mode", ["read_only","pre_created"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_delete_user_non_full_access(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert user.exists()

    with pytest.raises(Rejection):
        user.delete()

    wait()

# test delete user - full access
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_delete_user_full_access(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert user.exists()

    user.delete()

    wait()

# test update user - non full access
@pytest.mark.parametrize("mode", ["read_only","pre_created"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_update_user_non_full_access(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)
    assert user.exists()

    user.update()

    wait()

# test update user - full access - non existing user
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_TOM])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_update_user_full_access_non_existing_user(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    assert not user.exists()
    user.update()

    wait()

# test update user - full access
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_update_user_full_access(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    assert user.exists()
    user.update()

    attributes = user.get_ldap_entry()
    userinfo = (UserInfo(user_info))
    assert attributes.get("sn") == userinfo.get("family_name")
    assert attributes.get("givenName") == userinfo.get("given_name")
    assert attributes.get("cn") == userinfo.get("full_name")
    assert attributes.get("mail") == userinfo.get("email")

    wait()

# test group exist
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name, group_exist", [("punch4nfdi", True), ("banana4nfdi", False)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_group_exist(bonsai_magic, mode, user_info, group_name, group_exist):

    group = Group(group_name)
    assert group.ldap_client.mode == Mode.from_str(mode)
    assert group.exists() == group_exist

    wait()

# test create group - non full access
@pytest.mark.parametrize("mode", ["read_only","pre_created"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name", ["punch4nfdi"])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH],[]])
def test_create_group_non_full_access(bonsai_magic, mode, user_info, group_name, ldap_group_entry):

    group = Group(group_name)
    assert group.ldap_client.mode == Mode.from_str(mode)

    assert group.exists() == bool(len(ldap_group_entry))
    group.create()

    wait()

# test create group - full access
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name", ["punch4nfdi"])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry, group_exist", [([LDAP_GROUP_PUNCH], True), ([LDAP_GROUP_EARTH], False)])
def test_create_group_full_access(bonsai_magic, mode, user_info, group_name, group_exist):

    group = Group(group_name)
    assert group.ldap_client.mode == Mode.from_str(mode)

    assert group.exists() == group_exist
    group.create()

    wait()

# test modify user - read_only
@pytest.mark.parametrize("mode", ["read_only"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("supplementary_group_names",
                         [ ["punch4nfdi", "nfdi4earth"],
                           ["punch4nfdi", "nfdi4earth", "nfdi4chem"],
                           ["punch4nfdi", "nfdi4earth", "nfdi4biodiversity"],
                           ["punch4nfdi", "nfdi4earth", "nfdi4chem", "nfdi4biodiversity"],
                           ["nfdi4earth"],
                           ["punch4nfdi"],
                           [],
                           None,
                           ["punch4nfdi", "nfdi4chem"],
                           ["punch4nfdi", "nfdi4earth", "banana4nfdi"]
                         ])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM, LDAP_GROUP_BIO)])
def test_modify_user_read_only(bonsai_magic, mode, user_info, supplementary_group_names):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    supplementary_groups = []
    if supplementary_group_names is not None:
        for name in supplementary_group_names:
            supplementary_groups.append(Group(name))
    else:
        supplementary_groups = None

    added, removed = user.mod(supplementary_groups)
    assert added == []
    assert removed == []

    wait()

# test modify user - pre_created
@pytest.mark.parametrize("mode", ["pre_created"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("supplementary_group_names, group_added, group_removed",
                         [ (["punch4nfdi", "nfdi4earth"], [], []), # nothing to do
                           (["punch4nfdi", "nfdi4earth", "nfdi4chem"], ["nfdi4chem"], []), # added to nfdi4chem
                           (["punch4nfdi", "nfdi4earth", "nfdi4biodiversity"], ["nfdi4biodiversity"], []), # added to nfdi4biodiversity
                           (["punch4nfdi", "nfdi4earth", "nfdi4chem", "nfdi4biodiversity"], ["nfdi4chem","nfdi4biodiversity"], []), # added to nfdi4biodiversity and nfdi4chem
                           (["nfdi4earth"], [], ["punch4nfdi"]), # removed from punch4nfdi
                           (["punch4nfdi"], [], ["nfdi4earth"]), # removed from nfdi4earth
                           ([], [], ["punch4nfdi","nfdi4earth"]), # removed from punch4nfdi and nfdi4earth
                           (None, [], ["punch4nfdi","nfdi4earth"]), # removed from punch4nfdi and nfdi4earth
                           (["punch4nfdi", "nfdi4chem"], ["nfdi4chem"], ["nfdi4earth"]), # added to nfdi4chem and removed from nfdi4earth
                           (["punch4nfdi", "nfdi4earth", "banana4nfdi"],  [], []) # can not be added to non-existing group
                         ])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM, LDAP_GROUP_BIO)])
def test_modify_user_pre_created(bonsai_magic, mode, user_info, supplementary_group_names, group_added, group_removed):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    supplementary_groups = []
    if supplementary_group_names is not None:
        for name in supplementary_group_names:
            supplementary_groups.append(Group(name))
    else:
        supplementary_groups = None

    added, removed = user.mod(supplementary_groups)
    assert set(added) == set(group_added)
    assert set(removed) == set(group_removed)

    wait()

# test modify user - full_access
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("supplementary_group_names, group_added, group_removed",
                         [ (["punch4nfdi", "nfdi4earth"], [], []), # nothing to do
                           (["punch4nfdi", "nfdi4earth", "nfdi4chem"], ["nfdi4chem"], []), # added to nfdi4chem
                           (["punch4nfdi", "nfdi4earth", "nfdi4biodiversity"], ["nfdi4biodiversity"], []), # added to nfdi4biodiversity
                           (["punch4nfdi", "nfdi4earth", "nfdi4chem", "nfdi4biodiversity"], ["nfdi4chem","nfdi4biodiversity"], []), # added to nfdi4biodiversity and nfdi4chem
                           (["nfdi4earth"], [], ["punch4nfdi"]), # removed from punch4nfdi
                           (["punch4nfdi"], [], ["nfdi4earth"]), # removed from nfdi4earth
                           ([], [], ["punch4nfdi","nfdi4earth"]), # removed from punch4nfdi and nfdi4earth
                           (None, [], ["punch4nfdi","nfdi4earth"]), # removed from punch4nfdi and nfdi4earth
                           (["punch4nfdi", "nfdi4chem"], ["nfdi4chem"], ["nfdi4earth"]), # added to nfdi4chem and removed from nfdi4earth
                           (["punch4nfdi", "nfdi4earth", "banana4nfdi"],  ["banana4nfdi"], []) # added to non-existing group
                         ])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM, LDAP_GROUP_BIO)])
def test_modify_user_full_access(bonsai_magic, mode, user_info, supplementary_group_names, group_added, group_removed):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    supplementary_groups = []
    if supplementary_group_names is not None:
        for name in supplementary_group_names:
            supplementary_groups.append(Group(name))
    else:
        supplementary_groups = None

    added, removed = user.mod(supplementary_groups)
    assert set(added) == set(group_added)
    assert set(removed) == set(group_removed)

    wait()

# test user membership
@pytest.mark.parametrize("mode", ["read_only","pre_created","full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("supplementary_group_names", [["punch4nfdi","nfdi4earth","nfdi4chem"]])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM)])
def test_user_membership(bonsai_magic, mode, user_info, supplementary_group_names):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    supplementary_groups = []
    for name in supplementary_group_names:
        supplementary_groups.append(Group(name))

    logger.info(f"Supplementary groups: {supplementary_group_names}")

    for group in supplementary_groups:
        assert group.ldap_client.mode == Mode.from_str(mode)
        members = group.get_ldap_entry().get("memberUid") or []
        assert user_info["username"] in members

    wait()

# test client nextuid
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("uid_min, uid_max", [(1000, 2000), (800, 2000)])
@pytest.mark.parametrize("gid_min, gid_max", [(1000, 2000)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_nextuid(bonsai_magic, mode, user_info, uid_min, uid_max, gid_min, gid_max):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    assert user.ldap_client.get_next_uid() == uid_min + 2
    assert user.ldap_client.get_next_uid() == uid_min + 3
    assert user.ldap_client.get_next_uid() == uid_min + 4

    wait()

# test client nextgid
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("uid_min, uid_max", [(1000, 2000)])
@pytest.mark.parametrize("gid_min, gid_max", [(1000, 2000), (800, 2000)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_nextgid(bonsai_magic, mode, user_info, uid_min, uid_max, gid_min, gid_max):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    assert user.ldap_client.get_next_gid() == gid_min + 2
    assert user.ldap_client.get_next_gid() == gid_min + 3
    assert user.ldap_client.get_next_gid() == gid_min + 4

    wait()

# test client nextuid all taken
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("uid_min, uid_max", [(1000, 2000)])
@pytest.mark.parametrize("gid_min, gid_max", [(1000, 2000)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_nextuid_all_taken(bonsai_magic, monkeypatch, mode, user_info, uid_min, uid_max, gid_min, gid_max):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    with monkeypatch.context() as mp:
        mp.setattr(user.ldap_client, "is_uid_taken", lambda *x: True)
        with pytest.raises(Failure):
            user.ldap_client.get_next_uid()

    wait()

# test client nextgid all taken
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("uid_min, uid_max", [(1000, 2000)])
@pytest.mark.parametrize("gid_min, gid_max", [(800, 3000)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_nextgid_all_taken(bonsai_magic, monkeypatch, mode, user_info, uid_min, uid_max, gid_min, gid_max):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    with monkeypatch.context() as mp:
        mp.setattr(user.ldap_client, "is_gid_taken", lambda *x: True)
        with pytest.raises(Failure):
            user.ldap_client.get_next_gid()

    wait()

# test client nextuid out of range
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("uid_min, uid_max", [(1000, 1000)])
@pytest.mark.parametrize("gid_min, gid_max", [(1000, 1000)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_nextuid_out_of_range(bonsai_magic, mode, user_info, uid_min, uid_max, gid_min, gid_max):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    with pytest.raises(Failure):
        user.ldap_client.get_next_uid()

    wait()

# test client nextgid out of range
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("uid_min, uid_max", [(1000, 1000)])
@pytest.mark.parametrize("gid_min, gid_max", [(1000, 1000)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_nextgid_out_of_range(bonsai_magic, mode, user_info, uid_min, uid_max, gid_min, gid_max):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    with pytest.raises(Failure):
        user.ldap_client.get_next_gid()

    wait()

# test client nextuid bad range
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("uid_min, uid_max", [(800, 400)])
@pytest.mark.parametrize("gid_min, gid_max", [(800, 400)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_nextuid_bad_range(bonsai_magic, mode, user_info, uid_min, uid_max, gid_min, gid_max):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    with pytest.raises(Failure):
        user.ldap_client.get_next_uid()

    wait()

# test client nextgid bad range
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("uid_min, uid_max", [(800, 400)])
@pytest.mark.parametrize("gid_min, gid_max", [(800, 400)])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_nextgid_bad_range(bonsai_magic, mode, user_info, uid_min, uid_max, gid_min, gid_max):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    with pytest.raises(Failure):
        user.ldap_client.get_next_gid()

    wait()

# test create user ldif
@pytest.mark.parametrize("mode, expected_ldif", [("read_only", LDIF_ALICE), ("pre_created", LDIF_ALICE_PRE_CREATED), ("full_access",LDIF_ALICE)])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_create_user_ldif(bonsai_magic, mode, expected_ldif, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    ldif_result = user.create_tostring()
    assert ldif_result == expected_ldif

    wait()

# test create group ldif
@pytest.mark.parametrize("mode, expected_ldif", [("read_only", LDIF_PUNCH), ("pre_created", LDIF_PUNCH), ("full_access", LDIF_PUNCH)])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name", ["punch4nfdi"])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_create_group_ldif(bonsai_magic, mode, expected_ldif, user_info, group_name):

    group = Group(group_name)
    assert group.ldap_client.mode == Mode.from_str(mode)

    ldif_result = group.create_tostring()
    assert ldif_result == expected_ldif

    wait()

# test modify user ldif
@pytest.mark.parametrize("mode", ["read_only", "pre_created", "full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("supplementary_group_names, expected_ldif",
                          [(["punch4nfdi","nfdi4earth"], ""), # nothing to do
                           (["punch4nfdi","nfdi4earth","nfdi4chem"], LDIF_CHEM_ADD), # added to nfdi4chem
                           (["punch4nfdi"], LDIF_EARTH_DELETE), # removed from nfdi4earth
                          ])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM)])
def test_modify_user_ldif(bonsai_magic, mode, user_info, supplementary_group_names, expected_ldif):
    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    supplementary_groups = []
    for name in supplementary_group_names:
        supplementary_groups.append(Group(name))

    ldif_result = user.mod_tostring(supplementary_groups)
    assert ldif_result == expected_ldif

    wait()

# test remove user from group ldif
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("expected_ldif", [LDIF_PUNCH_DELETE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_remove_user_from_group_ldif(bonsai_magic, mode, user_info, expected_ldif):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    ldif_result = user.ldap_client.remove_user_from_group_ldif(user.name, "punch4nfdi")
    assert ldif_result == expected_ldif

    wait()

# test add user ldif
@pytest.mark.parametrize("mode", ["read_only", "pre_created", "full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("expected_ldif", [LDIF_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_add_user_ldif(bonsai_magic, mode, user_info, expected_ldif):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.from_str(mode)

    ldif_result = user.ldap_client.add_user_ldif(UserInfo(user_info), user.name, "punch4nfdi")
    assert ldif_result == expected_ldif

    wait()

# test add group ldif
@pytest.mark.parametrize("mode", ["read_only", "pre_created", "full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name", ["punch4nfdi"])
@pytest.mark.parametrize("expected_ldif", [LDIF_PUNCH])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_add_group_ldif(bonsai_magic, mode, user_info, group_name, expected_ldif):

    group = Group(group_name)
    assert group.ldap_client.mode == Mode.from_str(mode)

    ldif_result = group.ldap_client.add_group_ldif(group_name)
    assert ldif_result == expected_ldif

    wait()

# test wrong access mode
@pytest.mark.parametrize("mode", ["banana"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_wrong_access_mode(bonsai_magic, mode, user_info):

    logger.info("\n\n" + "=" * 30 + " Test wrong access mode " + "=" * 30 + "\n")

    with pytest.raises(Failure) as exc_info:
         user = User(UserInfo(user_info))
    assert f"Unknown mode '{mode}'." in exc_info.value.message

    wait()

# test connection timeout
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_connection_timeout(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.FULL_ACCESS

    logger.info("\n\n" + "=" * 30 + " Test connection timeout " + "=" * 30 + "\n")

    user.ldap_client.pool.idle_connection = 0
    connection = bonsai_magic["connection"]

    with patch.object(connection, "whoami", side_effect=TimeoutError("Connection Timeout")):
        with pytest.raises(Failure) as exc_info:
            user.exists()
    assert "Attempt to spawn a connection failed" in exc_info.value.message

    wait()

# test client - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_client_fail(bonsai_magic, mode, user_info):

    logger.info("\n\n" + "=" * 30 + " Test client failure " + "=" * 30 + "\n")

    connection = bonsai_magic["connection"]

    with patch.object(connection, "search", side_effect = Exception("Error adding entries.")):
        with pytest.raises(Failure) as exc_info:
            user = User(UserInfo(user_info))
    assert exc_info.value.message == f"Failed to add entries in LDAP when tracking available UID and GID values"

    wait()

# test create user - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_TOM])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_create_user_fail(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.FULL_ACCESS
    connection = bonsai_magic["connection"]

    logger.info("\n\n" + "=" * 30 + " Test create user failure " + "=" * 30 + "\n")

    with patch.object(connection, "add", side_effect = Exception("LDAP backend failure.")):
        with pytest.raises(Failure) as exc_info:
            user.create()
    assert exc_info.value.message == f"Failed to add an entry for the user {user.name}"

    wait()

# test delete user - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_delete_user_fail(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    assert user.ldap_client.mode == Mode.FULL_ACCESS
    connection = bonsai_magic["connection"]

    logger.info("\n\n" + "=" * 30 + " Test delete user failure " + "=" * 30 + "\n")

    with patch.object(connection, "delete", side_effect = Exception("LDAP backend failure.")):
        with pytest.raises(Failure) as exc_info:
            user.delete()
    assert exc_info.value.message == f"Failed to delete the LDAP entry for the user {user.name}"

    wait()

# test map user - fail
@pytest.mark.parametrize("mode", ["pre_created"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_map_user_fail(bonsai_magic, mode, user_info):

    entry = bonsai_magic["entry"]

    logger.info("\n\n" + "=" * 30 + " Test map user failure " + "=" * 30 + "\n")

    with patch.object(entry, "side_effect", entry_error):
        with pytest.raises(Failure) as exc_info:
            user = User(UserInfo(user_info))
            assert user.ldap_client.mode == Mode.PRE_CREATED
            user.create()
    assert exc_info.value.message == f"Failed to modify the LDAP entry for the user {user.name}"

    wait()

# test modify user - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize(("supplementary_group_names","group_name"),
                         [ (["punch4nfdi","nfdi4earth", "nfdi4chem"], "nfdi4chem") ])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH, LDAP_GROUP_CHEM)])
def test_modify_user_fail(bonsai_magic, mode, user_info, supplementary_group_names, group_name):

    entry = bonsai_magic["entry"]

    supplementary_groups = []
    for name in supplementary_group_names:
        supplementary_groups.append(Group(name))

    logger.info("\n\n" + "=" * 30 + " Test modify user failure " + "=" * 30 + "\n")

    with patch.object(entry, "side_effect", entry_exception):
        with pytest.raises(Failure) as exc_info:
            user = User(UserInfo(user_info))
            assert user.ldap_client.mode == Mode.FULL_ACCESS
            user.mod(supplementary_groups)
    assert exc_info.value.message == f"Failed to modify the LDAP entry for the user {user.name} and the group {group_name}"

    wait()

# test update user - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_update_user_fail(bonsai_magic, mode, user_info):

    entry = bonsai_magic["entry"]

    logger.info("\n\n" + "=" * 30 + " Test update user failure " + "=" * 30 + "\n")

    with patch.object(entry, "side_effect", entry_error):
        with pytest.raises(Failure) as exc_info:
            user = User(UserInfo(user_info))
            assert user.ldap_client.mode == Mode.FULL_ACCESS
            user.ldap_client.update_user(UserInfo(user_info), user.name)
    assert exc_info.value.message == f"Failed to modify the entry for user {user.name}"

    wait()

# test remove user from group - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [(LDAP_GROUP_PUNCH, LDAP_GROUP_EARTH)])
def test_remove_user_from_group_fail(bonsai_magic, mode, user_info):

    entry = bonsai_magic["entry"]

    logger.info("\n\n" + "=" * 30 + " Test remove user from group failure " + "=" * 30 + "\n")

    with patch.object(entry, "side_effect", entry_exception):
        with pytest.raises(Failure) as exc_info:
            user = User(UserInfo(user_info))
            assert user.ldap_client.mode == Mode.from_str(mode)
            user.ldap_client.remove_user_from_group("alice.hertzog", "punch4nfdi")
    assert exc_info.value.message == f"Failed to modify the LDAP entry for user alice.hertzog and group punch4nfdi"

    wait()

# test create group - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name", ["punch4nfdi"])
@pytest.mark.parametrize("create_group_fail", [True])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_EARTH]])
def test_create_group_fail(bonsai_magic, mode, user_info, group_name, create_group_fail):

    group = Group(group_name)
    assert group.ldap_client.mode == Mode.FULL_ACCESS
    connection = bonsai_magic["connection"]

    logger.info("\n\n" + "=" * 30 + " Test create group failure " + "=" * 30 + "\n")

    with patch.object(connection, "add", side_effect = Exception("LDAP backend failure.")):
        with pytest.raises(Failure) as exc_info:
            group.create()
    assert exc_info.value.message == f"Failed to add an LDAP entry for the group {group_name}"

    wait()

# test next uid - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_next_uid_fail(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))
    connection = bonsai_magic["connection"]

    logger.info("\n\n" + "=" * 30 + " Test next uid failure " + "=" * 30 + "\n")

    with patch.object(connection, "search", return_value=False):
        with pytest.raises(Failure) as exc_info:
            user.ldap_client.get_next_uid()

    assert exc_info.value.message == f"No UID found in LDAP search."

    wait()

# test next gid - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name", ["punch4nfdi"])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_next_gid_fail(bonsai_magic, mode, user_info, group_name):

    user = User(UserInfo(user_info))
    group = Group(group_name)
    connection = bonsai_magic["connection"]

    logger.info("\n\n" + "=" * 30 + " Test next gid failure " + "=" * 30 + "\n")

    with patch.object(connection, "search", return_value=False):
        with pytest.raises(Failure) as exc_info:
            group.ldap_client.get_next_gid()

    assert exc_info.value.message == f"No GID found in LDAP search."

    wait()

# test group not found
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name", ["punch4nfdi"])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_group_not_found(bonsai_magic, mode, user_info, group_name):

    user = User(UserInfo(user_info))
    group = Group(group_name)
    connection = bonsai_magic["connection"]

    logger.info("\n\n" + "=" * 30 + " Test group not found " + "=" * 30 + "\n")

    with patch.object(connection, "search", return_value=False):
        assert group.ldap_client.get_user_groups(user.name) == []

    wait()

# test missing primary group
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER_NO_PRIMARY_GROUP]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_missing_primary_group(bonsai_magic, mode, user_info):

    logger.info("\n\n" + "=" * 30 + " Test missing primary group " + "=" * 30 + "\n")

    with pytest.raises(Failure) as exc_info:
        user = User(UserInfo(user_info))

    assert exc_info.value.message == f"Primary group is missing for user {user_info.get('username')}."

    wait()

# test ldif - fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_ldif_fail(bonsai_magic, mode, user_info):

    user = User(UserInfo(user_info))

    class Banana:
        def __str__(self):
            raise Exception("banana")

    user.ldap_client.attr_oidc_uid = Banana()

    logger.info("\n\n" + "=" * 30 + " Test LDIF failure " + "=" * 30 + "\n")

    with pytest.raises(Failure) as exc_info:
        user.ldap_client.map_user_ldif(UserInfo(user_info), "alice.hertzog")

    assert exc_info.value.message == f"Failed to get LDIF to modify the entry for user {user.name} with uid {user.unique_id}"

    wait

# test ldap entry fail
@pytest.mark.parametrize("mode", ["full_access"])
@pytest.mark.parametrize("user_info", [USER_INFO_ALICE])
@pytest.mark.parametrize("group_name", ["punch4nfdi"])
@pytest.mark.parametrize("ldap_user_entry", [[LDAP_USER]])
@pytest.mark.parametrize("ldap_group_entry", [[LDAP_GROUP_PUNCH]])
def test_ldap_entry_fail(bonsai_magic, mode, user_info, group_name):

    user = User(UserInfo(user_info))
    group = Group(group_name)
    connection = bonsai_magic["connection"]

    logger.info("\n\n" + "=" * 30 + " Test ldap user entry failure " + "=" * 30 + "\n")

    with patch.object(connection, "search", return_value=False):
        with pytest.raises(Failure) as exc_info:
            user.get_ldap_entry()

    assert exc_info.value.message == f"User with unique_id {user.unique_id} not found."

    wait()

    logger.info("\n\n" + "=" * 30 + " Test ldap group entry failure " + "=" * 30 + "\n")

    with patch.object(connection, "search", return_value=False):
        with pytest.raises(Failure) as exc_info:
            group.get_ldap_entry()

    assert exc_info.value.message == f"Group with name {group_name} not found."

    wait()

