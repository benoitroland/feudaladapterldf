"""Simple example backend, for documentation purposes only."""

class ExampleUser:
    """Manages the user object on the service."""
    def __init__(self, userinfo):
        """
        Arguments:
        userinfo -- (type: UserInfo)
        """
        pass
    def exists(self):
        """Return whether the user exists on the service.

        If this returns True,  calling `create` should have no effect or raise an error.
        """
        return bool()
    def name_taken(self, name):
        """Return wheter a given username is already taken by another user on the service.

        Should return True if the name is not available for this user (even if it is available
        for other users for some reason)
        """
        return bool()
    def create(self):
        """Create the user on the service.

        If the user already exists, do nothing or raise an error
        """
        pass
    def update(self):
        """Update all relevant information about the user on the service.

        If the user doesn't exists, behaviour is undefined.
        """
        pass
    def delete(self):
        """Delete the user on the service.

        If the user doesn't exists, do nothing or raise an error.
        """
        pass
    def mod(self, supplementary_groups=None):
        """Modify the user on the service.

        The state of the user with respect to the provided Arguments after calling this function
        should not depend on the state the user had previously.

        If the user doesn't exists, behaviour is undefined.

        Arguments:
        supplemantary_groups -- A list of groups to add the user to (type: list(ExampleGroup))
        """
        pass
    def install_ssh_keys(self):
        """Install users SSH keys on the service.

        No other SSH keys should be active after calling this function.

        If the user doesn't exists, behaviour is undefined.
        """
        pass
    def uninstall_ssh_keys(self):
        """Uninstall the users SSH keys on the service.

        This must uninstall all SSH keys installed with `install_ssh_keys`. It may uninstall SSH
        keys installed by other means.

        If the user doesn't exists, behaviour is undefined.
        """
        pass
    def get_username(self):
        """Return local username on the service.

        If the user doesn't exists, behaviour is undefined.
        """
        pass
    def set_username(self, username):
        """Set local username on the service."""
        pass
    @property
    def credentials(self):
        """Return any additional login information required to access the service after deployment.

        This should not include the installed SSH keys.

        If the user is not fully deployed, behaviour is undefined.
        """
        pass

class ExampleGroup:
    """Manages the group object on the service."""
    def __init__(self, name):
        """
        Arguments:
        name -- The name of the group
        """
        pass
    def exists(self):
        """Return whether the group already exists."""
        pass
    def create(self):
        """Create the group on the service.

        If the group already exists, behaviour is undefined.
        """
        pass
