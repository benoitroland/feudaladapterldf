"""test name_generators"""
import pytest
from ldf_adapter import name_generators

marcus_userinfo_json = {
    "state_target": "deployed",
    "user": {
        "userinfo": {
            "acr": "https://aai.egi.eu/LoA#Substantial",
            "eduperson_assurance": ["https://aai.egi.eu/LoA#Substantial"],
            "eduperson_entitlement": [
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@saps-vo.i3m.upv.es",
                "urn:mace:egi.eu:group:EOServices-vo.indra.es:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@saps-vo.i3m.upv.es",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@mteam.data.kit.edu",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@cryoem.instruct-eric.eu",
                "urn:mace:egi.eu:group:covid19.eosc-synergy.eu:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@worsica.vo.incd.pt",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@mswss.ui.savba.sk",
                "urn:mace:egi.eu:aai.egi.eu:member@umsa.cerit-sc.cz",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@o3as.data.kit.edu",
                "urn:mace:egi.eu:group:eosc-synergy.eu:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@covid19.eosc-synergy.eu",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@umsa.cerit-sc.cz",
                "urn:mace:egi.eu:group:covid19.eosc-synergy.eu:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:cryoem.instruct-eric.eu:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@umsa.cerit-sc.cz",
                "urn:mace:egi.eu:group:umsa.cerit-sc.cz:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@o3as.data.kit.edu",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@mswss.ui.savba.sk",
                "urn:mace:egi.eu:group:mteam.data.kit.edu:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:saps-vo.i3m.upv.es:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:group:umsa.cerit-sc.cz:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:group:goc.egi.eu:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:group:goc.egi.eu:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:saps-vo.i3m.upv.es:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@worsica.vo.incd.pt",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@covid19.eosc-synergy.eu",
                "urn:mace:egi.eu:group:cryoem.instruct-eric.eu:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:group:EOServices-vo.indra.es:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@EOServices-vo.indra.es",
                "urn:mace:egi.eu:group:covid19.eosc-synergy.eu:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:owner@perfmon",
                "urn:mace:egi.eu:group:o3as.data.kit.edu:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:registry:perfmon:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:group:worsica.vo.incd.pt:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:eosc-synergy.eu:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:group:cryoem.instruct-eric.eu:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:group:saps-vo.i3m.upv.es:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@goc.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@o3as.data.kit.edu",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@cryoem.instruct-eric.eu",
                "urn:mace:egi.eu:group:umsa.cerit-sc.cz:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@perfmon.m.d.k.e",
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@eosc-synergy.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@saps-vo.i3m.upv.es",
                "urn:mace:egi.eu:group:o3as.data.kit.edu:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:group:mswss.ui.savba.sk:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:saps-vo.i3m.upv.es:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:registry:perfmon:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@eosc-synergy.eu",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@covid19.eosc-synergy.eu",
                "urn:mace:egi.eu:group:EOServices-vo.indra.es:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@mteam.data.kit.edu",
                "urn:mace:egi.eu:group:worsica.vo.incd.pt:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:group:o3as.data.kit.edu:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@mteam.data.kit.edu",
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@covid19.eosc-synergy.eu",
                "urn:mace:egi.eu:group:mteam.data.kit.edu:perfmon.m.d.k.e:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@EOServices-vo.indra.es",
                "urn:mace:egi.eu:group:mswss.ui.savba.sk:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:group:mteam.data.kit.edu:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@mswss.ui.savba.sk",
                "urn:mace:egi.eu:group:eosc-synergy.eu:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:EOServices-vo.indra.es:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:group:mswss.ui.savba.sk:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@eosc-synergy.eu",
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@umsa.cerit-sc.cz",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@saps-vo.i3m.upv.es",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@EOServices-vo.indra.es",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@perfmon.m.d.k.e",
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@EOServices-vo.indra.es",
                "urn:mace:egi.eu:aai.egi.eu:admins:member@eosc-synergy.eu",
                "urn:mace:egi.eu:group:umsa.cerit-sc.cz:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:group:o3as.data.kit.edu:role=vm_operator#aai.egi.eu",
                "urn:mace:egi.eu:group:covid19.eosc-synergy.eu:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:vm_operator@goc.egi.eu",
                "urn:mace:egi.eu:group:cryoem.instruct-eric.eu:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@cryoem.instruct-eric.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@perfmon",
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@mteam.data.kit.edu",
                "urn:mace:egi.eu:group:eosc-synergy.eu:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:admins:owner@o3as.data.kit.edu",
                "urn:mace:egi.eu:group:mteam.data.kit.edu:perfmon.m.d.k.e:role=member#aai.egi.eu",
                "urn:mace:egi.eu:group:mteam.data.kit.edu:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:group:mswss.ui.savba.sk:admins:role=owner#aai.egi.eu",
                "urn:mace:egi.eu:group:mteam.data.kit.edu:admins:role=member#aai.egi.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@cryoem.instruct-eric.eu",
                "urn:mace:egi.eu:aai.egi.eu:member@mswss.ui.savba.sk",
            ],
            "eduperson_scoped_affiliation": ["faculty@KIT"],
            "eduperson_unique_id": "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756@egi.eu",
            "email": "hardt@kit.edu",
            "email_verified": True,
            "family_name": "Hardt",
            "given_name": "Marcus",
            "name": "Marcus Hardt",
            "preferred_username": "mhardt",
            "sub": "d7a53cbe3e966c53ac64fde7355956560282158ecac8f3d2c770b474862f4756@egi.eu",
            "iss": "https://aai.egi.eu/oidc/",
            "voperson_verified_email": ["hardt@kit.edu"],
        }
    },
}


