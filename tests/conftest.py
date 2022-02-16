import pytest
import subprocess
import os
from pathlib import Path

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
def local_unix_user(input, exists, taken, monkeypatch):
    """Creates a backend user from provided dict data.
    input should contain:
        - userinfo, which should contain: unique_id, username, primary_group and ssh_keys.
        - new_root: the folder relative to which the user and group dbs will be stored
    If exists, it also adds an entry to the user database in /etc/passwd
    Otherwise, if taken, it adds an entry in the user db for this user's username
    """
    # save original subprocess.run for calling inside the mocked one
    old_subprocess_run = subprocess.run

    def mock_root():
        return input["new_root"]

    def mock_subprocess_run(*args, **kwargs):
        """patches calls to system utilities:
        - only for: useradd, userdel, usermod, chage
        - add prefix argument to command
        - patch pkill to do nothing
        - lett all other system calls go through
        """
        logger.debug(args)
        command = args[0]
        if command[0] in ["useradd", "userdel", "usermod", "chage"]:
            new_command = [command[0], "--prefix", mock_root()] + command[1:]
        elif command[0] == "/usr/bin/pkill":
            return None
        else:
            new_command = command
        return old_subprocess_run(new_command, *args[1:], **kwargs)

    class MockUserInfo():
        """Mocks a UserInfo object to be passed to local_unix.User
        Only a few properties are necessary:
            - unique_id
            - username
            - primary_group
            - ssh_keys
        """
        def __init__(self, data):
            self.unique_id = data["unique_id"]
            self.username = data["username"]
            self.primary_group = data["primary_group"]
            self.ssh_keys = data["ssh_keys"]
    
    monkeypatch.setitem(CONFIG['ldf_adapter'], "backend", "local_unix")
    monkeypatch.setitem(CONFIG['backend.local_unix'], "shell", "/bin/bash")
    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    backend.User.ROOT = mock_root  # type: ignore
    backend.Group.ROOT = mock_root  # type: ignore

    # init root and necessary files in new root directory (/etc/{passwd,group,shadow})
    os.makedirs(mock_root())
    os.makedirs(Path(mock_root())/"etc")
    (Path(mock_root())/"etc"/"passwd").touch()
    (Path(mock_root())/"etc"/"group").touch()
    (Path(mock_root())/"etc"/"shadow").touch()

    if exists:
        (Path(mock_root())/"etc"/"passwd").write_text(input["passwd_entry"])
    elif taken:
        (Path(mock_root())/"etc"/"passwd").write_text(input["passwd_taken"])
    (Path(mock_root())/"etc"/"group").write_text(input["group_entry"])


    # init service user from unix backend
    service_user = backend.User(MockUserInfo(input["userinfo"]))  # type:ignore

    yield service_user

    # clean up files
    old_subprocess_run(['rm', '-rf', mock_root()])


@pytest.fixture(scope="function")
def local_unix_group(input, exists, monkeypatch):
    """Creates a backend user from provided dict data.
    input should contain:
        - name: the group name (no constraints on allowed names)
        - new_root: the folder relative to which the user and group dbs will be stored
    If exists=True, also adds an entry to the group database in /etc/group
    """
    # save original subprocess.run for calling inside the mocked one
    old_subprocess_run = subprocess.run

    def mock_root():
        return input["new_root"]

    def mock_subprocess_run(*args, **kwargs):
        """patches calls to system utilities:
        - only for: groupadd
        - add prefix argument to command
        - lett all other system calls go through
        """
        logger.debug(args)
        command = args[0]
        if command[0] in ["groupadd"]:
            new_command = [command[0], "--prefix", mock_root()] + command[1:]
        else:
            new_command = command
        return old_subprocess_run(new_command, *args[1:], **kwargs)

    monkeypatch.setitem(CONFIG['ldf_adapter'], "backend", "local_unix")
    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    backend.Group.ROOT = mock_root  # type:ignore

    # init root and necessary files in new root directory (/etc/{passwd,group,shadow})
    os.makedirs(mock_root())
    os.makedirs(Path(mock_root())/"etc")
    (Path(mock_root())/"etc"/"group").touch()

    if exists:
        (Path(mock_root())/"etc"/"group").write_text(input["group_entry"])

    # init service user from unix backend
    service_group = backend.Group(input["name"])  # type:ignore

    yield service_group

    # clean up files
    old_subprocess_run(['rm', '-rf', mock_root()])



class MockBackendUserDB():
    """Simple user db represented as a dict"""
    def __init__(self):
        pass


class MockBackendUser():
    """Mock user for the backend"""
    def __init__(self):
        pass

# vim: tw=100
