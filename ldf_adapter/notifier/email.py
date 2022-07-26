from dataclasses import dataclass
from typing import Optional
import logging
import smtplib
from email.message import EmailMessage
import json
from pathlib import Path

from ldf_adapter.results import Failure
from ldf_adapter.utils import to_bool, to_int
from ldf_adapter.notifier.generic import GenericNotifier
from ldf_adapter.notifier.notification import NotificationType, NotificationTemplate

logger = logging.getLogger(__name__)

NOTIFY_TIMEOUT = 1.2  # seconds


@dataclass
class EmailSettings:
    send_to_template: str
    subject_template: str
    body_template_file: str


# settings for each notification type.
EMAIL_SETTINGS = {
    NotificationType.ADMIN_DEPLOY: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Request for deployment for user ${unique_id}",
        body_template_file="admin.deploy.template",
    ),
    NotificationType.ADMIN_DEPLOY_UPDATE: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Updated request for deployment for user ${unique_id}",
        body_template_file="admin.deploy.update.template",
    ),
    NotificationType.ADMIN_UPDATE: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Request for update for user ${unique_id}",
        body_template_file="admin.update.template",
    ),
    NotificationType.ADMIN_TEST: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Test email notification on '${hostname}'",
        body_template_file="admin.test.template",
    ),
    NotificationType.USER_DEPLOY: EmailSettings(
        send_to_template="${email}",
        subject_template="Request for deployment to '${hostname}' submitted",
        body_template_file="user.deploy.template",
    ),
    NotificationType.USER_DEPLOY_UPDATE: EmailSettings(
        send_to_template="${email}",
        subject_template="Updated request for deployment to '${hostname}' submitted",
        body_template_file="user.deploy.update.template",
    ),
    NotificationType.USER_UPDATE: EmailSettings(
        send_to_template="${email}",
        subject_template="Request for account update on '${hostname}' submitted",
        body_template_file="user.update.template",
    ),
    NotificationType.UNKNOWN: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Unknown notification type",
        body_template_file="unknown.template",
    ),
}


class EmailNotifier(GenericNotifier):
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
        templates_dir: str = "/etc/feudal/templates",
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
            templates_dir (str, optional): path to directory containing templates. Defaults to "/etc/feudal/templates".
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.admin_email = admin_email
        self.sent_from = sent_from
        self.sent_from_password = sent_from_password
        self.hostname = hostname
        self.use_ssl = use_ssl
        self.templates_dir = templates_dir

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
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=NOTIFY_TIMEOUT)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=NOTIFY_TIMEOUT)
            server.ehlo()
            if self.sent_from_password:
                server.login(self.sent_from, self.sent_from_password)
            server.send_message(email)
            server.close()
            logger.debug(
                "Email with subject '%s' sent successfully to '%s'!", email["Subject"], email["To"]
            )
        except Exception as ex:
            raise Exception("Could not send email to {%s}: %s", email["To"], ex)

    def notify(
        self,
        notification_type: NotificationType,
        data: dict,
        **_ignored: dict,
    ):
        """Sends out an email notification.

        Args:
            notification_type (NotificationType): type of notification
            data (dict): data to use in email template
        Returns:
            bool: True if notification was sent, False otherwise
        """
        if notification_type == NotificationType.NONE:
            logger.info("Notification type is NONE, not sending email")
            return False
        data = {**data, "admin_email": self.admin_email}
        send_to = NotificationTemplate(EMAIL_SETTINGS[notification_type].send_to_template).fill(
            **data
        )
        subject = NotificationTemplate(EMAIL_SETTINGS[notification_type].subject_template).fill(
            **data
        )
        content = NotificationTemplate.load(
            Path(self.templates_dir) / EMAIL_SETTINGS[notification_type].body_template_file
        ).fill(**data)
        email = self._build_email(send_to, subject, content)
        self._send_email(email)
        return True

    def test(self):
        """Send test notification to admin to make sure the configured set-up works."""
        data = {
            "admin_email": self.admin_email,
            "hostname": self.hostname,
            "notifier": "email",
            "settings": json.dumps(
                {
                    "smtp_server": self.smtp_server,
                    "smtp_port": self.smtp_port,
                    "use_ssl": self.use_ssl,
                    "admin_email": self.admin_email,
                    "sent_from": self.sent_from,
                    "sent_from_password": "*****" if self.sent_from_password else None,
                },
                indent=4,
            ),
        }
        self.notify(notification_type=NotificationType.ADMIN_TEST, data=data)


class EmailNotifierBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, ssh_host: str, **notifier_config):
        if not self._instance:
            smtp_server = notifier_config.get("smtp_server", "localhost")
            smtp_port = to_int(notifier_config.get("smtp_port", "25"))
            admin_email = notifier_config.get("admin_email", "admin@localhost")
            sent_from = notifier_config.get("sent_from", "admin@localhost")
            sent_from_password = notifier_config.get("sent_from_password", None)
            use_ssl = to_bool(notifier_config.get("use_ssl", "False"))
            templates_dir = notifier_config.get("templates_dir", "/etc/feuda/templates")
            self._instance = EmailNotifier(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                admin_email=admin_email,
                sent_from=sent_from,
                sent_from_password=sent_from_password,
                hostname=ssh_host,
                use_ssl=use_ssl,
                templates_dir=templates_dir,
            )
        return self._instance
