import pytest
from attr import dataclass
import pytest
import json
from typing import List
import logging

import ldf_adapter
from . import settings

logger = logging.getLogger(__name__)


@dataclass
class DbUser:
    unique_id: str
    username: str
    primary_group: str
    groups: List[str]
    pending: bool = False
    rejected: bool = False
    suspended: bool = False
    limited: bool = False


@dataclass
class DbGroup:
    name: str
    members: List[str]


class MockDB:
    """Simple user db represented as a dict"""

    def __init__(self):
        self.users = {}
        self.groups = {}

    def reset(self):
        self.users = {}
        self.groups = {}

    def add_user(self, **kwargs):
        self.users[kwargs["unique_id"]] = DbUser(**kwargs)

    def add_group(self, **kwargs):
        self.groups[kwargs["name"]] = DbGroup(**kwargs)

    def has_user(self, unique_id):
        return unique_id in self.users

    def name_taken(self, username):
        return any(user.username == username for user in self.users.values())

    def has_group(self, name):
        return name in self.groups

    def delete_user(self, unique_id):
        del self.users[unique_id]


MOCK_DB = MockDB()


class MockBackendUser:
    """Mock user for the backend"""

    def __init__(self, userinfo):
        self.unique_id = userinfo.unique_id
        if self.exists():
            self.set_username(self.get_username())
            self.primary_group = MockBackendGroup(self.get_primary_group())
        else:
            self.set_username(userinfo.username)
            self.primary_group = MockBackendGroup(userinfo.primary_group)

    def exists(self):
        return MOCK_DB.has_user(unique_id=self.unique_id)

    def name_taken(self, name):
        return MOCK_DB.name_taken(name)

    def create(self):
        MOCK_DB.add_user(
            unique_id=self.unique_id,
            username=self.username,
            primary_group=self.primary_group.name,
            groups=[self.primary_group.name],
        )
        MOCK_DB.groups[self.primary_group.name].members.append(self.username)

    def create_tostring(self):
        return json.dumps(
            {
                "unique_id": self.unique_id,
                "username": self.username,
                "primary_group": self.primary_group.name,
                "groups": [self.primary_group.name],
            }
        )

    @staticmethod
    def create_fromstring(create_cmd):
        kwargs = json.loads(create_cmd)
        MOCK_DB.add_user(**kwargs)
        MOCK_DB.groups[kwargs["primary_group"]].members.append(kwargs["username"])

    def update(self):
        pass

    def delete(self):
        MOCK_DB.delete_user(self.unique_id)

    def mod(self, supplementary_groups=None):
        if supplementary_groups is None:
            supplementary_groups_names = []
        else:
            supplementary_groups_names = [group.name for group in supplementary_groups]
        current_groups = self.get_groups()
        groups_to_add = list(set(supplementary_groups_names) - set(current_groups))
        groups_to_remove = list(set(current_groups) - set(supplementary_groups_names))

        MOCK_DB.users[self.unique_id].groups = supplementary_groups_names
        for group in groups_to_add:
            MOCK_DB.groups[group].members.append(self.username)
        for group in groups_to_remove:
            MOCK_DB.groups[group].members.remove(self.username)
        return groups_to_add, groups_to_remove

    def get_groups(self):
        return MOCK_DB.users[self.unique_id].groups

    def install_ssh_keys(self):
        pass

    def uninstall_ssh_keys(self):
        pass

    def get_username(self):
        try:
            return MOCK_DB.users[self.unique_id].username
        except KeyError:
            return None

    def set_username(self, username):
        self.username = username

    def get_primary_group(self):
        return MOCK_DB.users[self.unique_id].primary_group

    @property
    def credentials(self):
        return {}

    def is_rejected(self):
        return MOCK_DB.users[self.unique_id].rejected

    def is_suspended(self):
        return MOCK_DB.users[self.unique_id].suspended

    def is_pending(self):
        return MOCK_DB.users[self.unique_id].pending

    def is_limited(self):
        return MOCK_DB.users[self.unique_id].limited

    def suspend(self):
        MOCK_DB.users[self.unique_id].suspended = True

    def resume(self):
        MOCK_DB.users[self.unique_id].suspended = False

    def limit(self):
        MOCK_DB.users[self.unique_id].limited = True

    def unlimit(self):
        MOCK_DB.users[self.unique_id].limited = False


class MockBackendGroup:
    def __init__(self, name):
        self.name = name

    def exists(self):
        return MOCK_DB.has_group(name=self.name)

    @property
    def members(self):
        return MOCK_DB.groups[self.name].members

    def create(self):
        MOCK_DB.add_group(name=self.name, members=[])

    def create_tostring(self):
        return json.dumps({"name": self.name, "members": []})

    @staticmethod
    def create_fromstring(create_cmd):
        kwargs = json.loads(create_cmd)
        MOCK_DB.add_group(**kwargs)


@pytest.fixture(scope="function")
def user(data, monkeypatch):
    """Creates a User from provided dict"""
    with monkeypatch.context() as mp:
        mp.setattr("ldf_adapter.backend.User", MockBackendUser)
        mp.setattr("ldf_adapter.backend.Group", MockBackendGroup)
        MOCK_DB.reset()
        user = ldf_adapter.User(data)
        yield user


