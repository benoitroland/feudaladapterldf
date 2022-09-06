import pytest
import mock
from itertools import repeat

from ldf_adapter.userinfo import UserInfo
from . import settings


@pytest.mark.parametrize(
    "sub",
    [
        "MWMQb4ybpHVSThMGpRKkqFDJIYlGLXl1CWXSRgM8bQGR9mMXRXtMbLFubL8Sua6vZn8Dq9X3YGoKR",
        "bNAkgXeaN2rlP83UeckV0fSjU2qNmKjQ7BsOsGFC7KB1PHtYGxRXkdSZ6S1egB085cwkIYt0NNPe",
        "0Y7zkfbvLmFVclSBFqtioE0xAaV4ZtMJ7tHxScwAN6FKoPn9R3aSXjoqp1jxRWFnyN7kNoq0nvJ33f7",
        "CO6bVYGIPtzPMHpm9o13S1bztxv6jHVEAXsGX3yBRmSv8RNnVsyzjJ67bvuvl4Tq2T8rPNTcfRRqgFF",
        "X5MOmSBpHzNj3h2BzHwhCFnHzMEpT7BxJEh6X0sgpqp7TBuUdLnfBIoovpQGEYZ7zxloVgmBV5B0FUa",
        "QHp9whOAuvUgmbJBUas1haLQfa4y4VnRlxbJwqm7pqvOfZudZAbDCXlIi20ifqfBYyjQpFN9XbOUSHi",
        "bQZO9gf6K08rlRilSYNlIuroaUBvlTV2QmHFHUlm8HUWZHs8RlNnvxQZXZZ62Oju3GARJQTx8Vb8vkF",
        "YqZE73sSxnOgoJ4jW0AhFfyZZPoaQGuzWZljOL4Nmt4x6VITfrH8EzJNES2uc0mOfGZrEIWUrxCHD6J",
        "LrcvjVB6q3omCRjzoX2uLJZzurDcU0srxJqoSmOSdCvdxisxvRo9nj52jCUxYCEnEW3FV4fKFt25Cqq4",
        "p32UOxqQGTh7xD8mfY1w9XVc0j2II06oXjw19iGhWUDMOMJiOFbwbwQRR6XVyHDwnR5hPA4bWlAxi6SK",
        "TRJvjHpnkwdsKpCYyjOPbbk5Zvk5YDfaO0BcRXpyntpuUQg5WLu9esrkqxHxH8o28A6An2bSG8mIP",
        "wl1dBQBFgPHFgetwz9m6VOYeTzGn2Pu3AMDtPRX6V0XvzhxhL7y9iEatlPqiSl5OO0yiSQWDz9GJ4Ut",
        "wTAg6ewnKtcpdj1t83NWojg7dr7ydjMhZf93hLCR5NA4GtlVfAJGwmy5XGO0AVMWMO0jhAw2KMhVK5t",
        "IkYQVi17paCZdkURaFput1p5FA2rCemT8szPIwtlDnbeecVuzEdsYVT7C3zXL8TTPKQXDdMxKYbibWO5",
        "yp1Xe4fhSGwdEyqzeejRwL8wxVeiMmamjcydJmR5hjIbQ5AQoN7pe4PwGSvNKXvkQmUO09ju0gVFALh",
        "QP8b8AwjfCw7n20WAyOYDCLztANZaKvc4uCyVtYwJnFWHYaXqFLlolPc9LJ7bb7shaRvFDpQHt07Qo",
        "nScpPJSkxQja7eMtgjM83MILbYarScUR4PWlLXK40rLHavl4dDty2OV6QJLH8AVs7LMtaOrWieHAiY",
        "UuTbVNi2RknFwKfy2n3XfCqkrscrIi0cdpJXVrbzIxBqgcvOOCWGL9YFXVTjWhbFjCvzxFgTR22yKw0X",
        "Vb15x73G3eYqtCEaqjM2MaGtUmKxNansoJxPhff5wtIK1VhDO6PutZrYxEAsxoZYIrhIZMrZpc926h",
        "w72mv9VQ62SDcBGFw4Izw7Vj5eH0JYRXdN0xImmIfZtAszqFz5mrB5aBxTZKqieTExDJWlrlAGfHIAZ",
    ],
)
def test_sub_masked_for_bwidm_eppn_unchanged(sub):
    info = UserInfo({"user": {"userinfo": {"sub": sub}}})
    assert info._sub_masked_for_bwidm_eppn() == sub


