import pytest
import regex
import random
from pathlib import Path
import subprocess
import os
import logging

import ldf_adapter.backend.local_unix
from ldf_adapter.results import Failure
from ..settings import MockUserInfo

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def local_unix_user(input, exists, taken, monkeypatch):
    """Creates a backend user from provided dict data.
    input should contain:
        - userinfo, which should contain: unique_id, username, primary_group and ssh_keys.
        - new_root: the folder relative to which the user and group dbs will be stored
        - home_base (optional): the base directory for users' home directories
    If exists, it also adds an entry to the user database in /etc/passwd
    Otherwise, if taken, it adds an entry in the user db for this user's username
    """
    # save original subprocess.run for calling inside the mocked one
    old_subprocess_run = subprocess.run

    def mock_root():
        return input["new_root"]

    def mock_subprocess_run(*args, **kwargs):
        """patches calls to system utilities:
        - only for: useradd, userdel, usermod, chage
        - add prefix argument to command
        - patch pkill to do nothing
        - lett all other system calls go through
        """
        logger.debug(args)
        command = args[0]
        if command[0] in ["useradd", "userdel", "usermod", "chage"]:
            new_command = [command[0], "--prefix", mock_root()] + command[1:]
        elif command[0] == "/usr/bin/pkill":
            return None
        else:
            new_command = command
        return old_subprocess_run(new_command, *args[1:], **kwargs)

    with monkeypatch.context() as mp:
        # patch root used by local_unix.User and subprocess.run to use this root for creating users
        mp.setattr("subprocess.run", mock_subprocess_run)
        mp.setattr("ldf_adapter.backend.local_unix.CONFIG.backend.local_unix.shell", "/bin/bash")
        mp.setattr("ldf_adapter.backend.local_unix.User.ROOT", mock_root)
        mp.setattr("ldf_adapter.backend.local_unix.Group.ROOT", mock_root)
        if input.get("home_base"):
            mp.setattr(
                "ldf_adapter.backend.local_unix.CONFIG.backend.local_unix.home_base",
                input["home_base"].rstrip("/"),
            )
        # init root and necessary files in new root directory (/etc/{passwd,group,shadow})
        os.makedirs(mock_root())
        os.makedirs(Path(mock_root()) / "etc")
        (Path(mock_root()) / "etc" / "passwd").touch()
        (Path(mock_root()) / "etc" / "group").touch()
        (Path(mock_root()) / "etc" / "shadow").touch()
        if exists:
            (Path(mock_root()) / "etc" / "passwd").write_text(input["passwd_entry"])
        elif taken:
            (Path(mock_root()) / "etc" / "passwd").write_text(input["passwd_taken"])
        (Path(mock_root()) / "etc" / "group").write_text(input["group_entry"])
        # init service user from unix backend
        service_user = ldf_adapter.backend.local_unix.User(MockUserInfo(input["userinfo"]))
        yield service_user
        # clean up files
        old_subprocess_run(["rm", "-rf", mock_root()])


