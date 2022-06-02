"""
Implement approval workflow for user deployments.
"""
import logging
from typing import List, Optional

from .. import backend
from ..userinfo import UserInfo
from .db import PendingUser, PendingGroup, PendingMembership, PendingDB

logger = logging.getLogger(__name__)


class PendingDeployment:
    """Represents a pending deployment request for a user and its groups.
    Communicates with the pending DB to store and retrieve pending deployments."""

    _user: Optional[PendingUser] = None
    _groups: List[PendingGroup] = []
    _memberships: List[PendingMembership] = []

    def __init__(self, pending_db: PendingDB, userinfo: UserInfo) -> None:
        """Initialise a pending deployment for a federated user.
        If a request already exists for this user, initialise properties.

        Args:
            pending_db (PendingDB): database containing pending deployment requests
            userinfo (UserInfo): user info of federated user
        """
        self._pending_db = pending_db
        self.unique_id = userinfo.unique_id
        self.email = userinfo.email
        self.full_name = userinfo.full_name
        self._user = pending_db.get_user(userinfo.unique_id)
        self._memberships = pending_db.get_memberships(userinfo.unique_id)
        self._groups = list(
            filter(
                None,
                [pending_db.get_group(m.name) for m in self._memberships],
            )
        )

    @property
    def user(self) -> Optional[PendingUser]:
        """Get information about the user pending deployment."""
        return self._user

    @property
    def groups(self) -> List[PendingGroup]:
        """Get information about the groups that need to be created for this pending deployment."""
        return self._groups

    @property
    def memberships(self) -> List[PendingMembership]:
        """Get information about the groups that the user needs to be added to."""
        return self._memberships

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
            email=self.email,
            full_name=self.full_name,
            username=service_user.name,
            state="pending",
            cmd=service_user.create_tostring(),
        )
        if self._pending_db.add_user(pending_user):
            self._user = pending_user
            return True
        return False

    def create_group(self, group: backend.Group) -> bool:  # type: ignore
        """Create new pending group entry and add it to db.
        Return False if the entry already exists for this user in pending db.
        """
        if group.name in [g.name for g in self.groups]:
            return False
        pending_group = PendingGroup(name=group.name, state="pending", cmd=group.create_tostring())
        self._pending_db.add_group(pending_group)
        self._groups.append(pending_group)
        return True

    def add_user_to_groups(self, service_user: backend.User, supplementary_groups: List[backend.Group]) -> List[str]:  # type: ignore
        """Create new pending membership entries for each group in list and add them to db.
        Return a list of group names the user was  in pending db.
        """
        new_groups = []
        pending_groups = [g.name for g in self.memberships]
        for group in supplementary_groups:
            if group.name not in pending_groups:
                membership = PendingMembership(
                    unique_id=service_user.unique_id,
                    name=group.name,
                    state="pending",
                    cmd=service_user.mod_tostring(supplementary_groups=[group]),
                )
                self._pending_db.add_membership(membership)
                self._memberships.append(membership)
                new_groups.append(group.name)
        return new_groups

    def remove_pending_data(self):
        """Remove from pending db all data associated to this user."""
        if self.user:
            self._pending_db.remove_user(self.user.unique_id)
        for group in self.groups:
            self._pending_db.remove_group(group.name)
        self._pending_db.remove_memberships(self.unique_id)
        self._user = None
        self._groups = []
        self._memberships = []

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
        return self.groups != [] or self.memberships != []

    def accept(self):
        """Accept this pending deployment and create user and groups (backend-specific)."""
        for group in self.groups:
            backend.Group.create_fromstring(group.cmd)  # type: ignore
        if self.user:
            backend.User.create_fromstring(self.user.cmd)  # type: ignore
        for membership in self.memberships:
            backend.User.mod_fromstring(membership.cmd)  # type: ignore
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
        self._memberships = []
