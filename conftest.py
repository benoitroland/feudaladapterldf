# pylint: disable=global-statement

import pytest

from ldf_adapter import config as globalConfig, UserInfo
from ldf_adapter import backend as backend_module

TEST_BACKENDS = ['bwidm', 'local_unix']

# this is from:
# https://docs.pytest.org/en/stable/example/parametrize.html#deferring-the-setup-of-parametrized-resources
def pytest_generate_tests(metafunc):
    if 'backend' in metafunc.fixturenames:
        metafunc.parametrize('backend', TEST_BACKENDS, indirect=True)

test_primary_group = 'test_primary_group'

@pytest.fixture
def backend(monkeypatch, request):
    monkeypatch.setattr(backend_module, '__backend__', request.param)
    return backend_module

@pytest.fixture
def answers():
    return {
    }

@pytest.fixture
def user_data():
    return {
        'user' : {
            'userinfo': {
                "displayName": "Hardt, Marcus (SCC)",
                "eduperson_entitlement": [
                    "urn:geant:kit.edu:group:DFN-SLCS#example.org",
                    "urn:geant:kit.edu:group:LSDF-DIS#example.org",
                    "urn:geant:kit.edu:group:bwGrid#example.org",
                    "urn:geant:kit.edu:group:bwLSDF-FS#example.org",
                    "urn:geant:kit.edu:group:bwUniCluster#example.org",
                    "urn:geant:kit.edu:group:bwsyncnshare#example.org",
                    "urn:geant:kit.edu:group:bwsyncnshare-idm#example.org",
                    "urn:geant:kit.edu:group:gruppenverwalter#example.org"
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
                "iss": "https://example.org/oauth",
                "groups": [
                    "/",
                    "/DFN-SLCS",
                    "/LSDF-DIS",
                    "/bwGrid",
                    "/bwLSDF-FS",
                    "/bwUniCluster",
                    "/bwsyncnshare",
                    "/bwsyncnshare-idm",
                    "/gruppenverwalter"
                ],
            }
        },
        'answers': {
            'primary_group': 'gruppenverwalter'
        },
        'credentials': {},
    }