@pytest.fixture(scope="function")
def local_unix_group(input, exists, monkeypatch):
    """Creates a backend user from provided dict data.
    input should contain:
        - name: the group name (no constraints on allowed names)
        - new_root: the folder relative to which the user and group dbs will be stored
    If exists=True, also adds an entry to the group database in /etc/group
    """
    # save original subprocess.run for calling inside the mocked one
    old_subprocess_run = subprocess.run

    def mock_root():
        return input["new_root"]

    def mock_subprocess_run(*args, **kwargs):
        """patches calls to system utilities:
        - only for: groupadd
        - add prefix argument to command
        - lett all other system calls go through
        """
        logger.debug(args)
        command = args[0]
        if command[0] in ["groupadd"]:
            new_command = [command[0], "--prefix", mock_root()] + command[1:]
        else:
            new_command = command
        return old_subprocess_run(new_command, *args[1:], **kwargs)

    with monkeypatch.context() as mp:
        # patch root used by local_unix.Group and subprocess.run to use this root for creating groups
        mp.setattr("subprocess.run", mock_subprocess_run)
        mp.setattr("ldf_adapter.backend.local_unix.Group.ROOT", mock_root)
        if input.get("home_base"):
            mp.setattr(
                "ldf_adapter.backend.local_unix.CONFIG.backend.local_unix.home_base",
                input["home_base"].rstrip("/"),
            )
        if input.get("punch4nfdi"):
            mp.setattr(
                "ldf_adapter.backend.local_unix.CONFIG.backend.local_unix.punch4nfdi",
                input["punch4nfdi"],
            )
        # init root and necessary files in new root directory (/etc/{passwd,group,shadow})
        os.makedirs(mock_root())
        os.makedirs(Path(mock_root()) / "etc")
        (Path(mock_root()) / "etc" / "group").touch()

        if exists:
            (Path(mock_root()) / "etc" / "group").write_text(input["group_entry"])

        # init service user from unix backend
        service_group = ldf_adapter.backend.local_unix.Group(input["name"])

        yield service_group

        # clean up files
        old_subprocess_run(["rm", "-rf", mock_root()])


INPUT_UNIX = {
    "new_root": f"/tmp/newroot{random.randint(1000, 9999)}",
    "userinfo": {
        "unique_id": "subuid@issuer.domain",
        "primary_group": "testgroup",
        "username": "testuser",
        "ssh_keys": {},
    },
    "passwd_entry": "testuser:x:1000:1000:subuid@issuer.domain:/home/testuser:/bin/bash",
    "passwd_taken": "testuser:x:2000:2000:::",
    "group_entry": "testgroup:x:1000:",
}

INPUT_CUSTOM_HOME_BASE = {
    "new_root": f"/tmp/newroot{random.randint(1000, 9999)}",
    "userinfo": {
        "unique_id": "subuid@issuer.domain",
        "primary_group": "testgroup",
        "username": "testuser",
        "ssh_keys": {},
    },
    "home_base": "/tmp/custom/home/",
    "passwd_entry": "testuser:x:1000:1000:subuid@issuer.domain:/tmp/custom/home/testuser:/bin/bash",
    "group_entry": "testgroup:x:1000:",
}


@pytest.mark.parametrize("input,exists,taken", [(INPUT_UNIX, False, False)])
def test_create(local_unix_user, input):
    """Test that create method adds the appropriate entry in /etc/passwd."""
    local_unix_user.create()
    assert input["passwd_entry"] in (Path(input["new_root"]) / "etc" / "passwd").read_text()


@pytest.mark.parametrize("input,exists,taken", [(INPUT_UNIX, False, True)])
def test_create_taken(local_unix_user, input):
    """Test that create raises a Failure if the username is already taken.
    User's primary group needs to exist.
    """
    with pytest.raises(Failure):
        local_unix_user.create()


@pytest.mark.parametrize("input,exists,taken", [(INPUT_CUSTOM_HOME_BASE, False, False)])
def test_create_custom_home_base(local_unix_user, input):
    """Test that create method adds the appropriate entry in /etc/passwd with custom home dir"""
    local_unix_user.create()
    assert input["passwd_entry"] in (Path(input["new_root"]) / "etc" / "passwd").read_text()


@pytest.mark.parametrize(
    "input,exists,taken", [(INPUT_UNIX, False, False), (INPUT_UNIX, False, True)]
)
def test_doesnt_exist(local_unix_user):
    """Tests that exists returns False on a clean system, or even if username is taken by another user.
    (i.e. username exists, but the gecos field does not contain this user's unique_id)."""
    assert not local_unix_user.exists()


@pytest.mark.parametrize("input,exists,taken", [(INPUT_UNIX, True, False)])
def test_exists(local_unix_user, input):
    """Tests that exists returns True if there is an entry in passwd for this unique_id."""
    assert local_unix_user.exists()


