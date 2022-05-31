from dataclasses import dataclass


_ADMIN_TEMPLATE_DEPLOY_ = """Dear admin,

The following user requests access to the host ${hostname}:
unique_id: ${unique_id}
name: ${full_name}
email: ${email}

If you wish to accept their request, create a local account for them via:
====
${user_cmd}
====

Create the following local groups via:
====
${groups_cmd}
====

And add the user to the following groups groups via:
====
${memberships_cmd}
====

You are free to change the user's local username as needed.

If you wish to accept this deployment as is, go to APPROVE_ENDPOINT.
If you wish to reject the deployment, go to REJECT_ENDPOINT and specify the reason.

Best,
Your humble email bot.
"""

_ADMIN_TEMPLATE_UPDATE_ = """Dear admin,

There has been an update to the following's user request access to the host ${hostname}:
unique_id: ${unique_id}
name: ${full_name}
email: ${email}

If you wish to accept their request, create a local account for them via:
====
${user_cmd}
====

Create the following local groups via:
====
${groups_cmd}
====

And add the user to the following groups groups via:
====
${memberships_cmd}
====

You are free to change the user's local username as needed.

If you wish to accept this deployment as is, go to APPROVE_ENDPOINT.
If you wish to reject the deployment, go to REJECT_ENDPOINT and specify the reason.

Best,
Your humble email bot.
"""


_ADMIN_TEMPLATE_TEST_ = """Dear admin,

This is a test notification for the approval of deployment requests to the host ${hostname}.

If you can read this message, the notification system is configured correctly. Here's a summary of your configuration:

<insert here: notifier, backend, etc.>

Best,
Your humble email bot.
"""


_USER_TEMPLATE_DEPLOY_ = """Dear user,

You are receiving this email because you requested access to ${hostname} for your federated account identified by:

    ${unique_id}

Your request has been submitted for approval to the site admin.

Please check again to see if your request has been accepted. You might NOT be notified if your request has been processed.

Best,
Your humble email bot.
"""

_USER_TEMPLATE_UPDATE_ = """Dear user,

You are receiving this email because there has been an update to your request to access ${hostname} via your federated account identified by:

    ${unique_id}

The updated request has been re-submitted for approval to the site admin.

Please check again to see if your request has been accepted. You might NOT be notified if your request has been processed.

Best,
Your humble email bot.
"""


@dataclass
class MessageTemplateAdmin:
    DEPLOY: str = _ADMIN_TEMPLATE_DEPLOY_
    UPDATE: str = _ADMIN_TEMPLATE_UPDATE_
    TEST: str = _ADMIN_TEMPLATE_TEST_


@dataclass
class MessageTemplateUser:
    DEPLOY: str = _USER_TEMPLATE_DEPLOY_
    UPDATE: str = _USER_TEMPLATE_UPDATE_
