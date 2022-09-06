from trycourier import Courier

from ldf_adapter.results import FatalError
from ldf_adapter.config import CONFIG
from ldf_adapter.notifier import generic


class Notifier(generic.Notifier):
    """(WIP) Implementation of a Courier notifier for deployment requests."""

    def __init__(self) -> None:
        """Initialises Courier notifier."""
        if CONFIG.notifier.courier is None:
            raise FatalError("Courier notifier is not configured")
        self.client = Courier(auth_token=CONFIG.notifier.courier.api_key)
        self.ssh_host = CONFIG.login_info.ssh_host

    def notify(
        self,
        notification_type: generic.NotificationType,
        send_to: str,
        template_id: str,
        data: dict,
        **_ignored: dict
    ):
        """Notifies admin of request of given type.

        Args:
            notification_type (NotificationType): type of notification
            send_to (str): email address to send notification to
            template_id (str): template ID of configured email template in courier
            data (dict): data to use in email template
        Returns:
            bool: True if notification was sent, False otherwise
        """
        self.client.send_message(
            message={
                "to": {
                    "email": send_to,
                },
                "template_id": template_id,
                "data": data,
            }
        )

    def test(self):
        return super().test()
