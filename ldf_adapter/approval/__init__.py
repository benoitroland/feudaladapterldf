"""
Implement approval workflow for user deployments.
"""
import logging
from typing import List, Optional, Tuple
from enum import Enum

from .. import backend
from ..userinfo import UserInfo
from .db import PendingUser, PendingGroup, PendingMemberships, SqlitePendingDB, DeploymentState


logger = logging.getLogger(__name__)


class NotificationType(Enum):
    NOOP = 0
    NEW = 1
    UPDATE_REQUEST = 2
    UPDATE_GROUPS = 3
    UNKNOWN = 4


class PendingDeployment:
    """Represents a pending deployment request for a user and its groups.
    Communicates with the pending DB to store and retrieve pending deployments."""

    _user: Optional[PendingUser] = None
    _groups: List[PendingGroup] = []
    _memberships: Optional[PendingMemberships] = None

    def __init__(self, userinfo: UserInfo, user_db_location: str) -> None:
        """Initialise a pending deployment for a federated user.
        If a request already exists for this user, initialise properties.

        Args:
            userinfo (UserInfo): user info of federated user
            user_db_location (str): path to pending db
        """
        self._pending_db = SqlitePendingDB(location=user_db_location)
        self.unique_id = userinfo.unique_id
        self._sub = userinfo.sub
        self._iss = userinfo.iss
        self._email = userinfo.email
        self._full_name = userinfo.full_name

        self._user = self._pending_db.get_user(userinfo.unique_id)
        self._memberships = self._pending_db.get_memberships(userinfo.unique_id)
        if self._memberships:
            self._groups = list(
                filter(
                    None,
                    [self._pending_db.get_group(m) for m in self._memberships.supplementary_groups],
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
        if (
            entry
            and entry.unique_id != self.unique_id
            and entry.state in [DeploymentState.PENDING, DeploymentState.NOTIFIED]
        ):
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
            state=DeploymentState.PENDING,
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
            name=group.name, state=DeploymentState.PENDING, cmd=group.create_tostring(), infodict={}
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
        if supplementary_groups == [] and removal_groups == []:
            return False
        supplementary_group_names = [g.name for g in supplementary_groups]
        removal_group_names = [g.name for g in removal_groups]

        memberships = PendingMemberships(
            unique_id=service_user.unique_id,
            supplementary_groups=supplementary_group_names,
            removal_groups=removal_group_names,
            state=DeploymentState.PENDING,
            cmd=service_user.mod_tostring(
                supplementary_groups=supplementary_groups, removal_groups=removal_groups
            ),
            infodict={},
        )

        if self._memberships is None:
            self._pending_db.add_memberships(memberships)
            self._memberships = memberships
            return True
        elif set(self._memberships.supplementary_groups) != set(supplementary_group_names) or set(
            self._memberships.removal_groups
        ) != set(removal_group_names):
            self._pending_db.update_memberships(memberships)
            self._memberships = memberships
            return True
        return False

    def remove_data(self):
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
        return self.user is not None and self.user.state in [
            DeploymentState.PENDING,
            DeploymentState.NOTIFIED,
        ]

    def is_rejected(self) -> bool:
        """Whether the deployment was requested and was rejected."""
        return self.user is not None and self.user.state == DeploymentState.REJECTED

    def mod_pending(self) -> bool:
        """Whether a group membership change is pending approval."""
        return self.memberships is not None and self.memberships.state in [
            DeploymentState.PENDING,
            DeploymentState.NOTIFIED,
        ]

    def accept(self) -> None:
        """Accept this pending deployment and create user and groups (backend-specific)."""
        for group in self.groups:
            backend.Group.create_fromstring(group.cmd)  # type: ignore
        if self.user:
            backend.User.create_fromstring(self.user.cmd)  # type: ignore
        if self.memberships:
            backend.User.mod_fromstring(self.memberships.cmd)  # type: ignore
        self.remove_data()

    def reject(self) -> None:
        """Reject this pending deployment by setting the state of the user in the pending db
        to 'rejected', and remove pending group and membership entries for this user."""
        if self.user:
            self._pending_db.reject_user(self.unique_id)
            self._user = self._pending_db.get_user(self.unique_id)
        for group in self.groups:
            self._pending_db.remove_group(group.name)
        self._groups = []
        if self.memberships:
            self._pending_db.remove_memberships(self.unique_id)
            self._memberships = None

    def get_notification_type(self) -> Tuple[NotificationType, str]:
        """Return the type of notification to be sent to the user."""
        if self.user is None and self.memberships is None:
            # no pending user or group membership, nothing to notify
            return NotificationType.NOOP, "No pending deployment, nothing to notify."
        if self.user and self.user.state == DeploymentState.PENDING:
            # new deployment request
            return NotificationType.NEW, "Request for deployment was submitted for approval."
        if self.memberships and self.memberships.state == DeploymentState.PENDING:
            # only membership changes are pending
            if self.user is None:
                # user exists, but groups need to be updated
                return (
                    NotificationType.UPDATE_GROUPS,
                    "Request for updating user groups was submitted for approval.",
                )
            if self.user and self.user.state == DeploymentState.NOTIFIED:
                # deployment request already notified, but groups have changed and need to be updated
                return (
                    NotificationType.UPDATE_REQUEST,
                    "Updated request for deployment was submitted for approval.",
                )
        # nothing to do, request already notified and no changes happened
        return NotificationType.NOOP, "Request for deployment was already submitted for approval."

    def set_notified(self) -> None:
        """Set the state of this pending deployment to 'notified' by setting the state of the user
        and/or its memberships in the pending db to 'notified'.
        """
        if self.user:
            self._pending_db.notify_user(self.unique_id)
        if self.memberships:
            self._pending_db.notify_memberships(self.unique_id)
        for group in self.groups:
            self._pending_db.notify_group(group.name)
