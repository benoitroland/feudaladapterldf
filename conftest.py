# pylint: disable=global-statement

import pytest

from ldf_adapter import config as globalConfig, UserInfo
from ldf_adapter import backend

# this is from:
# https://docs.pytest.org/en/stable/example/parametrize.html#deferring-the-setup-of-parametrized-resources
def pytest_generate_tests(metafunc):
    if 'config' in metafunc.fixturenames:
        metafunc.parametrize('config', ['bwidm', 'local_unix'], indirect=True)

test_primary_group = 'test_primary_group'

@pytest.fixture
def config(monkeypatch, request):
    conf = globalConfig.CONFIG

    conf['ldf_adapter']['backend'] = request.param
    conf['ldf_adapter']['primary_group'] = test_primary_group

    # replace config
    monkeypatch.setattr(globalConfig, 'CONFIG', conf)
    monkeypatch.setattr(backend, '__backend__', request.param)
    return conf

@pytest.fixture
def userinfo():
    data = {'user': {
        'userinfo': {
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
            "groups": [test_primary_group],
        }
    }}

    return UserInfo(data)