# Generated with: cat /dev/urandom | tr -dc '[:graph:]' | tr -d 'a-zA-Z0-9_!#$%&*+/=?{|}~^.\-' | fold -w 80 | head -n 20 | sed 's/\\/\\\\/g;s/'\''/\\'\''/g;s/^/'\''/;s/$/'\'',/'
@pytest.mark.parametrize(
    "sub",
    [
        ')@\\\'>""\'`,,();@"",,[];>,@,((::;;\'\']<)[:]"@;<\\<",])]>\'][@`<[\\<)>();("`"@\';;[(;[@;',
        ',`@:(,(>>;,()],["(@,\'"<]:[[,::;,@>`<[;\\:,@,(",:;)]`::;;>@<](><:(],@]\\:\\\'\'>>:\\\\>"',
        '@;<@,)]`[],:,,;\\>,](":,]@"@\'>)>]]@(]```(\\(),"(\\[,"(<`<[):;>`(:`,>,\':<[>`";>),(@@',
        '<`:;>``,@";))[\']@((>:)>`@\'":)>:"`,)><,\\""`,\';)<`\\>]`\'((\\>("<]\\\\\'>\\>\\\\"">],\\[<\'[\\',
        "''\\\\'>><'>]'`'<)>,(;:,`)'>'];,,]@@\";]]',[\\([;`([>@[\\:;)@(<[@\"`,`@''\"));,\\><`>>,@",
        "(`>@]`)':]>@\"\"@@<:;::,>\\\\(\":`<`]'(<@')[\\'('@\\:\";\"`(<[:][[@<,\"),<\\,;));'>`'\\>':[)",
        "(]`\\\"\\`'(;;)\\[\\)`\\[`)](>`]`)\\[]\\:>::@;\\[',[><`:\">@@,(@'`[@@````,`<,'])(\\[]'(]<[<",
        ']<[\'`)<`[)>\\<]\']@>,(""["<,":](""\'>,,\'@\\]><)\\\',(\\"("[``\'@];<"(:>[>\')\\;)::,[:;>",[',
        "\"(()''\\'@)]:;:;'<\":])`\\(`'(](),@;:]'>);\";'\\((::[;><)'(<[`(::(>>(@)(;\\,@[`]):,`,)",
        "`)<\"']@:@):\"]`\\);:\\\\`\">)\\@>><;>)],<:;\\],`<[]])('\\\\,(,\\:`(@>;'[))<,,\"];@[`,<>\\\\';",
        '(>`";>\'\'@;)")\'\\;<\\`<:<,"]@:(:)">\\@\\<[;)[:<@"\\(],(":)<\'"<,<`>:)@\';@`]:,[\\\\@<[\'>>\\',
        "])``\\;\"]`):\\`),):';';['\")>,`[<\">\":>>('](,[)<'@;:[[@@]`@;((@<<;`\\():;[:<,'`>>\\[\",",
        "]]\"<@``;;<<]);<];):'[,<<>\\>))>(>`)\")'(`<]>:@<:;,@>)';(:)>))'';::>[]<]'`)@[\"<`<](",
        ')<>][`";["",():`]@@[`];(;)\'\\\':,]`[\\[@]\'"";":<",[)())\\<,];"<,\'"<,:]"::(]<>@](@)<\\',
        '<;::>\'];(>[;;],]:(@<<:",<\'>\\@,""`(@\\\\@)@\'<[`,:<(\'`;<@\\"><@>:[](,`<]""`@"[""[)(\\:',
        "::>\"(:(())[\\'(,['((`):']';`\"]`@,';:];@<`<:\\,;:\">:)<'@(()]\\\"<;\"(>[());[@@:][:;,]`",
        ';``@[,,[@<;;,]<[";\'`["":;<[(;:])[;@\'\'>@<():`)""<"<\\,@><@@)\']<@"@`]\'(@>(<@@@\'`\'":',
        "@'[<,[>:@@[`(;:[<<](:@)<<,>\">\"[\\,:'@']';,\\\\\"(]:<,`<\",>],'>`:[,)(@([:>\\\\@]):@\\;,>",
        '))"]["(@,[[\']]<);)\'<)`@,@:"`\'`">"<[\'])\';;("]:,"\\(]@>@\'`;:()(`>)>[]>)<<,>:;,:;@[;',
        ':)]](,);\\\'(\\,,:\\`(<`<\'[@(,;[;<""""`<<(,@@",)`><@[)\'`"`]<]<\\\\:(`\\`>`<;`;(["\\,[[[]',
    ],
)
def test_sub_masked_for_bwidm_eppn_rnd(sub):
    info = UserInfo({"user": {"userinfo": {"sub": sub}}})
    assert info._sub_masked_for_bwidm_eppn() == "".join(repeat("-", 80))


