from abc import ABC, abstractmethod

from string import Template
from enum import Enum
from pathlib import Path


class NotificationType(Enum):
    NONE = 0
    ADMIN_DEPLOY = 1
    ADMIN_DEPLOY_UPDATE = 2
    ADMIN_UPDATE = 3
    ADMIN_TEST = 4
    USER_DEPLOY = 5
    USER_DEPLOY_UPDATE = 6
    USER_UPDATE = 7
    UNKNOWN = -1


class NotificationTemplate:
    def __init__(self, template_body: str, template_id: str = ""):
        """Initialises notification template.

        Args:
            template_body (str): body of the template
            template_id (str, optional): id of the template. Defaults to "".
        """
        self.template_body = template_body
        self.template_id = template_id

    def get_variables(self) -> list:
        """Returns list of variables in the template."""
        return [var for var in Template(self.template_body).pattern.split("$") if var != ""]

    def fill(self, **kwargs):
        """Fills template with given variables.

        Args:
            **kwargs: variables to fill template with.
        """
        # return Template(self.template_body).substitute(**kwargs)
        return Template(self.template_body).safe_substitute(**kwargs)

    @classmethod
    def load(cls, template_file: Path) -> "NotificationTemplate":
        """Loads notification template from file.

        Args:
            template_file (Path): path to the template file.
        """
        with open(template_file, "r") as f:
            return cls(
                template_body=f.read(),
                template_id=Path(template_file).name,
            )


class Notifier(ABC):
    """Generic class for sending notifications."""

    @abstractmethod
    def notify(self, notification_type: NotificationType, **kwargs: dict) -> bool:
        """Sends out a notification. Arguments are not specified here, but are passed to the
        concrete implementation.
        Returns True if notification was sent, False otherwise.

        To be implemented for all notification providers.
        """
        pass

    @abstractmethod
    def test(self):
        """Send test notification to admin to make sure the configured set-up works.

        To be implemented for all notification providers.
        """
        pass
