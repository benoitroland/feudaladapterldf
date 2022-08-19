import pytest

from ldf_adapter.userinfo import UserInfo


@pytest.fixture(scope="function")
def userinfo(data):
    """Creates a UserInfo object from provided dict"""
    userinfo = UserInfo(data)
    yield userinfo


class MockUserInfo:
    """Mocks a UserInfo object to be passed to backend user
    Only a few properties are necessary:
        - unique_id
        - username
        - primary_group
        - ssh_keys
    """

    def __init__(self, data):
        self.unique_id = data.get("unique_id")
        self.username = data.get("username")
        self.primary_group = data.get("primary_group")
        self.ssh_keys = data.get("ssh_keys")
        self.family_name = data.get("family_name")
        self.given_name = data.get("given_name")
        self.full_name = data.get("full_name")
        self.email = data.get("email")