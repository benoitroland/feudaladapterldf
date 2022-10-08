"""Generic backend User and Group, to be implemented by all backends."""
from abc import ABC, abstractmethod


class User(ABC):
    """Manages the user object on the service."""

    def __init__(self, userinfo):
        """
        Arguments:
        userinfo -- (type: UserInfo)
        """
        pass

    @abstractmethod
    def exists(self):
        """Return whether the user exists on the service.

        If this returns True,  calling `create` should have no effect or raise an error.
        """
        return bool()

    @abstractmethod
    def name_taken(self, name):
        """Return whether a given username is already taken by another user on the service.

        Should return True if the name is not available for this user (even if it is available
        for other users for some reason)
        """
        return bool()

    @abstractmethod
    def create(self):
        """Create the user on the service.

        If the user already exists, do nothing or raise an error
        """
        pass

    @abstractmethod
    def create_tostring(self):
        """String representation of commands needed to deploy a new user.

        Returns:
            str: backend specific string containing user creation command(s)
        """
        pass

    # def create_fromstring(self, create_cmd: str):
    #     """Create a new user from string representation of commands needed to deploy a new user.
    #     Optional, only needed if the backend supports it.
    #
    #     Arguments:
    #         create_cmd str: backend specific string containing user creation command(s)
    #     """
    #     pass

    @abstractmethod
    def update(self):
        """Update all relevant information about the user on the service.

        If the user doesn't exists, behaviour is undefined.
        """
        pass

    @abstractmethod
    def delete(self):
        """Delete the user on the service.

        If the user doesn't exists, do nothing or raise an error.
        """
        pass

    @abstractmethod
    def mod(self, supplementary_groups=None):
        """Modify the user on the service.

        After this operation, the user will only be part of the provided groups.

        If the user doesn't exists, behaviour is undefined.

        Arguments:
        supplementary_groups -- A list of groups the user must be part of (type: list(Group))

        Returns:
        two lists of groups: the groups the user was added to and the groups the user was removed from
        """
        pass

    @abstractmethod
    def mod_tostring(self, supplementary_groups=None):
        """String representation of commands needed to modify a user to be added and removed from given groups.

        Arguments:
            supplementary_groups (list[Group], optional): the list of groups the user must be part of. Defaults to None.

        Returns:
            str: backend specific string containing all user modifications
        """
        pass

    # def mod_fromstring(self, mod_cmd: str):
    #     """Modify a user using string representation of commands needed to add & remove user to groups.
    #     Optional, only needed if the backend supports it.
    #
    #     Arguments:
    #         mod_cmd str: backend specific string containing all user modification command(s)
    #     """
    #     pass

    @abstractmethod
    def get_groups(self):
        """Get a list of names of all service groups that the user belongs to.

        If the user doesn't exist, behaviour is undefined.
        """
        pass

    @abstractmethod
    def install_ssh_keys(self):
        """Install users SSH keys on the service.

        No other SSH keys should be active after calling this function.

        If the user doesn't exists, behaviour is undefined.
        """
        pass

    @abstractmethod
    def uninstall_ssh_keys(self):
        """Uninstall the users SSH keys on the service.

        This must uninstall all SSH keys installed with `install_ssh_keys`. It may uninstall SSH
        keys installed by other means.

        If the user doesn't exists, behaviour is undefined.
        """
        pass

    @abstractmethod
    def get_username(self):
        """Return local username on the service.

        If the user doesn't exists, behaviour is undefined.
        """
        pass

    @abstractmethod
    def set_username(self, username):
        """Set local username on the service."""
        pass

    @abstractmethod
    def get_primary_group(self):
        """Check if a user exists based on unique_id and return the primary group name."""
        pass

    @abstractmethod
    def is_suspended(self):
        """Optional, only if the backend supports it.
        Return whether the user was suspended (e.g. due to a security incident)"""
        return False

    @abstractmethod
    def is_limited(self):
        """Optional, only if the backend supports it.
        Return whether the user has limited access"""
        return False

    @abstractmethod
    def suspend(self):
        """Optional, only if the backend supports it.
        Suspends the user such that no access to the service is possible"""
        pass

    @abstractmethod
    def resume(self):
        """Optional, only if the backend supports it.
        Restores the suspended user"""
        pass

    @abstractmethod
    def limit(self):
        """Optional, only if the backend supports it.
        Limits the user's capabilities on the service (e.g. read-only access)"""
        pass

    @abstractmethod
    def unlimit(self):
        """Optional, only if the backend supports it.
        Restores a user with limited access to full capabilities"""
        pass


class Group(ABC):
    """Manages the group object on the service."""

    def __init__(self, name):
        """
        Arguments:
        name -- The name of the group
        """
        pass

    @abstractmethod
    def exists(self):
        """Return whether the group already exists."""
        pass

    @abstractmethod
    def create(self):
        """Create the group on the service.

        If the group already exists, behaviour is undefined.
        """
        pass
