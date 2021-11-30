import pytest
import regex
import random
from pathlib import Path

from ldf_adapter.backend.local_unix import make_shadow_compatible
from ldf_adapter.results import Failure


INPUT_UNIX = {
    "new_root": f"/tmp/newroot{random.randint(1000, 9999)}",
    "userinfo": {
        "unique_id": "subuid@issuer.domain",
        "primary_group": "testgroup",
        "username": "testuser",
        "ssh_keys": {}
    },
    "passwd_entry": "testuser:x:1000:1000:subuid@issuer.domain:/home/testuser:/bin/bash",
    "passwd_taken": "testuser:x:2000:2000:::",
    "group_entry": "testgroup:x:1000:",
}


@pytest.mark.parametrize('input,exists,taken', [(INPUT_UNIX, False, False)])
def test_create(local_unix_user, input):
    """Test that create method adds the appropriate entry in /etc/passwd.
    """
    local_unix_user.create()
    assert input["passwd_entry"] in (Path(input["new_root"])/"etc"/"passwd").read_text()


@pytest.mark.parametrize('input,exists,taken', [(INPUT_UNIX, False, True)])
def test_create_taken(local_unix_user, input):
    """Test that create raises a Failure if the username is already taken.
    User's primary group needs to exist.
    """
    with pytest.raises(Failure):
        local_unix_user.create()


@pytest.mark.parametrize('input,exists,taken', [
        (INPUT_UNIX, False, False),
        (INPUT_UNIX, False, True)
    ])
def test_doesnt_exist(local_unix_user):
    """Tests that exists returns False on a clean system, or even if username is taken by another user.
    (i.e. username exists, but the gecos field does not contain this user's unique_id)."""
    assert not local_unix_user.exists()


@pytest.mark.parametrize('input,exists,taken', [(INPUT_UNIX, True, False)])
def test_exists(local_unix_user, input):
    """Tests that exists returns True if there is an entry in passwd for this unique_id."""
    assert local_unix_user.exists()


@pytest.mark.parametrize('input,exists,taken', [(INPUT_UNIX, False, True)])
def test_name_taken(local_unix_user, input):
    """Tests that name_taken returns True if the username exists on the system but is not
    mapped to this user's unique_id (via gecos field).
    """
    assert local_unix_user.name_taken(input["userinfo"]["username"])


@pytest.mark.parametrize('input,exists,taken', [(INPUT_UNIX, True, False)])
def test_name_taken_byme(local_unix_user, input):
    """Tests that name_taken returns False if the username exists on the system and is
    mapped to this user's unique_id (via gecos field).
    """
    assert not local_unix_user.name_taken(input["userinfo"]["username"])


@pytest.mark.parametrize('input,exists,taken', [(INPUT_UNIX, True, False)])
def test_get_username_same(local_unix_user, input):
    """Tests that get_username returns the username in passwd.
    Case 1: username in userinfo is the same as the one in passwd.
    """
    assert local_unix_user.get_username() == "testuser"


@pytest.mark.parametrize('input,exists,taken', [(INPUT_UNIX, False, False)])
def test_get_username_different(local_unix_user, input):
    """Tests that get_username returns the username in passwd.
    Case 2: username in userinfo is different than the one in passwd.
    """
    passwd_mapped = "testuser2:x:1000:1000:subuid@issuer.domain:/home/testuser:/bin/bash"
    (Path(input["new_root"])/"etc"/"passwd").write_text(passwd_mapped)
    assert local_unix_user.get_username() == "testuser2"


@pytest.mark.parametrize('input,exists,taken', [
        (INPUT_UNIX, False, False),
        (INPUT_UNIX, False, True)
    ])
def test_get_username_none(local_unix_user, input):
    """Tests that get_username returns None if there is no username mapped to the
    user's unique_id, even when the username in userinfo is already taken.
    """
    assert local_unix_user.get_username() == None


@pytest.mark.parametrize('input,exists,taken', [(INPUT_UNIX, True, False)])
def test_delete(local_unix_user, input):
    """Test that after delete, there is no user with the username in the db,
    or any other user mapped to the unique_id."""
    local_unix_user.delete()
    passwd_content = (Path(input["new_root"])/"etc"/"passwd").read_text()
    assert input["userinfo"]["unique_id"] not in passwd_content
    assert input["userinfo"]["username"] not in passwd_content


