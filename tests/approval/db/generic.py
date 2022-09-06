import pytest
import mock

from ldf_adapter.approval.models import (
    PendingUser,
    PendingGroup,
    PendingMemberships,
    DeploymentState,
)
from ldf_adapter.approval.db import databases

MOCK_USER = PendingUser(
    unique_id="unique_id",
    sub="sub",
    iss="iss",
    email="email@domain",
    full_name="full_name",
    username="username",
    state=DeploymentState.PENDING,
    cmd="cmd",
    infodict={},
)

MOCK_GROUP = PendingGroup(
    name="name",
    state=DeploymentState.PENDING,
    cmd="cmd",
    infodict={},
)

MOCK_MEMBERSHIPS = PendingMemberships(
    unique_id="unique_id",
    supplementary_groups=["group1", "group2"],
    removal_groups=["group3", "group4"],
    state=DeploymentState.PENDING,
    cmd="cmd",
    infodict={},
)

MOCK_MEMBERSHIPS_UPDATED = PendingMemberships(
    unique_id="unique_id",
    supplementary_groups=["group1", "group2", "group3", "group5"],
    removal_groups=["group4"],
    state=DeploymentState.PENDING,
    cmd="cmd",
    infodict={},
)


@pytest.fixture(scope="function")
def pending_db(db_type):
    databases._builders = {}
    if db_type == "sqlite":
        with mock.patch(
            "ldf_adapter.approval.db.sqlite.CONFIG.approval.user_db_location", ":memory:"
        ):
            yield databases.get(db_type)
    else:
        yield databases.get(db_type)


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_add_user(pending_db):
    # get_user returns None
    assert pending_db.get_user(MOCK_USER.unique_id) == None
    # successful add
    assert pending_db.add_user(MOCK_USER) == True
    # get_user returns the same user
    assert pending_db.get_user(MOCK_USER.unique_id) == MOCK_USER

    # second add returns False
    assert pending_db.add_user(MOCK_USER) == False


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_remove_user(pending_db):
    # get_user returns None
    assert pending_db.get_user(MOCK_USER.unique_id) == None
    # remove user that doesn't exist
    pending_db.remove_user(MOCK_USER.unique_id)

    # remove user that does exist
    pending_db.add_user(MOCK_USER)
    pending_db.remove_user(MOCK_USER.unique_id)
    # get_user returns None
    assert pending_db.get_user(MOCK_USER.unique_id) == None


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_reject_user(pending_db):
    # get_user returns None
    assert pending_db.get_user(MOCK_USER.unique_id) == None
    # reject user that doesn't exist
    pending_db.reject_user(MOCK_USER.unique_id)

    # reject user that does exist
    pending_db.add_user(MOCK_USER)
    # get_user returns user in PENDING state
    assert pending_db.get_user(MOCK_USER.unique_id).state == DeploymentState.PENDING
    pending_db.reject_user(MOCK_USER.unique_id)
    # get_user returns user in REJECTED state
    assert pending_db.get_user(MOCK_USER.unique_id).state == DeploymentState.REJECTED


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_notify_user(pending_db):
    # get_user returns None
    assert pending_db.get_user(MOCK_USER.unique_id) == None
    # notify user that doesn't exist
    pending_db.notify_user(MOCK_USER.unique_id)

    # notify user that does exist
    pending_db.add_user(MOCK_USER)
    # get_user returns user in PENDING state
    assert pending_db.get_user(MOCK_USER.unique_id).state == DeploymentState.PENDING
    pending_db.notify_user(MOCK_USER.unique_id)
    # get_user returns user in NOTIFIED state
    assert pending_db.get_user(MOCK_USER.unique_id).state == DeploymentState.NOTIFIED


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_add_group(pending_db):
    # get_group returns None
    assert pending_db.get_group(MOCK_GROUP.name) == None
    # successful add
    assert pending_db.add_group(MOCK_GROUP) == True
    # get_group returns the same group
    assert pending_db.get_group(MOCK_GROUP.name) == MOCK_GROUP

    # second add returns False
    assert pending_db.add_group(MOCK_GROUP) == False


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_remove_group(pending_db):
    # get_group returns None
    assert pending_db.get_group(MOCK_GROUP.name) == None
    # remove group that doesn't exist
    pending_db.remove_group(MOCK_GROUP.name)

    # remove group that does exist
    pending_db.add_group(MOCK_GROUP)
    pending_db.remove_group(MOCK_GROUP.name)
    # get_group returns None
    assert pending_db.get_group(MOCK_GROUP.name) == None


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_notify_group(pending_db):
    # get_group returns None
    assert pending_db.get_group(MOCK_GROUP.name) == None
    # notify group that doesn't exist
    pending_db.notify_group(MOCK_GROUP.name)

    # notify group that does exist
    pending_db.add_group(MOCK_GROUP)
    # get_group returns group in PENDING state
    assert pending_db.get_group(MOCK_GROUP.name).state == DeploymentState.PENDING
    pending_db.notify_group(MOCK_GROUP.name)
    # get_group returns group in NOTIFIED state
    assert pending_db.get_group(MOCK_GROUP.name).state == DeploymentState.NOTIFIED


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_add_memberships(pending_db):
    # get_memberships returns None
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id) == None
    # successful add
    assert pending_db.add_memberships(MOCK_MEMBERSHIPS) == True
    # get_memberships returns the same memberships
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id) == MOCK_MEMBERSHIPS

    # second add returns False
    assert pending_db.add_memberships(MOCK_MEMBERSHIPS) == False


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_remove_memberships(pending_db):
    # get_memberships returns None
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id) == None
    # remove memberships that doesn't exist
    pending_db.remove_memberships(MOCK_MEMBERSHIPS.unique_id)

    # remove memberships that does exist
    pending_db.add_memberships(MOCK_MEMBERSHIPS)
    pending_db.remove_memberships(MOCK_MEMBERSHIPS.unique_id)
    # get_memberships returns None
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id) == None


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_notify_memberships(pending_db):
    # get_memberships returns None
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id) == None
    # notify memberships that don't exist
    pending_db.notify_memberships(MOCK_MEMBERSHIPS.unique_id)

    # notify memberships that do exist
    pending_db.add_memberships(MOCK_MEMBERSHIPS)
    # get_memberships returns memberships in PENDING state
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id).state == DeploymentState.PENDING
    pending_db.notify_memberships(MOCK_MEMBERSHIPS.unique_id)
    # get memberships returns memberships in NOTIFIED state
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id).state == DeploymentState.NOTIFIED


@pytest.mark.parametrize("db_type", ["sqlite"])
def test_update_memberships(pending_db):
    # get_memberships returns None
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id) == None
    # update memberships that don't exist: doesn't fail, but nothing changes
    pending_db.update_memberships(MOCK_MEMBERSHIPS)
    # get_memberships returns None
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id) == None

    # update memberships that do exist
    pending_db.add_memberships(MOCK_MEMBERSHIPS)
    pending_db.update_memberships(MOCK_MEMBERSHIPS_UPDATED)
    # get_memberships returns updated value
    assert pending_db.get_memberships(MOCK_MEMBERSHIPS.unique_id) == MOCK_MEMBERSHIPS_UPDATED
