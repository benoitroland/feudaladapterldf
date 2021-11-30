import pytest
import subprocess
import inspect
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
        - only for: useradd, userdel, usermod, chage, groupadd
        - add sudo command for chroot option
        - add prefix argument to command
        - patch pkill to do nothing
        - lett all other system calls go through
        """
        logger.debug(args)
        command = args[0]
        if command[0] in ["useradd", "userdel", "usermod", "chage", "groupadd"]:
            new_command = ["sudo", command[0], "--prefix", mock_root()] + command[1:]
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
    backend.User.ROOT = mock_root
    backend.Group.ROOT = mock_root

    # init root and necessary files in new root directory (/etc/{passwd,group,shadow})
    os.mkdir(mock_root())
    os.mkdir(Path(mock_root())/"etc")
    (Path(mock_root())/"etc"/"passwd").touch()
    (Path(mock_root())/"etc"/"group").touch()
    (Path(mock_root())/"etc"/"shadow").touch()
    (Path(mock_root())/"etc"/"passwd").write_text("root:x:0:0::/root:/bin/bash\n")

    if exists:
        (Path(mock_root())/"etc"/"passwd").write_text(input["passwd_entry"])
    elif taken:
        (Path(mock_root())/"etc"/"passwd").write_text(input["passwd_taken"])


    # init service user from unix backend
    service_user = backend.User(MockUserInfo(input["userinfo"]))

    yield service_user

    # clean up files
    old_subprocess_run(['sudo', 'rm', '-rf', mock_root()])


class MockBackendUserDB():
    """Simple user db represented as a dict"""
    def __init__(self):
        pass


class MockBackendUser():
    """Mock user for the backend"""
    def __init__(self):
        pass