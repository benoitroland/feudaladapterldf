###############################################################
# all
class User:
 | Method                                    | unix | bwidm | ldap | Mandatory |
 +-------------------------------------------+------+-------+------+-----------+
 | __init__(self, userinfo)                  | y    | y     | y    |           |
 | create(self)                              |      | y     | y    |           |
 | credentials(self)                         |      |       |      |           |
 | deactivate(self)                          |      | y     |      |           |
 | delete(self)                              | y    | y     | y    |           |
 | exists(self)                              | y    | y     | y    |           |
 | external_user_update(self, state_updates) |      | y     |      |           |
 | get_username(self)                        |      | y     |      |           |
 | install_ssh_keys(self)                    | y    | y     | y    |           |
 | is_limited(self)                          | y    |       |      |           |
 | is_pending(self)                          | y    |       |      |           |
 | is_rejected(self)                         | y    |       |      |           |
 | is_suspended(self)                        | y    |       |      |           |
 | limit(self)                               | y    |       |      |           |
 | mod(self, supplementary_groups=None)      | y    | y     | y    |           |
 | name_taken(self)                          | y    | y     | y    |           |
 | reg_info(self, json=True, **kwargs)       |      | y     |      |           |
 | resume(self)                              | y    |       |      |           |
 | set_username(self, username)              | y    | y     |      |           |
 | suspend(self)                             | y    |       |      |           |
 | uninstall_ssh_keys(self)                  | y    | y     | y    |           |
 | unlimit(self)                             | y    |       |      |           |
 | update(self)                              | y    | y     | y    |           |

class Group
 | Method                                           | unix | bwidm | ldap | Mandatory |
 +--------------------------------------------------+------+-------+------+-----------+
 | __init__(self, name)                             | y    | y     | y    |           |
 | create(self)                                     | y    | y     | y    |           |
 | delete(self)                                     | y    | y     |      |           |
 | exists(self)                                     | y    | y     | y    |           |
 | mod(self)                                        | y    | y     |      |           |
 | reg_info(self, json=True, short=False, **kwargs) |      | y     |      |           |

###############################################################
# local_unix.py
class User:
    def __init__(self, userinfo):
    def exists(self):
    def is_rejected(self):
    def is_suspended(self):
    def is_pending(self):
    def is_limited(self):
    def name_taken(self):
    def get_username(self):
    def set_username(self, username):
    def create(self):
    def update(self):
    def delete(self):
    def mod(self, supplementary_groups=None):
    def suspend(self):
    def resume(self):
    def limit(self):
    def unlimit(self):
    def install_ssh_keys(self):
    def uninstall_ssh_keys(self):
class Group:
    def __init__(self, name):
    def exists(self):
    def create(self):
    def delete(self):
    def mod(self):

###############################################################
# bwidm.py
class BwIdmConnection:
class User:
    def __init__(self, userinfo):
    def exists(self):
    def name_taken(self):
    def get_username(self):
    def set_username(self, username):
    def create(self):
    def update(self):
    def delete(self):
    def deactivate(self):
    def mod(self, supplementary_groups=None):
    def install_ssh_keys(self):
    def uninstall_ssh_keys(self):
    def external_user_update(self, state_updates):
    def reg_info(self, json=True, **kwargs):
class Group:
    def __init__(self, name):
    def exists(self):
    def create(self):
    def delete(self):
    def mod(self):
    def reg_info(self, json=True, short=False, **kwargs):

    @property
    def members(self):
        raise NotImplementedError('Do we even need this function?')

###############################################################
# ldap.py
"""Simple example backend, for documentation purposes only.
It's in the proof-of-concept state.
"""
class User:
    def __init__(self, userinfo):
    def exists(self):
    def name_taken(self):
    def create(self):
    def update(self):
    def delete(self):
    def mod(self, supplementary_groups=None):
    def install_ssh_keys(self):
    def uninstall_ssh_keys(self):

    @property
    def credentials(self):

class Group:
    """Manages the group object on the service."""
    def __init__(self, name):
    def exists(self):
    def create(self):


