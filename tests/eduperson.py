import pytest

from ldf_adapter.eduperson import Entitlement


@pytest.mark.parametrize(
    "raw,group",
    [
        ("urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority", "group"),
        ("urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de", "IMK-TRO-EWCC"),
        (
            "urn:geant:h-df.de:group:MyExampleColab#login.helmholtz-data-federation.de",
            "MyExampleColab",
        ),
        ("urn:geant:h-df.de:group:wlcg-test#login.helmholtz-data-federation.de", "wlcg-test"),
        ("urn:geant:h-df.de:group:HDF#login.helmholtz-data-federation.de", "HDF"),
    ],
)
def test_entitlement_group(raw, group):
    ent = Entitlement(raw)
    assert ent.group == group


@pytest.mark.parametrize(
    "raw,subgroup",
    [
        (
            "urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority",
            ["subgroup1", "subgroup2"],
        ),
        ("urn:nid:namespace:group:group:subgroup:role=admin#authority", ["subgroup"]),
        ("urn:nid:namespace:group:group:role=admin#authority", []),
    ],
)
def test_entitlement_subgroup(raw, subgroup):
    ent = Entitlement(raw)
    assert ent.subgroups == subgroup


@pytest.mark.parametrize(
    "raw,full_namespace",
    [
        ("urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority", ["namespace"]),
        (
            "urn:nid:ns1:ns2:ns3:group:group:subgroup1:subgroup2:role=admin#authority",
            ["ns1", "ns2", "ns3"],
        ),
        ("urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de", ["h-df.de"]),
    ],
)
def test_entitlement_full_namespace(raw, full_namespace):
    ent = Entitlement(raw)
    assert ent.full_namespace == full_namespace


@pytest.mark.parametrize(
    "raw,namespace_id",
    [
        ("urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority", "nid"),
        ("urn:nid:ns1:ns2:ns3:group:group:subgroup1:subgroup2:role=admin#authority", "nid"),
        ("urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de", "geant"),
    ],
)
def test_entitlement_namespace_id(raw, namespace_id):
    ent = Entitlement(raw)
    assert ent.namespace_id == namespace_id


@pytest.mark.parametrize(
    "raw,delegated_namespace",
    [
        ("urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority", "namespace"),
        ("urn:nid:ns1:ns2:ns3:group:group:subgroup1:subgroup2:role=admin#authority", "ns1"),
        ("urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de", "h-df.de"),
    ],
)
def test_entitlement_delegated_namespace(raw, delegated_namespace):
    ent = Entitlement(raw)
    assert ent.delegated_namespace == delegated_namespace


@pytest.mark.parametrize(
    "raw,subnamespaces",
    [
        ("urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority", []),
        (
            "urn:nid:ns1:ns2:ns3:group:group:subgroup1:subgroup2:role=admin#authority",
            ["ns2", "ns3"],
        ),
        ("urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de", []),
    ],
)
def test_entitlement_subnamespaces(raw, subnamespaces):
    ent = Entitlement(raw)
    assert ent.subnamespaces == subnamespaces


@pytest.mark.parametrize(
    "raw,role",
    [
        ("urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority", "admin"),
        ("urn:nid:namespace:group:group:subgroup1:subgroup2:role=user#authority", "user"),
        ("urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de", None),
    ],
)
def test_entitlement_role(raw, role):
    ent = Entitlement(raw)
    assert ent.role == role


@pytest.mark.parametrize(
    "raw,group_authority",
    [
        ("urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority", "authority"),
        ("urn:nid:ns1:ns2:ns3:group:group:subgroup1:subgroup2:role=admin#.", "."),
        (
            "urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de",
            "login.helmholtz-data-federation.de",
        ),
    ],
)
def test_entitlement_group_authority(raw, group_authority):
    ent = Entitlement(raw)
    assert ent.group_authority == group_authority


@pytest.mark.parametrize(
    "raw",
    [
        "urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority",  # all fields
        "urn:nid:namespace:group:group:subgroup1:subgroup2#authority",  # no role
        "urn:nid:namespace:group:group:role=admin#authority",  # no subgroups
        "urn:geant:h-df.de:group:IMK-TRO-EWCC#login.helmholtz-data-federation.de",
        "urn:geant:h-df.de:group:MyExampleColab#login.helmholtz-data-federation.de",
        "urn:geant:h-df.de:group:wlcg-test#login.helmholtz-data-federation.de",
        "urn:geant:h-df.de:group:HDF#login.helmholtz-data-federation.de",
    ],
)
def test_entitlement_valid(raw):
    ent = Entitlement(raw)
    assert repr(ent) == raw


@pytest.mark.parametrize(
    "raw",
    [
        "nid:namespace:group:group:subgroup1:subgroup2:role=admin#authority",
        "urn:nid:namespace:group::subgroup1:subgroup2:role=admin#authority",
        "urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin#",
        "urn:group:group:subgroup1:subgroup2:role=admin#authority",
        "urn:nid:namespace:subgroup1:subgroup2:role=admin#authority",
        "urn:nid:namespace:group:group:subgroup1:subgroup2:role=admin",
        "urn:nid:namespace:group:group:subgroup1:subgroup2",
        "urn:nid:namespace:group:group:subgroup1",
        "urn:nid:namespace:group:group",
        "urn:nid:namespace:group",
        "urn:nid:namespace",
        "urn:nid",
        "anything",
    ],
)
def test_entitlement_invalid(raw):
    with pytest.raises(ValueError):
        Entitlement(raw)