@pytest.mark.parametrize("data", [marcus_userinfo_json])
def test_friendly_name(userinfo):
    """test friendly name generator with provided userinfo json
    Depends on the hardcoded strategies"""
    name_generator = name_generators.FriendlyNameGenerator(userinfo=userinfo)
    name = name_generator.suggest_name()
    assert name == "mhardt"

    name = name_generator.suggest_name()
    assert name == "marcus"


@pytest.mark.parametrize("data", [marcus_userinfo_json])
def test_friendly_name_again(userinfo):
    """test friendly name generator with provided userinfo json
    run for a 2nd time, to verify internal state works
    Depends on the hardcoded strategies"""
    name_generator = name_generators.FriendlyNameGenerator(userinfo)
    name = name_generator.suggest_name()
    assert name == "mhardt"

    name = name_generator.suggest_name()
    assert name == "marcus"


def test_pooled_name_one():
    """test pooled name generator with provided userinfo json
    this depends on the shipped configfile
    """
    name_generator = name_generators.PooledNameGenerator("pytest")
    name = name_generator.suggest_name()
    assert name == "pytest001"

    name = name_generator.suggest_name()
    assert name == "pytest002"


def test_pooled_name():
    """test pooled name generator with provided userinfo json
    this depends on the shipped configfile
    """
    name_generator = name_generators.PooledNameGenerator(pool_prefix="pytest")
    name = name_generator.suggest_name()
    assert name == "pytest001"

    name = name_generator.suggest_name()
    assert name == "pytest002"


@pytest.mark.parametrize("data", [marcus_userinfo_json])
def test_new_friendly(userinfo):
    """test new invocation method"""
    name_generator = name_generators.NameGenerator("friendly", userinfo=userinfo)
    name = name_generator.suggest_name()
    assert name == "mhardt"

    name = name_generator.suggest_name()
    assert name == "marcus"


def test_new_pooled():
    """test new invocation method"""
    name_generator = name_generators.NameGenerator("pooled", pool_prefix="pytest")
    name = name_generator.suggest_name()
    assert name == "pytest001"

    name = name_generator.suggest_name()
    assert name == "pytest002"


@pytest.mark.parametrize("data", [marcus_userinfo_json])
def test_new_friendly_simpler(userinfo):
    """test new invocation method"""
    name_generator = name_generators.NameGenerator("friendly", userinfo=userinfo)
    name = name_generator.suggest_name()
    assert name == "mhardt"

    name = name_generator.suggest_name()
    assert name == "marcus"


def test_new_pooled_simpler():
    """test new invocation method"""
    name_generator = name_generators.NameGenerator("pooled", pool_prefix="pytest")
    name = name_generator.suggest_name()
    assert name == "pytest001"

    name = name_generator.suggest_name()
    assert name == "pytest002"


@pytest.mark.parametrize("data", [marcus_userinfo_json])
def test_new_pooled_generic(userinfo):
    """test new invocation method"""
    name_generator = name_generators.NameGenerator(
        "friendly", userinfo=userinfo, pool_prefix="pytest"
    )
    name = name_generator.suggest_name()
    assert name == "mhardt"

    name_generator = name_generators.NameGenerator(
        "pooled", userinfo=userinfo, pool_prefix="pytest"
    )
    name = name_generator.suggest_name()
    assert name == "pytest001"


@pytest.mark.parametrize("data", [marcus_userinfo_json])
def test_multiple_calls(userinfo):
    """test returning the tried names"""
    name_generator = name_generators.NameGenerator(
        "friendly", userinfo=userinfo, pool_prefix="pytest"
    )
    old_name = ""
    for i in range(0, 17):
        new_name = name_generator.suggest_name()
        assert old_name != new_name
        old_name = new_name
    tried_names = name_generator.tried_names()
    print(f"TRIED NAMES:{tried_names}")
    assert isinstance(tried_names, list)


@pytest.mark.parametrize("data", [marcus_userinfo_json])
def test_tried_names_friendly(userinfo):
    """test returning the tried names"""
    name_generator = name_generators.NameGenerator(
        "friendly", userinfo=userinfo, pool_prefix="pytest"
    )
    tried_names = name_generator.tried_names()
    assert isinstance(tried_names, list)


@pytest.mark.parametrize("data", [marcus_userinfo_json])
def test_tried_names_pooled(userinfo):
    """test returning the tried names"""
    name_generator = name_generators.NameGenerator(
        "pooled", userinfo=userinfo, pool_prefix="pytest"
    )
    tried_names = name_generator.tried_names()
    assert tried_names == []


# vim: tw=100
