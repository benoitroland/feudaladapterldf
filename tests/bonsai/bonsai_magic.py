# tox -c tox_bonsai.ini -e [report-info,report-debug]
import pytest
import os, re
from unittest.mock import MagicMock, patch
from ldf_adapter.backend.bonsai_ldap import BonsaiLDAPClient, User, Group, LDAPEntry
from ldf_adapter.backend.bonsai_ldap import Mode
from ldf_adapter.results import Rejection, Failure
from bonsai import TimeoutError, LDAPError
import logging

logger = logging.getLogger(__name__)

class UserInfo:
    def __init__(self, data):
        self.unique_id = data.get("unique_id")
        self.username = data.get("username")
        self.primary_group = data.get("primary_group")
        self.ssh_keys = data.get("ssh_keys")
        self.family_name = data.get("family_name")
        self.given_name = data.get("given_name")
        self.full_name = data.get("full_name")
        self.email = data.get("email")

    def get(self, key, default=None):
        return getattr(self, key, default)

def wait():
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    if log_level.upper() == "DEBUG":
        input("Press ENTER to continue")

def entry_error(*args, **kwargs):
    entry = MagicMock()
    entry.modify.side_effect = LDAPError("LDAP backend failure.")
    return entry

def entry_exception(*args, **kwargs):
    entry = MagicMock()
    entry.modify.side_effect = Exception("LDAP backend failure.")
    return entry

def filter_entry(ldap_entry, key, filter):
    entry_found = []
    if filter:
        for entry in ldap_entry:

            entry_key = entry.get(key)
            if not isinstance(entry_key, list):
                entry_key= [entry_key]

            for value in entry_key:
                if value == filter:
                    entry_found.append(entry)
    else:
        entry_found = ldap_entry
    return entry_found

def filter_attribute(entry_found, attrlist):
    search_result = []
    for entry in entry_found:
        result = {}
        for attr in attrlist:
            if attr in entry:
                result[attr] = entry[attr]
        if result:
            search_result.append(result)

    return search_result