@pytest.mark.parametrize("input,exists,taken", [(INPUT_UNIX, False, True)])
def test_name_taken(local_unix_user, input):
    """Tests that name_taken returns True if the username exists on the system but is not
    mapped to this user's unique_id (via gecos field).
    """
    assert local_unix_user.name_taken(input["userinfo"]["username"])


@pytest.mark.parametrize("input,exists,taken", [(INPUT_UNIX, True, False)])
def test_name_taken_byme(local_unix_user, input):
    """Tests that name_taken returns False if the username exists on the system and is
    mapped to this user's unique_id (via gecos field).
    """
    assert not local_unix_user.name_taken(input["userinfo"]["username"])


@pytest.mark.parametrize("input,exists,taken", [(INPUT_UNIX, True, False)])
def test_get_username_same(local_unix_user, input):
    """Tests that get_username returns the username in passwd.
    Case 1: username in userinfo is the same as the one in passwd.
    """
    assert local_unix_user.get_username() == "testuser"


@pytest.mark.parametrize("input,exists,taken", [(INPUT_UNIX, False, False)])
def test_get_username_different(local_unix_user, input):
    """Tests that get_username returns the username in passwd.
    Case 2: username in userinfo is different than the one in passwd.
    """
    passwd_mapped = "testuser2:x:1000:1000:subuid@issuer.domain:/home/testuser:/bin/bash"
    (Path(input["new_root"]) / "etc" / "passwd").write_text(passwd_mapped)
    assert local_unix_user.get_username() == "testuser2"


@pytest.mark.parametrize(
    "input,exists,taken", [(INPUT_UNIX, False, False), (INPUT_UNIX, False, True)]
)
def test_get_username_none(local_unix_user, input):
    """Tests that get_username returns None if there is no username mapped to the
    user's unique_id, even when the username in userinfo is already taken.
    """
    assert local_unix_user.get_username() == None


@pytest.mark.parametrize("input,exists,taken", [(INPUT_UNIX, True, False)])
def test_delete(local_unix_user, input):
    """Test that after delete, there is no user with the username in the db,
    or any other user mapped to the unique_id."""
    local_unix_user.delete()
    passwd_content = (Path(input["new_root"]) / "etc" / "passwd").read_text()
    assert input["userinfo"]["unique_id"] not in passwd_content
    assert input["userinfo"]["username"] not in passwd_content


@pytest.mark.parametrize(
    "input,exists,taken", [(INPUT_UNIX, False, False), (INPUT_UNIX, False, True)]
)
def test_delete_doesnt_exist(local_unix_user, input, taken):
    """Test that delete raises a Failure if the user is not in the db,
    even if its username is taken by another user."""
    with pytest.raises(Failure):
        local_unix_user.delete()
    passwd_content = (Path(input["new_root"]) / "etc" / "passwd").read_text()
    assert input["userinfo"]["unique_id"] not in passwd_content
    if taken:
        assert input["userinfo"]["username"] in passwd_content


INPUT_UNIX_GROUP = {
    "new_root": f"/tmp/newroot{random.randint(1000, 9999)}",
    "name": "testgroup",
    "group_entry": "testgroup:x:1000:",
}


@pytest.mark.parametrize("input,exists", [(INPUT_UNIX_GROUP, False)])
def test_group_create(local_unix_group, input):
    """Test that create method adds the appropriate entry in /etc/group."""
    local_unix_group.create()
    assert input["group_entry"] in (Path(input["new_root"]) / "etc" / "group").read_text()


@pytest.mark.parametrize("input,exists", [(INPUT_UNIX_GROUP, True)])
def test_group_create_exists(local_unix_group):
    """Test that create raises a Failure if the group exists."""
    with pytest.raises(Failure):
        local_unix_group.create()


