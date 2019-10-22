from unittest import TestCase

from itertools import repeat

from ldf_adapter import *

class UserInfoTest(TestCase):
    def test_sub_masked_for_bwidm_eppn_unchanged(self):
        subs = [
            "MWMQb4ybpHVSThMGpRKkqFD-JIYlGLXl1CWXSRgM8bQGR9mMXRXtMbLFubL8S-ua6vZn8Dq9X3YG-oKR",
            "bNAkgXeaN2rlP83UeckV0fSjU2-qN--mKjQ7BsOsGFC-7KB1PHtYGxRXkdSZ6S1egB085cwkIYt0NNPe",
            "0Y7zkfbvLmFVclSBFqtioE0xAaV4ZtMJ7tHxScwAN6FKoPn9R3aSXjoqp1jxRWFnyN-7kNoq0nvJ33f7",
            "CO6bVYGIPtzPMHpm9o13S1bztxv6jHVEAX-sGX3yBRmSv8RNnVsyzjJ67bvuvl4Tq2T8rPNTcfRRqgFF",
            "-X5MOmSBpHzNj3h2BzHwhCFnHzMEpT7BxJEh6X0sgpqp7TBuUdLnfBIoovpQGEYZ7zxloVgmBV5B0FUa",
            "QHp9whOAuvUgmbJBUas1-haLQfa4y4VnRlxbJwqm7pqvOfZudZAbDCXlIi20ifqfBYyjQpFN9XbOUSHi",
            "bQZO9gf6K08rlRilSYNlIuroaUBvlTV2QmHFHUlm8HUWZHs8RlNnvxQ-ZXZZ62Oju3GARJQTx8Vb8vkF",
            "YqZE73sSxnOgoJ4jW0AhFfyZZPoaQGuzWZl-jOL4Nmt4x6VITfrH8EzJNES2uc0mOfGZrEIWUrxCHD6J",
            "LrcvjVB6q3omCRjzoX2uLJZzurDcU0srxJqoSmOSdCvdxisxvRo9nj52jCUxYCEnEW3FV4fKFt25Cqq4",
            "p32UOxqQGTh7xD8mfY1w9XVc0j2II06oXjw19iGhWUDMOMJiOFbwbwQRR6XVyHDwnR5hPA4bWlAxi6SK",
            "TRJvjHpnkwdsKpCYyjOPbbk5Zvk5YDfaO0BcRXpyntpuUQ-g5WLu9e-srkqxHxH8o28A6An-2bSG8mIP",
            "wl1dBQBFgPHFgetwz9m6VOYeTzGn2Pu3AMDtPRX6V0XvzhxhL7y9iEatlPqiSl5OO0yiSQWDz9GJ-4Ut",
            "wTAg6ewnKtcpdj1t83NWojg7dr7ydjMhZf93hLCR5NA4GtlVfAJGwmy5XGO-0AVMWMO0jhAw2KMhVK5t",
            "IkYQVi17paCZdkURaFput1p5FA2rCemT8szPIwtlDnbeecVuzEdsYVT7C3zXL8TTPKQXDdMxKYbibWO5",
            "yp1Xe4fhSGw-dEyqzeejRwL8wxVeiMmamjcydJmR5hjIbQ5AQoN7pe4PwGSvNKXvkQmUO09ju0gVFALh",
            "QP8b8-AwjfCw7-n20WAyOYDCLztANZaKvc4uCyVtYwJnFWHYaXqFLlolPc9LJ7bb7shaRvFDpQHt07Qo",
            "nScpPJSkxQja7eMtgjM83MILbYarScUR4PW-lLXK40rLHavl4dDty2OV6QJLH8AVs-7LMtaOrWieHAiY",
            "UuTbVNi2RknFwKfy2n3XfCqkrscrIi0cdpJXVrbzIxBqgcvOOCWGL9YFXVTjWhbFjCvzxFgTR22yKw0X",
            "Vb15x7-3G3eYqtCEaqjM2M-aGtUmKxNansoJxPhff5wtIK1VhDO6PutZrYxEAsxoZYIrhIZMrZpc926h",
            "w72mv9VQ62SDcBGFw4Izw7Vj5eH0-JYRXdN0xImmIfZtAszqFz5mrB5aBxTZKqieTExDJWlrlAGfHIAZ"
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
