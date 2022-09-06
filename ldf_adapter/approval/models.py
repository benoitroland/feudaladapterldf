from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeploymentState(Enum):
    """The state of a deployment request. One of:

    - PENDING: the request has been created and is pending approval
    - NOTIFIED: the local admin has been notified of the pending request
    - REJECTED: the request has been rejected
    - UNKNOWN: the request state is unknown

    Once it is accepted, the request is removed from the pending database.
    """

    PENDING = 0
    NOTIFIED = 1
    REJECTED = 2
    UNKNOWN = 3

    @staticmethod
    def from_string(state: str):
        """
        Convert a string to a DeploymentState.
        Args:
            state (str): the string to convert
        Returns:
            DeploymentState: the DeploymentState or DeploymentState.UNKNOWN if the string is not a valid DeploymentState
        """
        try:
            return DeploymentState[state]
        except ValueError:
            return DeploymentState.UNKNOWN


@dataclass
class PendingModel:
    """A generic data model to be stored in the pending DB."""


@dataclass
class PendingUser(PendingModel):
    """Data model for storing information on a user pending approval."""

    unique_id: str
    sub: str
    iss: str
    email: Optional[str]
    full_name: Optional[str]
    username: str
    state: DeploymentState
    cmd: str
    infodict: dict


@dataclass
class PendingGroup(PendingModel):
    """Data model for storing groups of a user pending approval."""

    name: str
    state: DeploymentState
    cmd: str
    infodict: dict


@dataclass
class PendingMemberships(PendingModel):
    """Data model for storing group memberships of a user pending approval."""

    unique_id: str
    supplementary_groups: list
    removal_groups: list
    state: DeploymentState
    cmd: str
    infodict: dict
