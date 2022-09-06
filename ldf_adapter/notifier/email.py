from dataclasses import dataclass
from typing import Optional
import logging
import smtplib
from email.message import EmailMessage
import json
from pathlib import Path
from ldf_adapter.config import CONFIG

from ldf_adapter.notifier import generic
from ldf_adapter.results import FatalError

logger = logging.getLogger(__name__)

NOTIFY_TIMEOUT = 1.2  # seconds


@dataclass
class EmailSettings:
    send_to_template: str
    subject_template: str
    body_template_file: str


# settings for each notification type.
EMAIL_SETTINGS = {
    generic.NotificationType.ADMIN_DEPLOY: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Request for deployment for user ${unique_id}",
        body_template_file="admin.deploy.template",
    ),
    generic.NotificationType.ADMIN_DEPLOY_UPDATE: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Updated request for deployment for user ${unique_id}",
        body_template_file="admin.deploy.update.template",
    ),
    generic.NotificationType.ADMIN_UPDATE: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Request for update for user ${unique_id}",
        body_template_file="admin.update.template",
    ),
    generic.NotificationType.ADMIN_TEST: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Test email notification on '${hostname}'",
        body_template_file="admin.test.template",
    ),
    generic.NotificationType.USER_DEPLOY: EmailSettings(
        send_to_template="${email}",
        subject_template="Request for deployment to '${hostname}' submitted",
        body_template_file="user.deploy.template",
    ),
    generic.NotificationType.USER_DEPLOY_UPDATE: EmailSettings(
        send_to_template="${email}",
        subject_template="Updated request for deployment to '${hostname}' submitted",
        body_template_file="user.deploy.update.template",
    ),
    generic.NotificationType.USER_UPDATE: EmailSettings(
        send_to_template="${email}",
        subject_template="Request for account update on '${hostname}' submitted",
        body_template_file="user.update.template",
    ),
    generic.NotificationType.UNKNOWN: EmailSettings(
        send_to_template="${admin_email}",
        subject_template="Unknown notification type",
        body_template_file="unknown.template",
    ),
}


class Notifier(generic.Notifier):
    """Implementation of an email notifier for deployment requests."""

    def __init__(self) -> None:
        """Initialise SMTP notifier."""
        if CONFIG.notifier.email is None:
            raise FatalError("Email notifier is not configured")
        self.smtp_server = CONFIG.notifier.email.smtp_server
        self.smtp_port = CONFIG.notifier.email.smtp_port
        self.admin_email = CONFIG.notifier.email.admin_email
        self.sent_from = CONFIG.notifier.email.sent_from
        self.sent_from_password = CONFIG.notifier.email.sent_from_password
        self.use_ssl = CONFIG.notifier.email.use_ssl
        self.templates_dir = CONFIG.notifier.email.templates_dir

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
        notification_type: generic.NotificationType,
        data: dict,
        **_ignored: dict,
    ):
        """Sends out an email notification.

        Args:
            notification_type (generic.NotificationType): type of notification
            data (dict): data to use in email template
        Returns:
            bool: True if notification was sent, False otherwise
        """
        if notification_type == generic.NotificationType.NONE:
            logger.info("Notification type is NONE, not sending email")
            return False
        data = {**data, "admin_email": self.admin_email}
        send_to = generic.NotificationTemplate(
            EMAIL_SETTINGS[notification_type].send_to_template
        ).fill(**data)
        subject = generic.NotificationTemplate(
            EMAIL_SETTINGS[notification_type].subject_template
        ).fill(**data)
        content = generic.NotificationTemplate.load(
            Path(self.templates_dir) / EMAIL_SETTINGS[notification_type].body_template_file
        ).fill(**data)
        email = self._build_email(send_to, subject, content)
        self._send_email(email)
        return True

    def test(self):
        """Send test notification to admin to make sure the configured set-up works."""
        if CONFIG.notifier.email is None:
            raise FatalError("Email notifier is not configured")
        settings = CONFIG.notifier.email.to_dict()
        settings["sent_from_password"] = "*****" if settings["sent_from_password"] else None
        data = {
            "admin_email": CONFIG.notifier.email.admin_email,
            "hostname": CONFIG.login_info.ssh_host,
            "notifier": "email",
            "settings": json.dumps(settings, indent=4),
        }
        self.notify(notification_type=generic.NotificationType.ADMIN_TEST, data=data)