@pytest.mark.parametrize("iss", ["example.org", "http://example.org", "https://example.org"])
def test_iss_masked_for_bwidm_eppn_fixes_prefix(iss):
    info = UserInfo({"user": {"userinfo": {"iss": iss}}})
    assert info._iss_masked_for_bwidm_eppn() == "example.org"


@pytest.mark.parametrize(
    "raw,cooked",
    [
        ("exämple.org", "example.org"),
        ("example.örg", "example.org"),
        ("ürsula.org", "ursula.org"),
    ],
)
def test_iss_masked_for_bwidm_eppn_fixes_umlaute(raw, cooked):
    info = UserInfo({"user": {"userinfo": {"iss": raw}}})
    assert info._iss_masked_for_bwidm_eppn() == cooked


@pytest.mark.parametrize(
    "raw,cooked",
    [
        ("example.org/foobar", "example.org-foobar"),
        ("example.org/foo%20bar", "example.org-foo-20bar"),
    ],
)
def test_iss_masked_for_bwidm_eppn_fixes_urls(raw, cooked):
    info = UserInfo({"user": {"userinfo": {"iss": raw}}})
    assert info._iss_masked_for_bwidm_eppn() == cooked


@pytest.mark.parametrize(
    "raw,cooked",
    [
        ("fooBarBaz", "foo_bar_baz"),
        ("FooBarBaz", "foo_bar_baz"),
        ("kit-edu_LSDF-DIS", "kit-edu_lsdf-dis"),
        ("kit-edu_bwGrid", "kit-edu_bw_grid"),
        ("kit-edu_bwLSDF-FS", "kit-edu_bw_lsdf-fs"),
        ("kit-edu_bwUniCluster", "kit-edu_bw_uni_cluster"),
    ],
)
def test_group_masked_for_bwidm_converts_camel_to_snake_case(raw, cooked):
    info = UserInfo({"user": {"userinfo": {}}})
    assert info._group_masked_for_bwidm(raw) == cooked


@pytest.mark.parametrize(
    "raw,cooked",
    [
        ("FOOBARBAZ", "foobarbaz"),
        ("FOO-BAR-BAZ", "foo-bar-baz"),
    ],
)
def test_group_masked_for_bwidm_all_caps(raw, cooked):
    info = UserInfo({"user": {"userinfo": {}}})
    assert info._group_masked_for_bwidm(raw) == cooked


@pytest.mark.parametrize(
    "raw,cooked",
    [
        ("42", "four_2"),
        ("--test--", "test--"),
        ("__init__()", "init__--"),
        ("?!#_bullshit", "bullshit"),
    ],
)
def test_group_masked_for_bwidm_fixes_beginning(raw, cooked):
    info = UserInfo({"user": {"userinfo": {}}})
    assert info._group_masked_for_bwidm(raw) == cooked


@pytest.mark.parametrize("data", settings.ALL_INPUT)
def test_given_name(userinfo):
    assert userinfo.given_name == "Marcus"


@pytest.mark.parametrize("data", settings.ALL_INPUT)
def test_family_name(userinfo):
    assert userinfo.family_name == "Hardt"


@pytest.mark.parametrize("data", settings.ALL_INPUT)
def test_full_name(userinfo):
    assert userinfo.full_name == "Marcus Hardt"


@pytest.mark.parametrize(
    "data,username",
    [
        (settings.INPUT_UNITY, "marcus"),
        (settings.INPUT_EGI, "mhardt"),
        (settings.INPUT_DEEP_IAM, "marcus"),
        (settings.INPUT_INDIGO_IAM, "marcus"),
        (settings.INPUT_KIT, "lo0018"),
    ],
)
def test_username(userinfo, username):
    assert userinfo.username == username


