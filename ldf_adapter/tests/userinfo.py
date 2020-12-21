
from unittest import TestCase

from itertools import repeat

from ldf_adapter import *

logger = logging.getLogger(__name__)


class UserInfoTest(TestCase):

    def test_sub_masked_for_bwidm_eppn_unchanged(self):

        subs = [
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
            "w72mv9VQ62SDcBGFw4Izw7Vj5eH0JYRXdN0xImmIfZtAszqFz5mrB5aBxTZKqieTExDJWlrlAGfHIAZ"
        ]

        for sub in subs:
            info = UserInfo({'user': {'userinfo': {'sub': sub}}})
            self.assertEqual(info._sub_masked_for_bwidm_eppn(), sub)

    def test_sub_masked_for_bwidm_eppn_rnd(self):
        # Generated with: cat /dev/urandom | tr -dc '[:graph:]' | tr -d 'a-zA-Z0-9_!#$%&*+/=?{|}~^.\-' | fold -w 80 | head -n 20 | sed 's/\\/\\\\/g;s/'\''/\\'\''/g;s/^/'\''/;s/$/'\'',/'

        subs = [
            ')@\\\'>""\'`,,();@"",,[];>,@,((::;;\'\']<)[:]"@;<\\<",])]>\'][@`<[\\<)>();("`"@\';;[(;[@;',
            ',`@:(,(>>;,()],["(@,\'"<]:[[,::;,@>`<[;\\:,@,(",:;)]`::;;>@<](><:(],@]\\:\\\'\'>>:\\\\>"',
            '@;<@,)]`[],:,,;\\>,](":,]@"@\'>)>]]@(]```(\\(),"(\\[,"(<`<[):;>`(:`,>,\':<[>`";>),(@@',
            '<`:;>``,@";))[\']@((>:)>`@\'":)>:"`,)><,\\""`,\';)<`\\>]`\'((\\>("<]\\\\\'>\\>\\\\"">],\\[<\'[\\',
            '\'\'\\\\\'>><\'>]\'`\'<)>,(;:,`)\'>\'];,,]@@";]]\',[\\([;`([>@[\\:;)@(<[@"`,`@\'\'"));,\\><`>>,@',
            '(`>@]`)\':]>@""@@<:;::,>\\\\(":`<`]\'(<@\')[\\\'(\'@\\:";"`(<[:][[@<,"),<\\,;));\'>`\'\\>\':[)',
            '(]`\\"\\`\'(;;)\\[\\)`\\[`)](>`]`)\\[]\\:>::@;\\[\',[><`:">@@,(@\'`[@@````,`<,\'])(\\[]\'(]<[<',
            ']<[\'`)<`[)>\\<]\']@>,(""["<,":](""\'>,,\'@\\]><)\\\',(\\"("[``\'@];<"(:>[>\')\\;)::,[:;>",[',
            '"(()\'\'\\\'@)]:;:;\'<":])`\\(`\'(](),@;:]\'>);";\'\\((::[;><)\'(<[`(::(>>(@)(;\\,@[`]):,`,)',
            '`)<"\']@:@):"]`\\);:\\\\`">)\\@>><;>)],<:;\\],`<[]])(\'\\\\,(,\\:`(@>;\'[))<,,"];@[`,<>\\\\\';',
            '(>`";>\'\'@;)")\'\\;<\\`<:<,"]@:(:)">\\@\\<[;)[:<@"\\(],(":)<\'"<,<`>:)@\';@`]:,[\\\\@<[\'>>\\',
            '])``\\;"]`):\\`),):\';\';[\'")>,`[<">":>>(\'](,[)<\'@;:[[@@]`@;((@<<;`\\():;[:<,\'`>>\\[",',
            ']]"<@``;;<<]);<];):\'[,<<>\\>))>(>`)")\'(`<]>:@<:;,@>)\';(:)>))\'\';::>[]<]\'`)@["<`<](',
            ')<>][`";["",():`]@@[`];(;)\'\\\':,]`[\\[@]\'"";":<",[)())\\<,];"<,\'"<,:]"::(]<>@](@)<\\',
            '<;::>\'];(>[;;],]:(@<<:",<\'>\\@,""`(@\\\\@)@\'<[`,:<(\'`;<@\\"><@>:[](,`<]""`@"[""[)(\\:',
            '::>"(:(())[\\\'(,[\'((`):\']\';`"]`@,\';:];@<`<:\\,;:">:)<\'@(()]\\"<;"(>[());[@@:][:;,]`',
            ';``@[,,[@<;;,]<[";\'`["":;<[(;:])[;@\'\'>@<():`)""<"<\\,@><@@)\']<@"@`]\'(@>(<@@@\'`\'":',
            '@\'[<,[>:@@[`(;:[<<](:@)<<,>">"[\\,:\'@\']\';,\\\\"(]:<,`<",>],\'>`:[,)(@([:>\\\\@]):@\\;,>',
            '))"]["(@,[[\']]<);)\'<)`@,@:"`\'`">"<[\'])\';;("]:,"\\(]@>@\'`;:()(`>)>[]>)<<,>:;,:;@[;',
            ':)]](,);\\\'(\\,,:\\`(<`<\'[@(,;[;<""""`<<(,@@",)`><@[)\'`"`]<]<\\\\:(`\\`>`<;`;(["\\,[[[]',
        ]

        for sub in subs:
            info = UserInfo({'user': {'userinfo': {'sub': sub}}})
            self.assertEqual(info._sub_masked_for_bwidm_eppn(), "".join(repeat('-', 80)))


    def test_iss_masked_for_bwidm_eppn_fixes_prefix(self):
        isss = [
            "example.org",
            "http://example.org",
            "https://example.org"
        ]

        for iss in isss:
            info = UserInfo({'user': {'userinfo': {'iss': iss}}})
            self.assertEqual(info._iss_masked_for_bwidm_eppn(), "example.org")

    def test_iss_masked_for_bwidm_eppn_fixes_umlaute(self):
        isss = [
            ("exämple.org","example.org"),
            ("example.örg","example.org"),
            ("ürsula.org","ursula.org"),
        ]

        for raw,cooked in isss:
            info = UserInfo({'user': {'userinfo': {'iss': raw}}})
            self.assertEqual(info._iss_masked_for_bwidm_eppn(), cooked)

    def test_iss_masked_for_bwidm_eppn_fixes_urls(self):
        isss = [
            ("example.org/foobar","example.org-foobar"),
            ("example.org/foo%20bar","example.org-foo-20bar"),
        ]

        for raw,cooked in isss:
            info = UserInfo({'user': {'userinfo': {'iss': raw}}})
            self.assertEqual(info._iss_masked_for_bwidm_eppn(), cooked)


    def test_group_masked_for_bwidm_converts_camel_to_snake_case(self):
        isss = [
            ("fooBarBaz", "foo_bar_baz"),
            ("FooBarBaz", "foo_bar_baz"),
        ]

        for raw,cooked in isss:
            info = UserInfo({'user': {'userinfo': {}}})
            self.assertEqual(info._group_masked_for_bwidm(raw), cooked)

    def test_group_masked_for_bwidm_all_caps(self):
        isss = [
            ("FOOBARBAZ", "foobarbaz"),
            ("FOO-BAR-BAZ", "foo-bar-baz"),
        ]

        for raw,cooked in isss:
            info = UserInfo({'user': {'userinfo': {}}})
            self.assertEqual(info._group_masked_for_bwidm(raw), cooked)

    def test_group_masked_for_bwidm_fixes_beginning(self):
        isss = [
            ("42", "four_2"),
            ("--test--", "test--"),
            ("__init__()", "init__--"),
            ("?!#_bullshit", "bullshit")
        ]

        for raw,cooked in isss:
            info = UserInfo({'user': {'userinfo': {}}})
            self.assertEqual(info._group_masked_for_bwidm(raw), cooked)


