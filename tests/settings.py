
def wrap_userinfo(input):
    return {'user': {'userinfo': input}}


INPUT_UNITY = wrap_userinfo({
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
        "sub": "6c611e2a-2c1c-487f-9948-c058a36c8f0e",
        "iss": "https://login.helmholtz-data-federation.de/oauth2"
    })

INPUT_EGI = wrap_userinfo({
        "acr": "https://aai.egi.eu/LoA#Substantial",
        "eduperson_assurance": [
            "https://aai.egi.eu/LoA#Substantial"
        ],
        "email": "marcus.hardt@kit.edu",
        "family_name": "Hardt",
        "given_name": "Marcus",
        "preferred_username": "mhardt",
        "sub": "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756@egi.eu",
        "iss": "https://aai.egi.eu/oidc/"
    })

INPUT_DEEP_IAM = wrap_userinfo({
        "iss": "https://iam.deep-hybrid-datacloud.eu/",
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
    })

INPUT_INDIGO_IAM = wrap_userinfo({
        "iss": "https://iam-test.indigo-datacloud.eu/",
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
    })

INPUT_KIT = wrap_userinfo({
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
        "sub": "4cbcd471-1f51-4e54-97b8-2dd5177e25ec",
        "iss": "https://oidc.scc.kit.edu/auth/realms/kit/"
    })


ALL_INPUT = [
    INPUT_UNITY,
    INPUT_EGI,
    INPUT_DEEP_IAM,
    INPUT_INDIGO_IAM,
    INPUT_KIT
]