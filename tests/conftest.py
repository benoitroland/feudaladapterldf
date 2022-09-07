import pytest

from ldf_adapter.userinfo import UserInfo


@pytest.fixture(scope="function")
def userinfo(data):
    """Creates a UserInfo object from provided dict"""
    userinfo = UserInfo(data)
    yield userinfo