@pytest.mark.parametrize("input,exists", [(INPUT_UNIX_GROUP, False), (INPUT_UNIX_GROUP, True)])
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
    ("\u5317\u4EB0", "bei_jing_"),
    ("\u20AC", "eur"),
    ("user$", "users"),
    ("-user", "_-user"),
    ("-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "_-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("-abcdefaaaaaaaaaaaaaaaaaaaaaaaaaa", "_..defaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("abcdefaaaaaaaaaaaaaaaaaaaaaaaaaaa", "__defaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("helmholtz-de_KIT_Helmholtz-member", "helmholtz-de_.._helmholtz-member"),
    # ("a_b_c_d_e_f_a_a_a_a______________", "a_.._d_e_f_a_a_a_a______________"), # ??
    # ("_________________________________", "_.._____________________________"), # ??
]

INPUT_SHADOW_COMPATIBLE_PUNCH4NFDI = [
    ("dfn-de-nfdi-de-punch_punch4nfdi_punch", "punch4nfdi_punch"),
    ("dfn-de-nfdi-de-punch_punch4nfdi_punch_intra", "punch4nfdi_punch_intra"),
]

INPUT_SHADOW_COMPATIBLE_FAIL = [
    "dfn-de-nfdi-de-punch_punch4nfdi_punch_intra",
    "dfn-de-nfdi-de-punch_punch4nfdi_punch_intra_physics_biology_chemistry",
    "_________________________________",  # all _ => no fragments can be shortened
]

INPUT_SHADOW_COMPATIBLE_V044 = [
    ("user", "user"),  # valid name
    ("", "_"),  # empty name
    (
        "äöüÄÖÜß!$*@",
        "aeoeueaeoeuessisx_at_",
    ),  # umlauts and few other special characters can be replaced
    (
        "#%^&()=+[]{}\\|;:'\",<.>/?",
        "________________________",
    ),  # all other special chars replaced with _, when first char is special
    (
        "u#%^&()=+[]{}\\|;:'\",<.>/?",
        "u________________________",
    ),  # all other special chars replaced with _, when first char is a letter
    ("\u5317\u4EB0", "bei_jing_"),  # unicode
    ("\u20AC", "eur"),  # unicode
    ("user$", "users"),  # $ replaced with s even ar the end (although valid shadow name)
    ("-user", "_user"),  # - as first character replaced with _
    (
        "-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    ),  # - as first character replaced with _
    # from here on, length > 32 needs to be shortened to 32; fragments are defined as substrings separated by _
    (
        "helmholtz-de_KIT_Helmholtz-member",
        "helmholtz.._kit_helmholtz-member",
    ),  # real world example: all lowercase, first fragment shortened from the end (denoted by ..)
    (
        "-abcdefaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "_abcdefaaaaaaaaaaaaaaaaaaaaaaa..",
    ),  # - as first character replaced with _, one fragment, shortened from the end
    (
        "abcdefaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "abcdefaaaaaaaaaaaaaaaaaaaaaaaa..",
    ),  # one fragment
    (
        "abcdefghij_abcdefghij_abcdefghij_abcdefghijk",
        "a.._abc.._abcdefghij_abcdefghijk",
    ),  # multiple fragments, two fragments need to be shortened, start with the first fragment; first character is always kept from a fragment
    (
        "abcdefaaaaaaaaaaaaaaaaaaaaaaaaaaa_bbbbbbbbbb",
        "abcdefaaaaaaaaaaaaa.._bbbbbbbbbb",
    ),  # multiple fragments, shortening first fragment is sufficient
    (
        "abcdefghijkl_b_cc__abcdefghijklmnop_eeeeeeee",
        "a.._b_cc__abcdefghijk.._eeeeeeee",
    ),  # fragments with length 0, 1, 2 are not shortened
    (
        "a_ab_abc_abcde_abcde_abcdefghi_abcdefghijklm",
        "a_ab_abc_a.._a.._a.._abcdefghi..",
    ),  # fragments with length 1, 2, 3 are not shortened
    (
        "aaaaaaaaaa_bbbb_cccc_ddddddddddddddddddddddd",
        "a.._b.._c.._dddddddddddddddddd..",
    ),  # all fragments are shortened
    (
        "abcdefabcdefabcdefabcdefabcdefabcdefabcdef_aaaaaaa",
        "abcdefabcdefabcdefabcd.._aaaaaaa",
    ),  # only first fragment is shortened
    (
        "abcdefabcdef_a_ab_cd_ef_abc_abcd_abcdef_abcdefghij",
        "a.._a_ab_cd_ef_abc_a.._a.._abc..",
    ),  # fragments with length 1, 2, 3 are not shortened
]

INPUT_SHADOW_COMPATIBLE_FAIL_V044 = [
    "_________________________________",  # all _ => no fragments can be shortened
    "a_b_c_d_e_f_g_h_i_j_k_l_m_n_o_p_q",  # all fragments of length 1, cannot be shortened
    "aa_bb_cc_dd_ee_ff_gg_hh_ii_jj_kk_",  # all fragments of length 2, cannot be shortened
    "aaa_bbb_ccc_ddd_eee_fff_ggg_hhh_iii",  # all fragments of length 3, cannot be shortened
]


@pytest.mark.parametrize("raw", [x[0] for x in INPUT_SHADOW_COMPATIBLE])
def test_make_shadow_compatible_length(raw):
    """a shadow-compatible name must be at most 32 characters long"""
    assert len(ldf_adapter.backend.local_unix.make_shadow_compatible(raw)) <= 32


@pytest.mark.parametrize("raw", [x[0] for x in INPUT_SHADOW_COMPATIBLE])
def test_make_shadow_compatible_allowed_chars(raw):
    """a shadow-compatible name must start with a lowercase letter or underscore
    and can also contain numbers and - in addition to lowercase letters and _
    """
    word = ldf_adapter.backend.local_unix.make_shadow_compatible(raw)
    assert regex.match(r"[a-z_]", word[0]) and regex.match(r"[-0-9_a-z]", word)


@pytest.mark.parametrize("raw,cooked", INPUT_SHADOW_COMPATIBLE)
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
    - shortening names longer than 32 chars to 32 as follows:
        - fragments (substrings separated by _) are shortened starting with the first fragment
          until the length 32 is reached
        - a fragment is shortened by removing the necessary amount of characters from the end,
          and adding .. at the end to denote the shortening took place, e.g. "abcdef" -> "abc.."
        - the length of any fragment has to be > 3 to be considered for shortening
        - the first character of a fragment is always kept, ie. the strongest shortening of "abcdef" will be "a.."
    """
    assert ldf_adapter.backend.local_unix.make_shadow_compatible(raw) == cooked


@pytest.mark.parametrize("raw,cooked", INPUT_SHADOW_COMPATIBLE_PUNCH4NFDI)
def test_make_shadow_compatible_punch4nfdi(raw, cooked):
    word = ldf_adapter.backend.local_unix.make_shadow_compatible_punch4nfdi(raw)
    assert len(word) <= 32
    assert regex.match(r"[a-z_]", word[0]) and regex.match(r"[-0-9_a-z]", word)
    assert word == cooked


@pytest.mark.parametrize("raw", INPUT_SHADOW_COMPATIBLE_FAIL)
def test_make_shadow_compatible_fail(raw):
    """expected behaviour: raise ValueError
    - some names might have too many fragments and cannot be shortened
    """
    with pytest.raises(ValueError):
        ldf_adapter.backend.local_unix.make_shadow_compatible(raw)


INPUT_UNIX_GROUP_PUNCH = {
    "new_root": f"/tmp/newroot{random.randint(1000, 9999)}",
    "name": "dfn-de-nfdi-de-punch_punch4nfdi_punch_intra",
    "group_entry": "punch4nfdi_punch_intra:x:1000:",
    "punch4nfdi": True,
}


@pytest.mark.parametrize("input,exists", [(INPUT_UNIX_GROUP_PUNCH, False)])
def test_create_group_punch4nfdi_enabled(local_unix_group, input):
    """Test that create method adds the appropriate entry in /etc/group when punch4nfdi flag is enabled."""
    local_unix_group.create()
    assert input["group_entry"] in (Path(input["new_root"]) / "etc" / "group").read_text()