@pytest.fixture
def bonsai_magic(monkeypatch, request, mode, ldap_user_entry, ldap_group_entry):

    # parameters
    params = getattr(request.node, "callspec", None)
    params = params.params if params else {}

    # uid and gid range
    uid_min = params.get("uid_min", 1000)
    uid_max = params.get("uid_max", 2000)

    gid_min = params.get("gid_min", 1000)
    gid_max = params.get("gid_max", 2000)

    # to reproduce next uid and next gid
    uid_num_counter = {"value": uid_min}
    gid_num_counter = {"value": gid_min}

    # filter for user
    def filter_user(ldap_user_entry, attrlist, filter_exp):

        # to reproduce next uid
        if "uidNext" in filter_exp:
            uid_num = uid_num_counter["value"]
            uid_num_counter["value"] += 1
            return [{"uidNumber": uid_num}]

        entry_found = []

        # filter uidNumber
        match_uidNumber = re.search(r"\(uidNumber=(\d+)\)", filter_exp)
        filter_uidNumber = int(match_uidNumber.group(1)) if match_uidNumber else None
        entry_found = filter_entry(ldap_user_entry, "uidNumber", filter_uidNumber)
        if not entry_found:
            return []

        # to mimic that the next uidNumber is free
        if filter_uidNumber and not attrlist:
            return []

        # filter gecos
        match_gecos = re.search(r"\(gecos=([^)]+)\)", filter_exp)
        filter_gecos = match_gecos.group(1) if match_gecos else None
        entry_found = filter_entry(ldap_user_entry, "gecos", filter_gecos)
        if not entry_found:
            return []

        # filter uid
        match_uid = re.search(r"\(uid=([^)]+)\)", filter_exp)
        filter_uid = match_uid.group(1) if match_uid else None
        entry_found = filter_entry(ldap_user_entry, "name", filter_uid)
        if not entry_found:
            return []

        # no attribute requested
        if not attrlist:
            return entry_found

        # attribute requested
        search_result = []
        search_result = filter_attribute(entry_found, attrlist)
        return search_result

    # filter for group
    def filter_group(ldap_group_entry, ldap_user_entry, attrlist, filter_exp):

        # to reproduce next gid
        if "gidNext" in filter_exp:
            gid_num = gid_num_counter["value"]
            gid_num_counter["value"] += 1
            return [{"gidNumber": gid_num}]

        entry_found = []

        # filter gidNumber
        match_gidNumber = re.search(r"\(gidNumber=(\d+)\)", filter_exp)
        filter_gidNumber = int(match_gidNumber.group(1)) if match_gidNumber else None
        entry_found = filter_entry(ldap_group_entry, "gidNumber", filter_gidNumber)
        if not entry_found:
            return []

        # to mimic that the next gidNumber is free
        if filter_gidNumber and not attrlist:
            return []

        # filter cn
        match_cn = re.search(r"\(cn=([^)]+)\)", filter_exp)
        filter_cn = match_cn.group(1) if match_cn else None
        entry_found = filter_entry(ldap_group_entry, "cn", filter_cn)
        if not entry_found:
            return []

        # filter memberUid
        match_memberUid = re.search(r"\(memberUid=([^)]+)\)", filter_exp)
        filter_memberUid  = match_memberUid.group(1) if match_memberUid else None
        entry_found = filter_entry(ldap_group_entry, "memberUid", filter_memberUid)
        if not entry_found:
            return []

        # no attribute requested
        if not attrlist:
            return entry_found

        # attribute requested
        search_result = []
        search_result = filter_attribute(entry_found, attrlist)
        return search_result

    # LDAPConnection
    connection_mock = MagicMock()

    # LDAPConnection search
    def search_mock(base, scope=None, filter_exp=None, attrlist=None):

        if ldap_user_entry and "ou=users" in base:
            return filter_user(ldap_user_entry, attrlist, filter_exp)

        if ldap_group_entry and "ou=groups" in base:
            return filter_group(ldap_group_entry, ldap_user_entry, attrlist, filter_exp)

        return []

    connection_mock.search.side_effect = search_mock

    # LDAPConnection add
    connection_mock.add.return_value = True

    # LDAPConnection delete
    connection_mock.delete.return_value = True

    # Pool spawn context manager
    spawn_cm_mock = MagicMock()
    spawn_cm_mock.__enter__.return_value = connection_mock
    spawn_cm_mock.__exit__.return_value = None

    # ThreadedConnectionPool
    pool_mock = MagicMock()
    pool_mock.spawn.return_value = spawn_cm_mock
    monkeypatch.setattr("ldf_adapter.backend.bonsai_ldap.ThreadedConnectionPool", MagicMock(return_value=pool_mock))

    # LDAPClient
    ldap_client_mock = MagicMock()

    def set_credentials_side_effect(*args, **kwargs):
        return None

    ldap_client_mock.set_credentials.side_effect = set_credentials_side_effect

    monkeypatch.setattr("ldf_adapter.backend.bonsai_ldap.LDAPClient", MagicMock(return_value=ldap_client_mock))

    # BonsaiLDAPClient.pool
    monkeypatch.setattr("ldf_adapter.backend.bonsai_ldap.BonsaiLDAPClient.pool", None)

    # BonsaiLDAPClient initialisation
    init_client = BonsaiLDAPClient.__init__
    def init_mock(self, *args, **kwargs):
        init_client(self, *args, **kwargs)
        self.mode = Mode.from_str(mode)
        self.uid_min = uid_min
        self.uid_max = uid_max
        self.gid_min = gid_min
        self.gid_max = gid_max
        self._init_nextuidgid()

    monkeypatch.setattr("ldf_adapter.backend.bonsai_ldap.BonsaiLDAPClient.__init__", init_mock)

    # LDAPEntry
    def ldap_entry_mock(dn=None, conn=None):
        entry_mock = MagicMock()

        entry_mock.change_attribute.return_value = None
        entry_mock.modify.return_value = True

        entry_mock.dn = dn
        entry_mock._attrs = {}

        def setitem(key, value):
            entry_mock._attrs[key] = value

        def getitem(key):
            return entry_mock._attrs.get(key)

        entry_mock.__setitem__.side_effect = setitem
        entry_mock.__getitem__.side_effect = getitem

        return entry_mock

    ldap_entry_class_mock = MagicMock()
    ldap_entry_class_mock.side_effect = ldap_entry_mock

    monkeypatch.setattr("ldf_adapter.backend.bonsai_ldap.LDAPEntry",ldap_entry_class_mock)

    return {"connection": connection_mock,
            "entry": ldap_entry_class_mock,
    }