@pytest.mark.parametrize(
    "data,email",
    [
        (settings.INPUT_UNITY, "marcus.hardt@kit.edu"),
        (settings.INPUT_EGI, "marcus.hardt@kit.edu"),
        (settings.INPUT_DEEP_IAM, None),
        (settings.INPUT_INDIGO_IAM, None),
        (settings.INPUT_KIT, "marcus.hardt@kit.edu"),
    ],
)
def test_email(userinfo, email):
    assert userinfo.email == email


@pytest.mark.parametrize(
    "data,unique_id",
    [
        (
            settings.INPUT_UNITY,
            "6c611e2a-2c1c-487f-9948-c058a36c8f0e@https%3A%2F%2Flogin.helmholtz-data-federation.de%2Foauth2",
        ),
        (
            settings.INPUT_EGI,
            "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756%40egi.eu@https%3A%2F%2Faai.egi.eu%2Foidc%2F",
        ),
        (
            settings.INPUT_DEEP_IAM,
            "d9730f60-3b19-4f45-83ab-f29addf72d58@https%3A%2F%2Fiam.deep-hybrid-datacloud.eu%2F",
        ),
        (
            settings.INPUT_INDIGO_IAM,
            "a1ea3aa2-8daf-41bb-b4fb-eb88f439e446@https%3A%2F%2Fiam-test.indigo-datacloud.eu%2F",
        ),
        (
            settings.INPUT_KIT,
            "4cbcd471-1f51-4e54-97b8-2dd5177e25ec@https%3A%2F%2Foidc.scc.kit.edu%2Fauth%2Frealms%2Fkit%2F",
        ),
    ],
)
def test_unique_id(userinfo, unique_id):
    assert userinfo.unique_id == unique_id


@pytest.mark.parametrize(
    "data,eppn",
    [
        (
            settings.INPUT_UNITY,
            "6c611e2a-2c1c-487f-9948-c058a36c8f0e@login.helmholtz-data-federation.de-oauth2",
        ),
        (
            settings.INPUT_EGI,
            "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756-egi.eu@aai.egi.eu-oidc-",
        ),
        (
            settings.INPUT_DEEP_IAM,
            "d9730f60-3b19-4f45-83ab-f29addf72d58@iam.deep-hybrid-datacloud.eu-",
        ),
        (
            settings.INPUT_INDIGO_IAM,
            "a1ea3aa2-8daf-41bb-b4fb-eb88f439e446@iam-test.indigo-datacloud.eu-",
        ),
        (
            settings.INPUT_KIT,
            "4cbcd471-1f51-4e54-97b8-2dd5177e25ec@oidc.scc.kit.edu-auth-realms-kit-",
        ),
    ],
)
def test_eppn(userinfo, eppn):
    assert userinfo.eppn == eppn


@pytest.mark.parametrize(
    "data,groups",
    [
        (
            settings.INPUT_UNITY,
            [
                "h-df-de_imk-tro-ewcc",
                "h-df-de_my_example_colab",
                "h-df-de_wlcg-test",
                "h-df-de_hdf",
            ],
        ),
        (settings.INPUT_EGI, []),
        (settings.INPUT_DEEP_IAM, ["kit-cloud"]),
        (settings.INPUT_INDIGO_IAM, ["users", "developers", "test-vo-users"]),
        (
            settings.INPUT_KIT,
            [
                "kit-edu_dfn-slcs",
                "kit-edu_lsdf-dis",
                "kit-edu_bw_grid",
                "kit-edu_bw_lsdf-fs",
                "kit-edu_bw_uni_cluster",
                "kit-edu_bwsyncnshare",
                "kit-edu_bwsyncnshare-idm",
                "kit-edu_gruppenverwalter",
            ],
        ),
    ],
)
def test_groups(userinfo, groups):
    assert sorted(userinfo.groups) == sorted(groups)


@mock.patch("ldf_adapter.userinfo.CONFIG.ldf_adapter.fallback_group", "nogroup")
@mock.patch("ldf_adapter.userinfo.CONFIG.ldf_adapter.primary_group", "mytestgroup")
@pytest.mark.parametrize("data", settings.ALL_INPUT)
def test_primary_group_primary_and_fallback_configured(userinfo):
    assert userinfo.primary_group == "mytestgroup"


