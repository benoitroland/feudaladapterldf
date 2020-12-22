"""Simple example backend, for documentation purposes only.
It's in the proof-of-concept state.
"""


import logging

# See https://ldap3.readthedocs.io/en/latest/operations.html
from ldap3 import Server, Connection, ALL, BASE, MODIFY_REPLACE, MODIFY_DELETE

logger = logging.getLogger(__name__)

class User:
    """Manages the user object on the service."""
    def __init__(self, userinfo):
        """
        Arguments:
        userinfo -- (type: UserInfo)
        """
        self.primary_group = Group(userinfo.primary_group)
        self.userinfo = userinfo

        s = Server('localhost', get_info=ALL)  # define an unsecure LDAP server
        self.connection = Connection(s, user='cn=admin,dc=foo,dc=ka,dc=bw-cloud-instance,dc=org', password='foobar123')
        self.connection.bind()

    def exists(self):
        logger.info(F"Uros: exist: {self.userinfo.userinfo['eduperson_targeted_id']}")
        """Return whether the user exists on the service.

        If this returns True,  calling `create` should have no effect or raise an error.
        """
        users_name = self.userinfo.userinfo['eduperson_targeted_id'][0]
        return self.connection.search(
            #f"cn={self.userinfo.username},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
            f"cn={users_name},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
            '(objectClass=*)',
            search_scope=BASE
        )

    def name_taken(self):
        """Return wheter the username is already taken by another user on the service.

        Should return True if the name is available for this user (even if it is unavailable
        for other users for some reason)
        """
        return bool()
    def create(self):
        """Create the user on the service.

        If the user already exists, do nothing or raise an error
        """
        users_name = self.userinfo.userinfo['eduperson_targeted_id'][0]
        self.connection.add(
            #f"cn={self.userinfo.username},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
            f"cn={users_name},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
            attributes={
                #'objectClass':  ['inetOrgPerson'],
                #'objectClass':  ['inetOrgPerson', 'ldapPublicKey'],
                'objectClass':  ['inetOrgPerson', 'ldapPublicKey','eduPerson'],
                'sn': self.userinfo.family_name,
                'givenName': self.userinfo.given_name,
                'mail': self.userinfo.email,
                'eduPersonPrincipalName': self.userinfo.userinfo['eduperson_principal_name'],
                'eduPersonEntitlement': self.userinfo.userinfo['eduperson_entitlement']
                #'sshPublicKey' = self.userinfo.ssh_keys[0]['value'] 
            })

    def update(self):
        """Update all relevant information about the user on the service.

        If the user doesn't exists, behavour is undefined.
        """
        #users_name = self.userinfo.userinfo['eduperson_targeted_id'][0]
        #self.connection.modify(
        #    #f"cn={self.userinfo.username},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
        #    f"cn={users_name},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
        #    {
        #        #'sn': self.userinfo.family_name,
        #        'givenName': [(MODIFY_REPLACE, [self.userinfo.given_name])],
        #        #'mail': self.userinfo.email,
        #        #'sshPublicKey': [(MODIFY_REPLACE, [SSHKey])],
        #        #'eduPersonPrincipalName': [(MODIFY_REPLACE, [self.userinfo.userinfo['eduperson_principal_name']])],
        #        #'eduPersonEntitlement': [(MODIFY_REPLACE, [self.userinfo.userinfo['eduperson_entitlement']])],
        #        }
        #    )
        pass

    def delete(self):
        """Delete the user on the service.

        If the user doesn't exists, do nothing or raise an error.
        """
        users_name = self.userinfo.userinfo['eduperson_targeted_id'][0]
        #self.connection.delete(f"cn={self.userinfo.username},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org")
        self.connection.delete(f"cn={users_name},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org")

    def mod(self, supplementary_groups=None):
        """Modify the user on the service.

        The state of the user with respect to the provided Arguments after calling this function
        should not depend on the state the user had previously.

        If the user doesn't exists, behavour is undefined.

        Arguments:
        supplemantary_groups -- A list of groups to add the user to (type: list(Group))
        """
        #users_name = self.userinfo.userinfo['eduperson_targeted_id'][0]
        #self.connection.modify(
        #    #f"cn={self.userinfo.username},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
        #    f"cn={users_name},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
        #    {
        #        #'sn': self.userinfo.family_name,
        #        'givenName': [(MODIFY_REPLACE, [self.userinfo.given_name])],
        #        #'mail': self.userinfo.email,
        #        #'sshPublicKey': [(MODIFY_REPLACE, [SSHKey])],
        #        #'eduPersonPrincipalName': [(MODIFY_REPLACE, [self.userinfo.userinfo['eduperson_principal_name']])],
        #        #'eduPersonEntitlement': [(MODIFY_REPLACE, [self.userinfo.userinfo['eduperson_entitlement']])],
        #        }
        #    )
        pass
    def install_ssh_keys(self):
        logger.info(F"Uros: key: {self.userinfo.ssh_keys[0]['value']}")
        SSHKey = self.userinfo.ssh_keys[0]['value'] 
        users_name = self.userinfo.userinfo['eduperson_targeted_id'][0]
        self.connection.modify(
            #f"cn={self.userinfo.username},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
            f"cn={users_name},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
            {
                #'sn': self.userinfo.family_name,
                #'givenName': self.userinfo.given_name,
                #'mail': self.userinfo.email,
                'sshPublicKey': [(MODIFY_REPLACE, [SSHKey])],
                }
            )
        """Install users SSH keys on the service.

        No other SSH keys should be active after calling this function.

        If the user doesn't exists, behaviour is undefined.
        """
        pass
    def uninstall_ssh_keys(self):
        logger.info(F"Uros delete: key: {self.userinfo.ssh_keys[0]['value']}")
        SSHKey = self.userinfo.ssh_keys[0]['value'] 
        users_name = self.userinfo.userinfo['eduperson_targeted_id'][0]
        self.connection.modify(
            #f"cn={self.userinfo.username},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
            f"cn={users_name},dc=foo,dc=ka,dc=bw-cloud-instance,dc=org",
            {
                'sshPublicKey': [(MODIFY_DELETE, [SSHKey])],
                }
            )
        """Uninstall the users SSH keys on the service.

        This must uninstall all SSH keys installed with `install_ssh_keys`. It may uninstall SSH
        keys installed by other means.

        If the user doesn't exists, behaviour is undefined.
        """
        pass
    @property
    def credentials(self):
        """Return any additional login information required to access the service after deployment.

        This should not include the installed SSH keys.

        If the user is not fully deployed, behaviour is undefined.
        """
        return {}

class Group:
    """Manages the group object on the service."""
    def __init__(self, name):
        """
        Arguments:
        name -- The name of the group
        """
        self.name = name
    def exists(self):
        """Return whether the group already exists."""
        pass
    def create(self):
        """Create the group on the service.

        If the group already exists, behaviour is undefined.
        """
        pass
