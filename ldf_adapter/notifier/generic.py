from abc import ABC, abstractmethod
from ldf_adapter.notifier.notification import NotificationType


class GenericNotifier(ABC):
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
