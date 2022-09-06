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
    def mod(self, supplementary_groups=None, removal_groups=None):
        """Modify the user on the service.

        The user's membership to groups not provided in the arguments will not change.

        If the user doesn't exists, behaviour is undefined.

        Arguments:
        supplementary_groups -- A list of groups to add the user to (type: list(Group))
        removal_groups -- A list of groups to remove the user from (type: list(Group))
        """
        pass

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
