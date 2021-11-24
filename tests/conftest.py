import pytest
import subprocess
import inspect

from ldf_adapter import UserInfo, User, backend, CONFIG
import logging

logger = logging.getLogger(__name__)

@pytest.fixture(scope="function")
def userinfo(data):
    """Creates a UserInfo object from provided dict"""
    userinfo = UserInfo(data)
    yield userinfo


@pytest.fixture(scope="function")
def user(data, monkeypatch):
    """Creates a User from provided dict"""
    # monkeypatch.setitem(CONFIG['ldf_adapter'], "backend", "local_unix")
    user = User(data)
    yield user


@pytest.fixture(scope="function")
def local_unix_backend(data):
    """Creates a backend user from provided dict"""
    monkeypatch.setitem(CONFIG['ldf_adapter'], "backend", "local_unix")
    service_user = backend.User(UserInfo(data))
    yield service_user


class BackendUserDBMocker():
    """Simple user db represented as a dict"""
    def __init__(self):
        pass


class BackendUserMocker():
    """Mock user for the backend"""
    def __init__(self):
        pass