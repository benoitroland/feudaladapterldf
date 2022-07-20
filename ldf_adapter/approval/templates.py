from dataclasses import dataclass


_ADMIN_TEMPLATE_DEPLOY_ = """Dear admin,

The following user requests access to the host '${hostname}':

    unique_id: ${unique_id}
    name: ${full_name}
    email: ${email}

Below are the backend-specific commands to deploy a local account for them.

Creating the necessary local groups:
====
${groups_cmd}
====

Creating the local account:
====
${user_cmd}
====

Adding the user to local groups:
====
${memberships_cmd}
====

You are free to change the user's local username as needed, and fill in any necessary information.

If you wish to accept this deployment as it is using feudal-adapter:
====
echo '{
    "state_target": "accepted",
    "user": {
        "userinfo": {
            "sub": "${sub}",
            "iss": "${iss}"
        }
    }
}' | feudal-adapter
====

If you wish to reject the deployment, fill in the reason for rejection in the command below and execute it:
====
echo '{
    "state_target": "rejected",
    "reason": "",
    "user": {
        "userinfo": {
            "sub": "${sub}",
            "iss": "${iss}"
        }
    }
}' | feudal-adapter
====

Best,
Your humble email bot.
"""

_ADMIN_TEMPLATE_UPDATE_REQUEST_ = """Dear admin,

There has been an update to the following user's request access to the host '${hostname}':

    unique_id: ${unique_id}
    name: ${full_name}
    email: ${email}

Below are the backend-specific commands to create the local account for them.

Creating the necessary local groups:
====
${groups_cmd}
====

Creating the local account:
====
${user_cmd}
====

Adding the user to local groups:
====
${memberships_cmd}
====

Fill in any necessary information.

If you wish to accept this deployment as it is using feudal-adapter:
====
echo '{
    "state_target": "accepted",
    "user": {
        "userinfo": {
            "sub": "${sub}",
            "iss": "${iss}"
        }
    }
}' | feudal-adapter
====

If you wish to reject the deployment, fill in the reason for rejection in the command below and execute it:
====
echo '{
    "state_target": "rejected",
    "reason": "",
    "user": {
        "userinfo": {
            "sub": "${sub}",
            "iss": "${iss}"
        }
    }
}' | feudal-adapter
====

Best,
Your humble email bot.
"""

_ADMIN_TEMPLATE_UPDATE_GROUPS_ = """Dear admin,

There has been an update to the following user's group memberships on host '${hostname}':

    unique_id: ${unique_id}
    name: ${full_name}
    email: ${email}

Below are the backend-specific commands to update the local account for them.

Creating the necessary local groups:
====
${groups_cmd}
====

Adding the user to local groups:
====
${memberships_cmd}
====

Fill in any necessary information.

If you wish to accept this update as it is using feudal-adapter:
====
echo '{
    "state_target": "accepted",
    "user": {
        "userinfo": {
            "sub": "${sub}",
            "iss": "${iss}"
        }
    }
}' | feudal-adapter
====

If you wish to reject the update, fill in the reason for rejection in the command below and execute it:
====
echo '{
    "state_target": "rejected",
    "reason": "",
    "user": {
        "userinfo": {
            "sub": "${sub}",
            "iss": "${iss}"
        }
    }
}' | feudal-adapter
====

Best,
Your humble email bot.
"""

_ADMIN_TEMPLATE_TEST_ = """Dear admin,

This is a test notification for the approval of deployment requests to the host '${hostname}'.

If you can read this message, the notification system is configured correctly. Here's a summary of your configuration:

Notifier: ${notifier}
Settings:
${settings}

Best,
Your humble email bot.
"""


_USER_TEMPLATE_DEPLOY_ = """Dear user,

You are receiving this email because you requested access to '${hostname}' for your federated account identified by:

    sub: ${sub}
    iss: ${iss}

Your request has been submitted for approval to the site admin.

Please check again to see if your request has been accepted. You might NOT be notified if your request has been processed.

Best,
Your humble email bot.
"""

_USER_TEMPLATE_UPDATE_REQUEST_ = """Dear user,

You are receiving this email because there has been an update to your request to access '${hostname}' via your federated account identified by:

    sub: ${sub}
    iss: ${iss}

The updated request has been re-submitted for approval to the site admin.

Please check again to see if your request has been accepted. You might NOT be notified if your request has been processed.

Best,
Your humble email bot.
"""

_USER_TEMPLATE_UPDATE_GROUPS_ = """Dear user,

You are receiving this email because there has been an update to your local group memberships for your account on host '${hostname}', corresponding to the federated account identified by:

    sub: ${sub}
    iss: ${iss}

The update request has been submitted for approval to the site admin. You might NOT be notified if your request has been processed.

Best,
Your humble email bot.
"""


@dataclass
class MessageTemplateAdmin:
    DEPLOY: str = _ADMIN_TEMPLATE_DEPLOY_
    UPDATE_REQUEST: str = _ADMIN_TEMPLATE_UPDATE_REQUEST_
    UPDATE_GROUPS: str = _ADMIN_TEMPLATE_UPDATE_GROUPS_
    TEST: str = _ADMIN_TEMPLATE_TEST_


@dataclass
class MessageTemplateUser:
    DEPLOY: str = _USER_TEMPLATE_DEPLOY_
    UPDATE_REQUEST: str = _USER_TEMPLATE_UPDATE_REQUEST_
    UPDATE_GROUPS: str = _USER_TEMPLATE_UPDATE_GROUPS_
