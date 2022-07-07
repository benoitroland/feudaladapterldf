"""
Implement approval workflow for user deployments.
"""
import logging
from typing import List, Optional

from .. import backend
from ..userinfo import UserInfo
from .db import PendingUser, PendingGroup, PendingMemberships, PendingDB

logger = logging.getLogger(__name__)


class PendingDeployment:
    """Represents a pending deployment request for a user and its groups.
    Communicates with the pending DB to store and retrieve pending deployments."""

    _user: Optional[PendingUser] = None
    _groups: List[PendingGroup] = []
    _memberships: Optional[PendingMemberships] = None

    def __init__(self, pending_db: PendingDB, userinfo: UserInfo) -> None:
        """Initialise a pending deployment for a federated user.
        If a request already exists for this user, initialise properties.

        Args:
            pending_db (PendingDB): database containing pending deployment requests
            userinfo (UserInfo): user info of federated user
        """
        self.unique_id = userinfo.unique_id
        self._sub = userinfo.sub
        self._iss = userinfo.iss
        self._email = userinfo.email
        self._full_name = userinfo.full_name

        self._pending_db = pending_db
        self._user = pending_db.get_user(userinfo.unique_id)
        self._memberships = pending_db.get_memberships(userinfo.unique_id)
        if self._memberships:
            self._groups = list(
                filter(
                    None,
                    [pending_db.get_group(m) for m in self._memberships.supplementary_groups],
                )
            )
        else:
            self._groups = []

    @property
    def user(self) -> Optional[PendingUser]:
        """Get information about the user pending deployment."""
        return self._user

    @property
    def groups(self) -> List[PendingGroup]:
        """Get information about the groups that need to be created for this pending deployment."""
        return self._groups

    @property
    def memberships(self) -> Optional[PendingMemberships]:
        """Get information about the groups that the user needs to be added to."""
        return self._memberships

    @property
    def sub(self) -> str:
        """Return sub as set in pending db, or in userinfo if user property not set."""
        if self.user:
            return self.user.sub
        return self._sub

    @property
    def iss(self) -> str:
        """Return iss as set in pending db, or in userinfo if user property not set."""
        if self.user:
            return self.user.iss
        return self._iss

    @property
    def email(self) -> Optional[str]:
        """Return email as set in pending db, or in userinfo if user property not set."""
        if self.user:
            return self.user.email
        return self._email

    @property
    def full_name(self) -> Optional[str]:
        """Return full_name as set in pending db, or in userinfo if user property not set."""
        if self.user:
            return self.user.full_name
        return self._full_name

    @property
    def username(self) -> Optional[str]:
        """Return local username as set in pending db, or None if user property not set."""
        if self.user:
            return self.user.username
        return None

    def exists(self) -> bool:
        """Whether there is already an entry in the pending DB for this user."""
        return self.user is not None

    def name_taken(self, name: str) -> bool:
        """Whether the username is already reserved by *another* user."""
        entry = self._pending_db.get_user_by_username(name)
        if entry and entry.unique_id != self.unique_id and entry.state == "pending":
            return True
        return False

    def create_user(self, service_user: backend.User) -> bool:  # type: ignore
        """Create pending user entry and add it to db.
        Return False if entry already exists in pending db.
        """
        pending_user = PendingUser(
            unique_id=service_user.unique_id,
            sub=self.sub,
            iss=self.iss,
            email=self.email,
            full_name=self.full_name,
            username=service_user.name,
            state="pending",
            cmd=service_user.create_tostring(),
            infodict={},
        )
        if self._pending_db.add_user(pending_user):
            self._user = pending_user
            return True
        return False

    def update_user(self, service_user: backend.User) -> bool:  # type: ignore
        """Add entry in pending db to update an existing user, only if necessary.
        Return True if there was an update.
        """
        return False

    def create_group(self, group: backend.Group) -> bool:  # type: ignore
        """Create new pending group entry and add it to db.
        Return False if the entry already exists for this user in pending db.
        """
        if group.name in [g.name for g in self.groups]:
            return False
        pending_group = PendingGroup(
            name=group.name, state="pending", cmd=group.create_tostring(), infodict={}
        )
        self._pending_db.add_group(pending_group)
        self._groups.append(pending_group)
        return True

    def mod(self, service_user: backend.User, supplementary_groups: List[backend.Group], removal_groups: List[backend.Group]) -> bool:  # type: ignore
        """Create or update info in pending db s.t. the given user is added and removed
        from the given groups.

        If no pending memberships exist, create a new entry for user's pending memberships
        and add it to pending db.
        If pending db contains given user's membership, modify entry only if the lists of groups
        to be added to/removed from have changed.

        Return True if the pending db has been modified and False otherwise.
        """
        supplementary_group_names = [g.name for g in supplementary_groups]
        removal_group_names = [g.name for g in removal_groups]

        membership = PendingMemberships(
            unique_id=service_user.unique_id,
            supplementary_groups=supplementary_group_names,
            removal_groups=removal_group_names,
            state="pending",
            cmd=service_user.mod_tostring(
                supplementary_groups=supplementary_groups, removal_groups=removal_groups
            ),
            infodict={},
        )

        if self._memberships is None:
            self._pending_db.add_memberships(membership)
            self._memberships = membership
            return True
        elif set(self._memberships.supplementary_groups) != set(supplementary_group_names) or set(
            self._memberships.removal_groups
        ) != set(removal_group_names):
            self._pending_db.update_memberships(membership)
            self._memberships = membership
            return True
        return False

    def remove_pending_data(self):
        """Remove from pending db all data associated to this user."""
        if self.user:
            self._pending_db.remove_user(self.user.unique_id)
        for group in self.groups:
            self._pending_db.remove_group(group.name)
        self._pending_db.remove_memberships(self.unique_id)
        self._user = None
        self._groups = []
        self._memberships = None

    def is_pending(self) -> bool:
        """Whether the deployment was requested and is pending approval."""
        entry = self._pending_db.get_user(self.unique_id)
        if entry:
            return entry.state == "pending"
        return False

    def is_rejected(self) -> bool:
        """Whether the deployment was requested and was rejected."""
        entry = self._pending_db.get_user(self.unique_id)
        if entry:
            return entry.state == "rejected"
        return False

    def groups_pending(self) -> bool:
        """Whether a group creation and membership change is pending approval."""
        return self.groups != [] or self.memberships != None

    def accept(self):
        """Accept this pending deployment and create user and groups (backend-specific)."""
        for group in self.groups:
            backend.Group.create_fromstring(group.cmd)  # type: ignore
        if self.user:
            backend.User.create_fromstring(self.user.cmd)  # type: ignore
        if self.memberships:
            backend.User.mod_fromstring(self.memberships.cmd)  # type: ignore
        self.remove_pending_data()

    def reject(self):
        """Reject this pending deployment by setting the state of the user in the pending db
        to 'rejected', and remove pending group and membership entries for this user."""
        if self.user:
            self._pending_db.reject_user(self.unique_id)
            self._user = self._pending_db.get_user(self.unique_id)
        for group in self.groups:
            self._pending_db.remove_group(group.name)
        self._pending_db.remove_memberships(self.unique_id)
        self._groups = []
        self._memberships = None
