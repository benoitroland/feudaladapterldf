from typing import Optional
from abc import ABC, abstractmethod

from ldf_adapter.approval.models import PendingUser, PendingGroup, PendingMemberships


class PendingDB(ABC):
    """Generic class to manage users (and groups) in states associated with the approval workflow.

    To add a new implementation for PendingDB, create a new module in this directory containing a
    class also named PendingDB that extends this class and implements all abstract methods.
    The new class will be automatically loaded by the 'databases' factory and can be accessed with
    the name of the module: databases.get("new_db_type")
    """

    @abstractmethod
    def add_user(self, user: PendingUser) -> bool:
        """Add a new entry for a user. Returns False if entry already exists."""
        return False

    @abstractmethod
    def remove_user(self, unique_id: str) -> None:
        """Remove user entry for unique_id."""
        pass

    @abstractmethod
    def get_user(self, unique_id: str) -> Optional[PendingUser]:
        """Get a user entry that is up for approval by the user's unique_id."""
        return None

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[PendingUser]:
        """Get a user entry by the local username."""
        return None

    @abstractmethod
    def reject_user(self, unique_id: str) -> None:
        """Change the state of user given by unique_id to REJECTED."""
        pass

    @abstractmethod
    def notify_user(self, unique_id: str) -> None:
        """Change the state of user given by unique_id to NOTIFIED."""
        pass

    @abstractmethod
    def add_group(self, group: PendingGroup) -> bool:
        """Add a new entry for a group. Returns False if entry already exists."""
        return False

    @abstractmethod
    def remove_group(self, name: str) -> None:
        """Remove group entry for name."""
        pass

    @abstractmethod
    def get_group(self, name: str) -> Optional[PendingGroup]:
        """Get a group entry that is up for approval by the group's name."""
        return None

    @abstractmethod
    def notify_group(self, name: str) -> None:
        """Change the state of group given by name to NOTIFIED."""
        pass

    @abstractmethod
    def add_memberships(self, membership: PendingMemberships) -> bool:
        """Add a new entry for a user's pending group memberships. Returns False if entry already exists."""
        return False

    @abstractmethod
    def update_memberships(self, membership: PendingMemberships) -> None:
        """Update a user's pending group memberships by replacing them with the given memberships.
        A user is denoted by the unique_id in membership.
        """
        pass

    @abstractmethod
    def remove_memberships(self, unique_id: str) -> None:
        """Remove all pending group memberships of a given user."""
        pass

    @abstractmethod
    def get_memberships(self, unique_id: str) -> Optional[PendingMemberships]:
        """Get a given user's pending group memberships. Returns None if the user is not found."""
        return None

    @abstractmethod
    def notify_memberships(self, unique_id: str) -> None:
        """Change the state of user's memberships given by unique_id to NOTIFIED."""
        pass