class UserInfoIntegration(TestCase):
    def assert_name(self, info):
        self.assertEqual(info.given_name, "Marcus")
        self.assertEqual(info.family_name, "Hardt")
        self.assertEqual(info.full_name, "Marcus Hardt")

    def test_unity(self):
        input = {
            "display_name": "Marcus Hardt",
            "eduperson_assurance": [
                "https://refeds.org/assurance/IAP/medium",
                "https://refeds.org/assurance/IAP/local-enterprise",
                "https://refeds.org/assurance/ID/eppn-unique-no-reassign",
                "https://refeds.org/assurance/ATP/ePA-1m",
                "https://refeds.org/assurance/ATP/ePA-1d",
                "https://refeds.org/assurance/ID/unique",
                "https://refeds.org/assurance/profile/cappuccino",
                "https://refeds.org/assurance/IAP/low"
            ],
            "eduperson_entitlement": [
                "urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de",
                "urn:geant:h-df.de:group:MyExampleColab#login.helmholtz-data-federation.de",
                "urn:geant:h-df.de:group:wlcg-test#login.helmholtz-data-federation.de",
                "urn:geant:h-df.de:group:HDF#login.helmholtz-data-federation.de"
            ],
            "eduperson_principal_name": "lo0018@kit.edu",
            "eduperson_scoped_affiliation": "member@kit.edu",
            "eduperson_unique_id": "6c611e2a2c1c487f9948c058a36c8f0e@login.helmholtz-data-federation.de",
            "email": "marcus.hardt@kit.edu",
            "email_verified": "true",
            "family_name": "Hardt",
            "given_name": "Marcus",
            "groups": [
                "/wlcg-test",
                "/IMK-TRO-EWCC",
                "/MyExampleColab",
                "/HDF",
                "/"
            ],
            "name": "Marcus Hardt",
            "preferred_username": "marcus",
            "sn": "Hardt",
            "ssh_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAqA5FW6m3FbFhCOsRQBxKMRki5qJxoNhZdaeLXg6ym/ marcus@nemo2019\n",
            "sub": "6c611e2a-2c1c-487f-9948-c058a36c8f0e"
        }

        info = UserInfo({'user': {'userinfo': input}})
        self.assert_name(info)
        self.assertEqual(info.username, "marcus")
        self.assertEqual(info.email, "marcus.hardt@kit.edu")
        self.assertEqual(sorted(info.groups), sorted(["imk-tro-ewcc", "my_example_colab", "wlcg-test", "hdf"]))

        self.assertEqual(info.unique_id,
                         "6c611e2a2c1c487f9948c058a36c8f0e@login.helmholtz-data-federation.de")
        self.assertEqual(info.eppn, "lo0018@kit.edu")

        self.assertTrue(info.assurance.profile.is_cappuccino())


    input_egi = {
        "acr": "https://aai.egi.eu/LoA#Substantial",
        "eduperson_assurance": [
            "https://aai.egi.eu/LoA#Substantial"
        ],
        "email": "marcus.hardt@kit.edu",
        "family_name": "Hardt",
        "given_name": "Marcus",
        "preferred_username": "mhardt",
        "sub": "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756@egi.eu",
        "iss": "egi.eu"
    }

    def test_egi(self):
        info = UserInfo({'user': {'userinfo': self.input_egi}})
        self.assert_name(info)
        self.assertEqual(info.username, "mhardt")
        self.assertEqual(info.email, "marcus.hardt@kit.edu")

    def test_egi_id(self):
        info = UserInfo({'user': {'userinfo': self.input_egi}})
        self.assertEqual(info.unique_id, "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756@egi.eu")
        self.assertEqual(info.eppn, info.unique_id)

    def test_egi_sub_is_unscoped(self):
        info = UserInfo({'user': {'userinfo': self.input_egi}})
        self.assertIn('@', info.userinfo['sub'])


    input_deep_iam = {
        "external_authn": {
            "iss": "https://accounts.google.com",
            "sub": "104223951181002749851",
            "type": "oidc"
        },
        "family_name": "Hardt",
        "given_name": "Marcus",
        "groups": [
            "KIT-Cloud"
        ],
        "name": "Marcus Hardt",
        "organisation_name": "deep-hdc",
        "preferred_username": "marcus",
        "sub": "d9730f60-3b19-4f45-83ab-f29addf72d58",
        "updated_at": "Mon Jun 25 16:55:15 CEST 2018"
    }

    def test_deep_iam(self):
        info = UserInfo({'user': {'userinfo': self.input_deep_iam}})
        self.assert_name(info)
        self.assertEqual(info.username, "marcus")
        self.assertEqual(sorted(info.groups), []) # We only support entitlements

    def test_deep_iam_id(self):
        info = UserInfo({'user': {'userinfo': self.input_egi}})
        with self.assertRaises(KeyError):
            self.assertEqual(info.unique_id, "d9730f60-3b19-4f45-83ab-f29addf72d58@deep-hdc")


    input_indigo_iam = {
        "external_authn": {
            "iss": "https://accounts.google.com",
            "sub": "104223951181002749851",
            "type": "oidc"
        },
        "family_name": "Hardt",
        "gender": "M",
        "given_name": "Marcus",
        "groups": [
            "Users",
            "Developers",
            "test.vo-users"
        ],
        "name": "Marcus Hardt",
        "organisation_name": "indigo-dc",
        "preferred_username": "marcus",
        "sub": "a1ea3aa2-8daf-41bb-b4fb-eb88f439e446",
        "updated_at": 1563283972
    }

    def test_indigo_iam(self):
        info = UserInfo({'user': {'userinfo': self.input_indigo_iam}})
        self.assert_name(info)
        self.assertEqual(info.username, "marcus")
        self.assertEqual(sorted(info.groups), sorted(["users", "developers", "test-vo-users"]))

    def test_indigo_iam_id(self):
        info = UserInfo({'user': {'userinfo': self.input_indigo_iam}})
        self.assertEqual(info.unique_id, "d9730f60-3b19-4f45-83ab-f29addf72d58@indigo-dc")
        self.assertEqual(info.eppn, info.unique_id)


    input_kit = {
        "displayName": "Hardt, Marcus (SCC)",
        "eduPersonEntitlement": [
            "urn:geant:kit.edu:group:DFN-SLCS",
            "urn:geant:kit.edu:group:LSDF-DIS",
            "urn:geant:kit.edu:group:bwGrid",
            "urn:geant:kit.edu:group:bwLSDF-FS",
            "urn:geant:kit.edu:group:bwUniCluster",
            "urn:geant:kit.edu:group:bwsyncnshare",
            "urn:geant:kit.edu:group:bwsyncnshare-idm",
            "urn:geant:kit.edu:group:gruppenverwalter"
        ],
        "eduPersonPrincipalName": "lo0018@kit.edu",
        "eduPersonScopedAffiliation": [
            "employee@kit.edu",
            "member@kit.edu"
        ],
        "eduperson_entitlement": [
            "urn:geant:kit.edu:group:DFN-SLCS",
            "urn:geant:kit.edu:group:LSDF-DIS",
            "urn:geant:kit.edu:group:bwGrid",
            "urn:geant:kit.edu:group:bwLSDF-FS",
            "urn:geant:kit.edu:group:bwUniCluster",
            "urn:geant:kit.edu:group:bwsyncnshare",
            "urn:geant:kit.edu:group:bwsyncnshare-idm",
            "urn:geant:kit.edu:group:gruppenverwalter"
        ],
        "eduperson_principal_name": "lo0018@kit.edu",
        "eduperson_scoped_affiliation": [
            "employee@kit.edu",
            "member@kit.edu"
        ],
        "email": "marcus.hardt@kit.edu",
        "family_name": "Hardt",
        "givenName": "Marcus",
        "given_name": "Marcus",
        "mail": "marcus.hardt@kit.edu",
        "name": "Marcus Hardt",
        "ou": "SCC",
        "preferred_username": "lo0018",
        "sn": "Hardt",
        "sub": "4cbcd471-1f51-4e54-97b8-2dd5177e25ec"
    }

    def test_kit(self):
        info = UserInfo({'user': {'userinfo': self.input_kit}})
        self.assert_name(info)
        self.assertEqual(info.username, "lo0018")
        self.assertEqual(info.email, "marcus.hardt@kit.edu")

    def test_kit_id(self):
        info = UserInfo({'user': {'userinfo': self.input_kit}})
        self.assertEqual(info.unique_id, "4cbcd471-1f51-4e54-97b8-2dd5177e25ec@kit.edu")
        self.assertEqual(info.eppn, "lo0018@kit.edu")

    def test_ignore_excess_entitlement(self):
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
                "https://refeds.org/assurance/IAP/low"
            ],
            "eduperson_entitlement": [
                "urn:mace:dir:entitlement:common-lib-terms",
                "http://bwidm.de/entitlement/bwLSDF-SyncShare",
                "urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de",
                "urn:geant:h-df.de:group:MyExampleColab#login.helmholtz-data-federation.de",
                "urn:geant:h-df.de:group:wlcg-test#login.helmholtz-data-federation.de",
                "urn:geant:h-df.de:group:HDF#login.helmholtz-data-federation.de"
            ],
            "eduperson_scoped_affiliation": "member@kit.edu",
            "email": "marcus.hardt@kit.edu",
            "email_verified": "true",
            "family_name": "Hardt",
            "given_name": "Marcus",
            "groups": [
                "/wlcg-test",
                "/IMK-TRO-EWCC",
                "/MyExampleColab",
                "/HDF",
                "/"
            ],
            "iss": "https://login.helmholtz-data-federation.de/oauth2",
            "name": "Marcus Hardt",
            "preferred_username": "marcus",
            "ssh_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAqA5FW6m3FbFhCOsRQBxKMRki5qJxoNhZdaeLXg6ym/ marcus@nemo2019\n",
            "sub": "6c611e2a-2c1c-487f-9948-c058a36c8f0e"
        }

        info = UserInfo({'user': {'userinfo': input_test}})
        self.assertEqual(len(list(info.entitlement)), 4)
