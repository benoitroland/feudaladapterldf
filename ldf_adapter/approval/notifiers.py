from __future__ import annotations
from enum import Enum
from typing import Optional
import logging
import smtplib
import sys
from email.message import EmailMessage
from string import Template

from . import PendingDeployment
from .templates import MessageTemplateAdmin, MessageTemplateUser
from ..results import Failure

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    NEW = 1
    UPDATE = 2


class Notifier:
    """Generic class for notifying admins of deployment requests."""

    def _notify(
        self,
        deployment: PendingDeployment,
        notification_type: NotificationType = NotificationType.NEW,
    ):
        """Notifies admin and user of request of given type.

        To be implemented for all notification providers.
        """

    def notify_new(self, deployment: PendingDeployment):
        """Notify admin and user of a new request for deployment."""
        self._notify(deployment, NotificationType.NEW)

    def notify_update(self, deployment: PendingDeployment):
        """Notify admin and user of an update to an already pending deployment.
        The update concerns new groups and group memberships."""
        self._notify(deployment, NotificationType.UPDATE)

    def test(self):
        """Send test notification to admin to make sure the configured set-up works.

        To be implemented for all notification providers.
        """

    @staticmethod
    def load(notifier_type: str, notifier_config: dict, hostname: str = "localhost") -> Notifier:
        """Load the notifier based on the type and configuration options given.

        Args:
            notifier_type (str): type of notifier; supported: email
            notifier_config (dict): configuration options loaded from feudal config
            hostname (str, optional): host where user requests access. Defaults to "localhost".

        Returns:
            Notifier: an initialised notifier object of desired type.
        """
        if notifier_type.lower() == "email":
            smtp_server = notifier_config.get("smtp_server", "localhost")
            smtp_port = int(notifier_config.get("smtp_port", "25"))
            admin_email = notifier_config.get("admin_email", "admin@localhost")
            sent_from = notifier_config.get("sent_from", "admin@localhost")
            sent_from_password = notifier_config.get("sent_from_password", None)
            use_ssl = bool(notifier_config.get("use_ssl", "False"))
            return EmailNotifier(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                admin_email=admin_email,
                sent_from=sent_from,
                sent_from_password=sent_from_password,
                hostname=hostname,
                use_ssl=use_ssl,
            )

        message = f"Could not initialise notifier for approval workflow: unknown notifier type {notifier_type}."
        logger.error(message)
        print(f"\nERROR: {message}\n")
        sys.exit(2)


class EmailNotifier(Notifier):
    """Implementation of an email notifier for deployment requests."""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        admin_email: str,
        sent_from: str,
        sent_from_password: Optional[str] = None,
        hostname: str = "localhost",
        use_ssl: bool = False,
    ) -> None:
        """Initialise SMTP notifier

        Args:
            smtp_server (str): hostname of SMTP server to use for sending emails
            smtp_port (int): port of SMTP server to use for sending emails
            admin_email (str): email address of admin to send emails TO
            sent_from (str): email address to send emails FROM
            sent_from_password (Optional[str], optional): password of sent_from email (optional).
                If not specified, no password login will be used, if the server supports it. Defaults to None.
            hostname (str, optional): ssh host where a user is requesting deployment. Defaults to 'localhost'.
            use_ssl (bool, optional): whether to use ssl connection to smtp server. Defaults to False.
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.admin_email = admin_email
        self.sent_from = sent_from
        self.sent_from_password = sent_from_password
        self.hostname = hostname
        self.use_ssl = use_ssl

    def _build_email(self, send_to: str, subject: str, content: str) -> EmailMessage:
        """Build and email message.

        Args:
            send_to (str): email address to put in "To" field
            subject (str): email subject line
            content (str): content of the email

        Returns:
            EmailMessage: email object
        """
        msg = EmailMessage()
        msg.set_content(content)
        msg["Subject"] = subject
        msg["From"] = self.sent_from
        msg["To"] = send_to
        return msg

    def _send_email(self, email: EmailMessage):
        """Send an email using the configured SMTP settings."""
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.ehlo()
            if self.sent_from_password:
                server.login(self.sent_from, self.sent_from_password)
            server.send_message(email)
            server.close()
            logger.debug(
                "Email with subject '%s' sent successfully to '%s'!", email["Subject"], email["To"]
            )
        except Exception as ex:
            logger.error("Could not send email to {%s}: %s", email["To"], ex)
            raise Failure(message=f"Failed to send request to admin for approval.")

    def _notify(
        self,
        deployment: PendingDeployment,
        notification_type: NotificationType = NotificationType.NEW,
    ):
        """Notifies admin and user of request of given type by sending en email."""
        if notification_type == NotificationType.NEW:
            admin_template = MessageTemplateAdmin.DEPLOY
            user_template = MessageTemplateUser.DEPLOY
        elif notification_type == NotificationType.UPDATE:
            admin_template = MessageTemplateAdmin.UPDATE
            user_template = MessageTemplateUser.UPDATE
        else:
            raise Failure(message=f"Unknown notification type {notification_type}")

        user_cmd = deployment.user.cmd if deployment.user else ""
        groups_cmd = "\n".join([m.cmd for m in deployment.groups])
        memberships_cmd = "\n".join([m.cmd for m in deployment.memberships])

        admin_content = Template(admin_template).substitute(
            hostname=self.hostname,
            unique_id=deployment.unique_id,
            full_name=deployment.full_name,
            email=deployment.email,
            user_cmd=user_cmd,
            groups_cmd=groups_cmd,
            memberships_cmd=memberships_cmd,
            sub=deployment.sub,
            iss=deployment.iss,
        )
        user_content = Template(user_template).substitute(
            hostname=self.hostname, unique_id=deployment.unique_id
        )

        self._send_email(
            email=self._build_email(
                send_to=self.admin_email,
                subject=f"Request for deployment for user {deployment.unique_id}",
                content=admin_content,
            )
        )
        if deployment.email:
            self._send_email(
                email=self._build_email(
                    send_to=deployment.email,
                    subject=f"Request for deployment to '{self.hostname}' submitted",
                    content=user_content,
                )
            )
        else:
            logger.warning(
                "No email found in deployment request: user will not receive email notification."
            )

    def test(self):
        """Send test notification to admin to make sure the configured set-up works."""
        self._send_email(
            email=self._build_email(
                send_to=self.admin_email,
                subject=f"Test email notification on '{self.hostname}'",
                content=Template(MessageTemplateAdmin.TEST).substitute(hostname=self.hostname),
            )
        )
