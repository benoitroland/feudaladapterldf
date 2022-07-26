from trycourier import Courier

from ldf_adapter.notifier.generic import GenericNotifier
from ldf_adapter.notifier.notification import NotificationType


class CourierNotifier(GenericNotifier):
    """(WIP) Implementation of a Courier notifier for deployment requests."""

    def __init__(self, api_key: str, ssh_host: str = "localhost") -> None:
        """Initialises Courier notifier

        Args:
            api_key (str): API key configured in Courier (from feudal config)
            template_id (str): template ID of configured email template in courier (from feudal config)
            ssh_host (str, optional): ssh host where a user is requesting deployment. Defaults to 'localhost'.
        """
        self.client = Courier(auth_token=api_key)
        self.ssh_host = ssh_host

    def notify(
        self,
        notification_type: NotificationType,
        send_to: str,
        template_id: str,
        data: dict,
        **ignored: dict
    ):
        """Notifies admin of request of given type."""
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


class CourierNotifierBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, ssh_host: str, **notifier_config):
        if not self._instance:
            api_key = notifier_config.get("api_key", "")
            self._instance = CourierNotifier(
                api_key=api_key,
                ssh_host=ssh_host,
            )
        return self._instance