@pytest.mark.parametrize('input,exists,taken', [
        (INPUT_UNIX, False, False),
        (INPUT_UNIX, False, True)
    ])
def test_delete_doesnt_exist(local_unix_user, input, taken):
    """Test that delete raises a Failure if the user is not in the db,
    even if its username is taken by another user."""
    with pytest.raises(Failure):
        local_unix_user.delete()
    passwd_content = (Path(input["new_root"])/"etc"/"passwd").read_text()
    assert input["userinfo"]["unique_id"] not in passwd_content
    if taken:
        assert input["userinfo"]["username"] in passwd_content


INPUT_UNIX_GROUP = {
    "new_root": f"/tmp/newroot{random.randint(1000, 9999)}",
    "name": "testgroup",
    "group_entry": "testgroup:x:1000:",
}


@pytest.mark.parametrize('input,exists', [(INPUT_UNIX_GROUP, False)])
def test_group_create(local_unix_group, input):
    """Test that create method adds the appropriate entry in /etc/group.
    """
    local_unix_group.create()
    assert input["group_entry"] in (Path(input["new_root"])/"etc"/"group").read_text()


@pytest.mark.parametrize('input,exists', [(INPUT_UNIX_GROUP, True)])
def test_group_create_exists(local_unix_group):
    """Test that create raises a Failure if the group exists.
    """
    with pytest.raises(Failure):
        local_unix_group.create()


@pytest.mark.parametrize('input,exists', [
        (INPUT_UNIX_GROUP, False),
        (INPUT_UNIX_GROUP, True)
    ])
def test_group_exist(local_unix_group, exists):
    """Tests that exists returns True if there is an entry for the given name,
    and False otherwise.
    """
    assert local_unix_group.exists() == exists



INPUT_SHADOW_COMPATIBLE = [
    ("user", "user"),
    ("", "_"),
    ("äöüÄÖÜß!$*@", "aeoeueaeoeuessisx_at_"),
    ("#%^&()=+[]{}\\|;:'\",<.>/?", "________________________"),
    ("u#%^&()=+[]{}\\|;:'\",<.>/?", "u________________________"),
    (u"\u5317\u4EB0", "bei_jing_"),
    (u"\u20AC", "eur"),
    ("user$", "users"),
    ("-user", "_-user"),
    ("-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "_-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("-abcdefaaaaaaaaaaaaaaaaaaaaaaaaaa", "_..defaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("abcdefaaaaaaaaaaaaaaaaaaaaaaaaaaa", "__defaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("helmholtz-de_KIT_Helmholtz-member", "helmholtz-de_.._helmholtz-member")
    # ("a_b_c_d_e_f_a_a_a_a______________", "a_.._d_e_f_a_a_a_a______________"), # ??
    # ("_________________________________", "_.._____________________________"), # ??
]


@pytest.mark.parametrize('raw', [x[0] for x in INPUT_SHADOW_COMPATIBLE])
def test_make_shadow_compatible_length(raw):
    """a shadow-compatible name must be at most 32 characters long
    """
    assert len(make_shadow_compatible(raw)) <= 32


@pytest.mark.parametrize('raw', [x[0] for x in INPUT_SHADOW_COMPATIBLE])
def test_make_shadow_compatible_allowed_chars(raw):
    """a shadow-compatible name must start with a lowercase letter or underscore
    and can also contain numbers and - in addition to lowercase letters and _
    """
    word = make_shadow_compatible(raw)
    assert regex.match(r'[a-z_]', word[0]) and regex.match(r'[-0-9_a-z]', word)


@pytest.mark.parametrize('raw,cooked', INPUT_SHADOW_COMPATIBLE)
def test_make_shadow_compatible(raw, cooked):
    """expected behaviour:
    - german umlauts are replaced with their phonetic equivalents
    - a few special characters are replaced by sensible equivalents:
        - ! to i
        - $ to s
        - * to x
        - @ to _at_
    - unicode characters are decoded to ascii
    - all other special characters are replaced with _
    - what about shortening? TODO: define expected behaviour
    """
    assert make_shadow_compatible(raw) == cooked
