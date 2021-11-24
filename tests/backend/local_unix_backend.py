import pytest
import regex

# from ldf_adapter import UserInfo, CONFIG
from ldf_adapter.backend.local_unix import make_shadow_compatible
import settings


# @pytest.mark.parametrize('data', [settings.INPUT_UNITY])
# def test_create(local_unix_backend):
#     assert not local_unix_backend.exists()
#     # local_unix_backend.create()
#     # assert local_unix_backend.exists()

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