@pytest.mark.parametrize(
    "data,group",
    [
        (settings.INPUT_UNITY, "h-df-de_hdf"),
        (settings.INPUT_EGI, None),
        (settings.INPUT_DEEP_IAM, "kit-cloud"),
        (settings.INPUT_INDIGO_IAM, "developers"),
        (settings.INPUT_KIT, "kit-edu_bw_grid"),
    ],
)
def test_primary_group_no_fallback_or_primary_configured(userinfo, group):
    assert userinfo.primary_group == group


@mock.patch("ldf_adapter.userinfo.CONFIG.ldf_adapter.fallback_group", "nogroup")
@pytest.mark.parametrize(
    "data,group",
    [
        (settings.INPUT_UNITY, "h-df-de_hdf"),
        (settings.INPUT_EGI, "nogroup"),
        (settings.INPUT_DEEP_IAM, "kit-cloud"),
        (settings.INPUT_INDIGO_IAM, "developers"),
        (settings.INPUT_KIT, "kit-edu_bw_grid"),
    ],
)
def test_primary_group_fallback_configured_no_primary(userinfo, group):
    assert userinfo.primary_group == group


def test_egi_sub_is_unscoped():
    assert "@" in settings.INPUT_EGI["user"]["userinfo"]["sub"]


@pytest.mark.parametrize(
    "data,assurance",
    [
        (
            settings.INPUT_UNITY,
            [
                "https://refeds.org/assurance/IAP/medium",
                "https://refeds.org/assurance/IAP/local-enterprise",
                "https://refeds.org/assurance/ID/eppn-unique-no-reassign",
                "https://refeds.org/assurance/ATP/ePA-1m",
                "https://refeds.org/assurance/ATP/ePA-1d",
                "https://refeds.org/assurance/ID/unique",
                "https://refeds.org/assurance/profile/cappuccino",
                "https://refeds.org/assurance/IAP/low",
            ],
        ),
        (settings.INPUT_EGI, ["https://aai.egi.eu/LoA#Substantial"]),
        (settings.INPUT_DEEP_IAM, []),
        (settings.INPUT_INDIGO_IAM, []),
        (settings.INPUT_KIT, []),
    ],
)
def test_missing_assurance(userinfo, assurance):
    assert sorted(userinfo.assurance) == sorted(assurance)


def test_ignore_excess_entitlement():
    """https://git.scc.kit.edu/feudal/feudalAdapterLdf/issues/8"""

    input_test = {
        "eduperson_assurance": [
            "https://refeds.org/assurance/IAP/medium",
            "https://refeds.org/assurance/IAP/local-enterprise",
            "https://refeds.org/assurance/ID/eppn-unique-no-reassign",
            "https://refeds.org/assurance/ATP/ePA-1m",
            "https://refeds.org/assurance/ATP/ePA-1d",
            "https://refeds.org/assurance/ID/unique",
            "https://refeds.org/assurance/profile/cappuccino",
            "https://refeds.org/assurance/IAP/low",
        ],
        "eduperson_entitlement": [
            "urn:mace:dir:entitlement:common-lib-terms",
            "http://bwidm.de/entitlement/bwLSDF-SyncShare",
            "urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de",
            "urn:geant:h-df.de:group:MyExampleColab#login.helmholtz-data-federation.de",
            "urn:geant:h-df.de:group:wlcg-test#login.helmholtz-data-federation.de",
            "urn:geant:h-df.de:group:HDF#login.helmholtz-data-federation.de",
        ],
        "eduperson_scoped_affiliation": "member@kit.edu",
        "email": "marcus.hardt@kit.edu",
        "email_verified": "true",
        "family_name": "Hardt",
        "given_name": "Marcus",
        "groups": ["/wlcg-test", "/IMK-TRO-EWCC", "/MyExampleColab", "/HDF", "/"],
        "iss": "https://login.helmholtz-data-federation.de/oauth2",
        "name": "Marcus Hardt",
        "preferred_username": "marcus",
        "ssh_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAqA5FW6m3FbFhCOsRQBxKMRki5qJxoNhZdaeLXg6ym/ marcus@nemo2019\n",
        "sub": "6c611e2a-2c1c-487f-9948-c058a36c8f0e",
    }

    info = UserInfo({"user": {"userinfo": input_test}})
    assert len(list(info.entitlement)) == 4