@pytest.mark.parametrize(
    "data,assurance_verified",
    [
        (settings.INPUT_EGI, True),
        (settings.INPUT_UNITY, True),
        (settings.INPUT_DEEP_IAM, False),
        (settings.INPUT_INDIGO_IAM, False),
        (settings.INPUT_KIT, False),
    ],
)
def test_assurance_verifier(user, assurance_verified):
    assert user.assurance_verifier()(user.data.assurance) == assurance_verified


@pytest.mark.parametrize("data", settings.ALL_INPUT)
def test_get_status(user):
    assert user.get_status().attributes == {"state": "not_deployed", "message": "No message"}


@pytest.mark.parametrize("data", [settings.INPUT_EGI])
def test_deploy_fails_no_primary_group(user):
    with pytest.raises(SystemExit):
        user.deploy()


@pytest.mark.parametrize(
    "data,username",
    [
        (settings.INPUT_UNITY, "marhar"),
        (settings.INPUT_DEEP_IAM, "marhar"),
        (settings.INPUT_INDIGO_IAM, "marhar"),
        (settings.INPUT_KIT, "lo0018"),
    ],
)
def test_deploy_name_taken(user, username, monkeypatch):
    monkeypatch.setattr(
        MockBackendUser, "name_taken", lambda x, n: True if n == "marcus" else False
    )
    assert user.deploy().attributes["state"] == "deployed"
    assert user.get_status().attributes == {"state": "deployed", "message": f"username {username}"}


@pytest.mark.parametrize(
    "data,username",
    [
        (settings.INPUT_UNITY, "marcus"),
        (settings.INPUT_DEEP_IAM, "marcus"),
        (settings.INPUT_INDIGO_IAM, "marcus"),
        (settings.INPUT_KIT, "lo0018"),
    ],
)
def test_deploy(user, username):
    result = user.deploy()
    assert result.attributes["state"] == "deployed"
    assert result.attributes["message"].startswith("User was created")
    assert user.get_status().attributes == {"state": "deployed", "message": f"username {username}"}


# test deploy_pooled_user
# test deploy groups
# test deploy group changes


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_suspend(user):
    user.deploy()
    assert user.suspend().attributes["state"] == "suspended"
    assert user.get_status().attributes["state"] == "suspended"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_suspend_not_deployed(user):
    assert user.suspend().attributes["state"] == "not_deployed"
    assert user.get_status().attributes["state"] == "not_deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_resume_after_suspend(user):
    user.deploy()
    user.suspend()
    assert user.resume().attributes["state"] == "deployed"
    assert user.get_status().attributes["state"] == "deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_resume_not_suspended(user):
    user.deploy()
    assert user.resume().attributes["state"] == "deployed"
    assert user.get_status().attributes["state"] == "deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_suspend_after_limit(user):
    user.deploy()
    user.limit()
    assert user.suspend().attributes["state"] == "suspended"
    assert user.get_status().attributes["state"] == "suspended"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_resume_after_limit(user):
    user.deploy()
    user.limit()
    assert user.resume().attributes["state"] == "limited"
    assert user.get_status().attributes["state"] == "limited"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_limit(user):
    user.deploy()
    assert user.limit().attributes["state"] == "limited"
    assert user.get_status().attributes["state"] == "limited"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_limit_not_deployed(user):
    assert user.limit().attributes["state"] == "not_deployed"
    assert user.get_status().attributes["state"] == "not_deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_unlimit(user):
    user.deploy()
    user.limit()
    assert user.unlimit().attributes["state"] == "deployed"
    assert user.get_status().attributes["state"] == "deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_unlimit_not_limited(user):
    user.deploy()
    assert user.unlimit().attributes["state"] == "deployed"
    assert user.get_status().attributes["state"] == "deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_limit_after_suspend(user):
    user.deploy()
    user.suspend()
    assert user.limit().attributes["state"] == "suspended"
    assert user.get_status().attributes["state"] == "suspended"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_unlimit_after_limit_and_suspend(user):
    user.deploy()
    user.suspend()
    user.limit()
    assert user.unlimit().attributes["state"] == "suspended"
    assert user.get_status().attributes["state"] == "suspended"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_undeploy_doesnt_exist(user):
    result = user.undeploy()
    assert result.attributes["state"] == "not_deployed"
    assert result.attributes["message"].startswith("No user for")
    assert user.get_status().attributes["state"] == "not_deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_undeploy(user):
    user.deploy()
    result = user.undeploy()
    assert result.attributes["state"] == "not_deployed"
    assert result.attributes["message"].endswith("was removed.")
    assert user.get_status().attributes["state"] == "not_deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_undeploy_after_suspend(user):
    user.deploy()
    user.suspend()
    assert user.undeploy().attributes["state"] == "not_deployed"
    assert user.get_status().attributes["state"] == "not_deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_undeploy_after_limit(user):
    user.deploy()
    user.limit()
    assert user.undeploy().attributes["state"] == "not_deployed"
    assert user.get_status().attributes["state"] == "not_deployed"


@pytest.mark.parametrize(
    "data",
    [settings.INPUT_UNITY, settings.INPUT_DEEP_IAM, settings.INPUT_INDIGO_IAM, settings.INPUT_KIT],
)
def test_deploy_exists(user):
    user.deploy()
    result = user.deploy()
    assert result.attributes["state"] == "deployed"
    assert result.attributes["message"].startswith("User already existed")
    assert user.get_status().attributes["state"] == "deployed"
