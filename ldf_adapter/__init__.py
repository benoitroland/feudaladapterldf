name = "ldf_adapter"
# vim: tw=100 foldmethod=expr
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=redefined-outer-name, logging-not-lazy, logging-format-interpolation, logging-fstring-interpolation
# pylint: disable=missing-docstring, trailing-whitespace, trailing-newlines, too-few-public-methods

import logging
from feudal_globalconfig import globalconfig

import regex

from ldf_adapter import backend
from ldf_adapter.config import CONFIG
from ldf_adapter.results import (
    Deployed,
    Failure,
    NotDeployed,
    Rejection,
    Question,
    Status,
    FatalError,
)
from ldf_adapter.name_generators import NameGenerator
from ldf_adapter.userinfo import UserInfo
from ldf_adapter.approval import PendingDeployment

logger = logging.getLogger(__name__)


class User:
    """Represents a user, abstracting from the concrete service.

    An abstract User is backed by a service_user and is associated with a set of groups (backed by
    service_groups).

    A user is usually identified on the service not by a username but by `self.data.unique_id` (see
    __init__ for details).
    """

    def __init__(self, data):
        """
        Arguments:
        data -- Information about the user (type: UserInfo or dict)

        Relevant config:
        ldf_adapter.backend -- The name of the backend. See function the `backend` for possible values
        ldf_adapter.primary_group -- The primary group of the user. If empty, one from the
          supplementary groups will be used. If there are multiple, a question will be raised.

        Words of warning: Since the service_user and service_groups are
        backend specific, their structures differ from backend to backend.

        Direct access to them from this __init__ is highly illegal (unless specified)
        Instead: Use self.data
        """
        # Info Display Hack
        if CONFIG.verbose_info_plugin.active:
            try:
                if data["state_target"] == "deployed":
                    import json
                    import os
                    import stat

                    filename = CONFIG.verbose_info_plugin.filename
                    dirname = CONFIG.verbose_info_plugin.dirname
                    try:
                        os.mkdir(dirname)
                        os.chmod(dirname, 0o0777)
                    except:
                        pass
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(
                            data,
                            f,
                            ensure_ascii=False,
                            sort_keys=True,
                            indent=4,
                            separators=(",", ": "),
                        )
                    os.chmod(filename, 0o0666)
                    # os.chmod(filename, stat.S_IREAD || stat.S_IWRITE ||stat.S_IRGRP || stat.S_IWGRP
                    #         || stat.S_IROTH || stat.S_IWOTH)
            except Exception as e:
                logger.error(f"Got an exception in uncritical code: {e}")

        # Proceed as normal
        self.data = data if isinstance(data, UserInfo) else UserInfo(data)
        self.service_user = backend.User(self.data)
        self.service_groups = [backend.Group(grp) for grp in self.data.groups]

        # add additional groups from config
        self.additional_groups = [
            backend.Group(grp)
            for grp in CONFIG.ldf_adapter.additional_groups
            if grp not in self.data.groups
        ]

        if CONFIG.ldf_adapter.backend_supports_preferring_existing_user:
            logger.debug("trying to update user from existing")
            if self.service_user.exists():
                self.update_username_from_existing()

        if CONFIG.approval.enabled:
            # initialise pending deployment and notification system
            self.pending_deployment = PendingDeployment(userinfo=self.data)

        # apply fixes to group names for unix backend
        if CONFIG.ldf_adapter.backend == "local_unix" and hasattr(backend.User, "fix_group_names"):
            for grp in self.service_groups + self.additional_groups:
                grp.fix_group_names()

    def assurance_verifier(self):
        """Produce a suitably function to check if a user is allowed.

        Relevant config:
        assurance.prefix -- The common prefix of all relative assurance claims
        assurance.require -- The boolean expression to be parsed, according to the following
          grammer: `E -> E "&" E | E "|" E | "(" E ")" | string`, where `&` binds stronger than `|`.
          Strings are assurance claims interpreted absolute (if they start with `"http[s]://"`) or
          relative to `assurance.prefix`. The strings "+" and "*" are interpreted specially: "+"
          means "any assurance claim", while "*" means "any claim, or no claim at all". They thus
          differ in their treatment of users without any claims.

        Returns:
        A function taking a set of assurance claims, interpreted absolute. The function returns
        `True`, if the claims satisfy the configured expression (`"assurance.require"`), `False`
        otherwise.
        """
        prefix = CONFIG.assurance.prefix
        prefix = prefix.rstrip("/") + "/"

        tokens = regex.findall("&|\||\(|\)|[^\s()&|]+", CONFIG.assurance.require)

        # We use a simple recursive descent parser to parse parenthesied expressions of strings,
        # composed with '&' (konjunction) and '|' (disjunction). The usual precedence rules apply.
        #
        # Instead of building an AST, we build a tree of nested lambdas, which takes a collection of
        # assurance claims and checks if they satisfy the configured expression

        #  EXPR -> DISJ 'EOF'
        def parse_expr(seq):
            expr = parse_disjunction(seq)
            if len(seq) > 0:
                raise ValueError("Reached end of input while parsing")
            return expr

        #  DISJ -> KONJ DISJ2
        def parse_disjunction(seq):
            lhs = parse_konjunction(seq)
            return parse_disjunction2(seq, lhs)

        #  DISJ2 -> ""
        #        -> "|" KONJ DISJ2
        def parse_disjunction2(seq, lhs):
            if len(seq) > 0 and seq[0] == "|":
                seq.pop(0)
                rhs = parse_konjunction(seq)
                expr = lambda values: lhs(values) or rhs(values)
                return parse_disjunction2(seq, expr)
            else:
                return lhs

        #  KONJ -> PRIMARY KONJ2
        def parse_konjunction(seq):
            lhs = parse_primary(seq)
            return parse_konjunction2(seq, lhs)

        #  KONJ2 -> ""
        #        -> "&" PRIMARY
        def parse_konjunction2(seq, lhs):
            if len(seq) > 0 and seq[0] == "&":
                seq.pop(0)
                rhs = parse_primary(seq)
                expr = lambda values: lhs(values) and rhs(values)
                return parse_konjunction2(seq, expr)
            else:
                return lhs

        #  PRIMARY -> "(" DISJ ")"
        #          -> ASSURANCE
        def parse_primary(seq):
            if len(seq) > 0 and seq[0] == "(":
                seq.pop(0)
                subexpr = parse_disjunction(seq)
                if len(seq) > 0 and seq.pop(0) != ")":
                    raise ValueError("Missing ')' while parsing")
                return subexpr
            else:
                return parse_assurance(seq)

        #  ASSURANCE -> string
        #            -> "*"
        #            -> "+"
        def parse_assurance(seq):
            value = seq.pop(0)
            if value == "+":
                return lambda values: len(values) > 0
            elif value == "*":
                return lambda values: True
            else:
                value = value if regex.match("https?://", value) else prefix + value
                return lambda values: value in values

        return parse_expr(tokens)

    def reach_state(self, target):
        """Attempt to put the user into the desired state on the configured service.

        Arguments:
        target -- The desired state. One of 'deployed' and 'not_deployed'.
        user -- The user to be deployed/undeployed (type: User)
        """

        username = "not yet assigned"
        if self.service_user.exists():
            username = self.service_user.get_username()
        try:
            logger.info(
                f"Incoming request to reach '{target}' for user with email: '{self.data.email}' ({self.data.unique_id}) username: {username}"
            )
        except AttributeError:
            logger.info(
                f"Incoming request to reach '{target}' for user with name: '{self.data.full_name}' ({self.data.unique_id}) username: {username}"
            )

        if target == "deployed":
            if CONFIG.assurance.skip:
                logger.warning(
                    "Assurance checking is disabled: Users with ANY assurance will be authorised"
                )
            elif not self.assurance_verifier()(self.data.assurance):
                raise Rejection(
                    message="Your assurance level is insufficient to access this resource"
                )

            logger.debug(f"User comes with these groups")
            for g in self.service_groups:
                logger.debug(f"    {g.name}")

            return self.deploy()
        elif target == "not_deployed":
            if not CONFIG.assurance.skip and not self.assurance_verifier()(self.data.assurance):
                if not CONFIG.assurance.verified_undeploy:
                    logger.warning("Assurance level is insufficient. Undeploying anyway.")
                else:
                    raise Rejection(
                        message="Your assurance level is insufficient to access this resource"
                    )
            return self.undeploy()
        elif target == "get_status":
            return self.get_status()
        elif target == "resumed":
            return self.resume()
        elif target == "suspended":
            return self.suspend()
        elif target == "limited":
            return self.limit()
        elif target == "accepted":
            return self.accept()
        elif target == "rejected":
            return self.reject()
        elif target == "test":
            return self.test()
        else:
            raise ValueError(f"Invalid target state: {target}")

    def deploy(self):
        """Deploy the user.

        Ensure that the user exists, is a member in the right groups (and only in those groups)
        and has the correct credentials installed.

        Return a Deployed result, with a message describing what was done.
        """
        if CONFIG.approval.enabled and self.pending_deployment.is_rejected():
            return Status(
                state="rejected",
                message="User deployment was rejected. No new deployment request will be sent.",
            )

        self.ensure_groups_exist()
        was_created = self.ensure_exists()
        new_memberships, removed_memberships = self.ensure_group_memberships()
        new_credentials = self.ensure_credentials_active()

        if CONFIG.approval.enabled:
            self.pending_deployment.notify()
            # if user existed
            if self.service_user.exists():
                what_changed = "User already existed"
                if new_memberships != [] or removed_memberships != []:
                    what_changed += ", but groups changed. A request for updating user groups was submitted for approval"
                what_changed += "."
                return Deployed(message=what_changed, credentials=self.credentials)
            # user is pending
            if was_created:
                what_changed = "Request for deployment was submitted for approval."
            elif new_memberships != [] or removed_memberships != []:
                what_changed = "Updated request for deployment was submitted for approval."
            else:
                what_changed = "Request for deployment was already submitted for approval. No new request was sent."
            return Status(state="pending", message=what_changed)
        else:
            what_changed = "User was created" if was_created else "User already existed"
            if new_memberships != []:
                what_changed += " and was added to groups {}".format(",".join(new_memberships))
            if removed_memberships != []:
                what_changed += " and was removed from groups {}".format(
                    ",".join(removed_memberships)
                )
            what_changed += "."
            if new_credentials:
                what_changed += " Credentials {} were activated.".format(",".join(new_credentials))

            return Deployed(credentials=self.credentials, message=what_changed)

    def undeploy(self):
        """Ensure that the user dosen't exist.

        Return a NotDeployed result with a message saying if the user previously existed.
        """
        username = self.service_user.get_username()
        was_removed = self.ensure_doesnt_exist()

        what_changed = ""
        if was_removed:
            what_changed += f"User '{username} ({self.data.unique_id})' was removed."
        else:
            what_changed += (
                f"No user for '{self.data.unique_id}' existed. "
                + f"User '{username}' was not changed"
            )

        return NotDeployed(message=what_changed)

    def suspend(self):
        """Ensure that the user is suspended.

        Return a Status result with a message describing what was done.
        """
        was_suspended = self.ensure_suspended()
        what_changed = ""
        if was_suspended:
            # FIXME: I'm not sure if this ought to be self.data.username
            what_changed += f"User '{self.data.unique_id}' was suspended."
            state = "suspended"
        else:
            state = self.get_status().state
            what_changed += (
                f"Suspending user '{self.data.unique_id}' was not possible from the '{state}' state. "
                + f"User was not changed."
            )
        return Status(state, message=what_changed)

    def resume(self):
        """Ensure that a suspended user is active again in state 'deployed'.

        Return a Status result with a message describing what was done.
        """
        was_resumed = self.ensure_resumed()
        what_changed = ""
        state = self.get_status().state
        if was_resumed:
            # FIXME: I'm not sure if this ought to be self.data.username
            what_changed += f"User '{self.data.unique_id}' was resumed."
        else:
            what_changed += (
                f"Resuming user '{self.data.unique_id}' was not possible from the '{state}' state. "
                + f"User was not changed."
            )
        return Status(state, message=what_changed)

    def limit(self):
        """Ensure that a user has limited access.

        Return a Status result with a message describing what was done.
        """
        was_limited = self.ensure_limited()
        what_changed = ""
        if was_limited:
            # FIXME: I'm not sure if this ought to be self.data.username
            what_changed += f"User '{self.data.unique_id}' was limited."
            state = "limited"
        else:
            state = self.get_status().state
            what_changed += (
                f"Limiting user '{self.data.unique_id}' was not possible from the '{state}' state. "
                + f"User was not changed."
            )
        return Status(state, message=what_changed)

    def unlimit(self):
        """Ensure that a limited user is active again in state 'deployed'.

        Return a Status result with a message describing what was done.
        """
        was_unlimited = self.ensure_unlimited()
        what_changed = ""
        if was_unlimited:
            # FIXME: I'm not sure if this ought to be self.data.username
            what_changed += f"User '{self.data.unique_id}' was unlimited."
            state = "deployed"
        else:
            state = self.get_status().state
            what_changed += (
                f"Resuming user '{self.data.unique_id}' was not possible from the '{state}' state. "
                + f"User was not changed."
            )
        return Status(state, message=what_changed)

    def accept(self):
        """Ensure that a pending request is accepted and the user is in state 'deployed'.

        Return a Status result with a message describing what was done.
        """
        if self.pending_deployment.is_pending() or self.pending_deployment.mod_pending():
            if not hasattr(backend.User, "create_fromstring"):
                raise Failure(
                    message=(
                        "Backend does not support automatic user creation from string."
                        "Follow the instructions in the notification you received to manually create the user."
                    )
                )
            if not hasattr(backend.Group, "create_fromstring"):
                raise Failure(
                    message=(
                        "Backend does not support automatic group creation from string."
                        "Follow the instructions in the notification you received to manually create the group(s)."
                    )
                )
            if not hasattr(backend.User, "mod_fromstring"):
                raise Failure(
                    message=(
                        "Backend does not support automatic user modification from string."
                        "Follow the instructions in the notification you received to manually add the user to groups."
                    )
                )
            self.pending_deployment.accept()
            return Deployed(credentials=self.credentials, message="User request was accepted.")
        elif self.pending_deployment.is_rejected():
            what_changed = "User request was already rejected, cannot accept it."
            logger.debug(what_changed)
            return Status(state="rejected", message=what_changed)
        else:
            what_changed = f"No pending request for user {self.data.unique_id} exists."
            logger.debug(what_changed)
            return Status(state=self.get_status().state, message=what_changed)

    def reject(self):
        """Ensure that a pending request is rejected and the user is in state 'not_deployed'.

        Return a Status result with a message describing what was done.
        """
        if self.pending_deployment.is_pending() or self.pending_deployment.mod_pending():
            self.pending_deployment.reject()
            what_changed = "User deployment request was rejected."
            logger.debug(what_changed)
            return Status(state="rejected", message=what_changed)
        else:
            what_changed = f"No pending request for user {self.data.unique_id} exists."
            logger.debug(what_changed)
            return NotDeployed(message=what_changed)

    def get_status(self):
        """
        Return the current status (that he has in the underlying local user management system)
        User can have these status:
        +--------------+-----------------------------------------------------------------+-----------------+
        | Status       | Comment                                                         | Backend support |
        +--------------+-----------------------------------------------------------------+-----------------+
        +--------------+-----------------------------------------------------------------+-----------------+
        | deployed     | There is an account for the user identified by unique_id        | Mandatory       |
        +--------------+-----------------------------------------------------------------+-----------------+
        | not deployed | There is no account for the user identified by unique_id        | Mandatory       |
        |              | We have no information if there has ever been an account        |                 |
        +--------------+-----------------------------------------------------------------+-----------------+
        | rejected     | This might not be supportable; Depends on the backend           | Optional        |
        +--------------+-----------------------------------------------------------------+-----------------+
        | suspended    | The user with unique_id has been suspended                      | Optional        |
        +--------------+-----------------------------------------------------------------+-----------------+
        | pending      | The creation of the user is pending                             | Optional        |
        +--------------+-----------------------------------------------------------------+-----------------+
        | limited      | The user was limited, typically after being idle for some time  | Optional        |
        +--------------+-----------------------------------------------------------------+-----------------+
        | unknown      | We don't know the status, but at least the user is not deployed | Mandatory       |
        +--------------+-----------------------------------------------------------------+-----------------+
        """

        msg = "No message"
        try:
            if not self.service_user.exists():
                if CONFIG.approval.enabled:
                    if self.pending_deployment.is_pending():
                        return Status("pending", message="User deployment is pending approval.")
                    if self.pending_deployment.is_rejected():
                        return Status("rejected", message="User deployment was rejected.")
                return Status("not_deployed", message=msg)
            msg = f"username {self.service_user.get_username()}"
            if hasattr(self.service_user, "is_suspended"):
                if self.service_user.is_suspended():
                    return Status("suspended", message=msg)
            if hasattr(self.service_user, "is_limited"):
                if self.service_user.is_limited():
                    return Status("limited", message=msg)
            return Status("deployed", message=msg)
        except Exception as e:
            logger.error(f"User {self.data.unique_id} is in an undefined state.: {e}")
            return Status("unknown", message=msg)

    def ensure_exists(self):
        """Ensure that the user exists on the service.

        If the username is already taken on the service, raise a questionaire for a new one. See
        UserInfo.username for details.

        Also ensure that all info about the user is up to date on the service. This is done
        independently of creating the user, so that the user is updated even if they already existed.

        Return True, if the user didn't exist before and there was no pending request for its creation.
        """
        logger.debug(f"Ensuring a local user mapping for {self.data.unique_id} exits")

        is_new_user = (
            not self.service_user.exists()
            if not CONFIG.approval.enabled
            else not self.service_user.exists() and not self.pending_deployment.exists()
        )

        unique_id = self.data.unique_id
        if is_new_user:
            username = self.data.username
            primary_group_name = self.service_user.primary_group.name

            # Raise question in case of existing username in case we're interactive
            if CONFIG.ldf_adapter.interactive:  # interactive
                logger.debug("interactive mode")
                if self.service_user.name_taken(username):
                    logger.info(
                        f'Username "{username}" is already taken, asking user to pick a new one'
                    )
                    raise Question(
                        name="username",
                        text=f'Username "{username}" already taken on this service. Please enter another one.',
                    )

            else:  # non-interactive
                logger.debug("noninteractive mode")
                username_mode = CONFIG.username_generator.mode
                logger.debug(f"username_mode: {username_mode}")
                pool_prefix = CONFIG.username_generator.pool_prefix or primary_group_name

                name_generator = NameGenerator(
                    username_mode, userinfo=self.data, pool_prefix=pool_prefix
                )
                proposed_name = name_generator.suggest_name()
                logger.debug(f"initially proposed_name: {proposed_name}")

                while proposed_name is not None and (
                    self.service_user.name_taken(proposed_name)
                    or (
                        CONFIG.approval.enabled
                        and self.pending_deployment.name_taken(proposed_name)
                    )
                ):
                    proposed_name = name_generator.suggest_name()
                if proposed_name is None:
                    raise Rejection(
                        message=f"I cannot create usernames. "
                        f"The list of tried ones is: {', '.join(name_generator.tried_names())}."
                    )
                self.service_user.set_username(proposed_name)

                logger.info(f"Chose username '{proposed_name}' for {unique_id}")

            logger.debug(f"Primary Group Name: {primary_group_name}")
            logger.debug(f"Primary Group from userinfo: {self.data.primary_group}")

            # Sanity check to ensure user has a primary group:
            if primary_group_name is None:
                config_file_name = globalconfig.info["config_files_read"]
                message = (
                    'User is not member of any group, and neither a "primary_group", nor '
                    f'a "fallback_group" have been defined in the config file {config_file_name}'
                )
                logger.error(message)
                raise FatalError(message=message)

            if CONFIG.approval.enabled:
                self.pending_deployment.create_user(self.service_user)
            else:
                self.service_user.create()
        elif CONFIG.approval.enabled and self.pending_deployment.exists():  # the user is pending
            username = self.pending_deployment.username
            self.service_user.set_username(username)
            logger.info(
                f"Username {username} already assigned to '{self.data.unique_id}' in pending request."
            )
        else:  # The user exists
            # Update service_user.name if unique_id already points to a username:
            username = self.service_user.get_username()
            logger.info(f"User {username} for '{self.data.unique_id}' already exists.")

        logger.debug(f"This is a new user: {is_new_user}")

        if not CONFIG.approval.enabled:
            self.service_user.update()
        return is_new_user

    def update_username_from_existing(self):
        """Update self.service_user.name, if a user with matching
        unique_id can be found, and if the backend implements 'set_username'
        """
        try:
            existing_username = self.service_user.get_username()
            if existing_username is not None:
                if hasattr(self.service_user, "set_username"):
                    logger.debug(f"Setting username to {existing_username} ({self.data.unique_id})")
                    if hasattr(self.service_user, "set_prefixed_username"):
                        logger.debug("calling set_prefixed_username")
                        self.service_user.set_prefixed_username(existing_username)
                    else:
                        logger.debug("calling set_username")
                        self.service_user.set_username(existing_username)
                logger.debug(f"Found an existing username: {existing_username}")
        except AttributeError:
            # the currently used service_user class has to method get_username
            existing_username = None

    def ensure_doesnt_exist(self):
        """Ensure that the user doesn't exist.

        Before deleting them, uninstall all SSH keys, to be sure that they are really gone.

        Return True, if the user existed before.
        """
        if self.service_user.exists():
            self.service_user.username = self.service_user.get_username()
            logger.info(f"Deleting user '{self.service_user.username}' ({self.data.unique_id})")
            # bwIDM requires prior removal of the user, because ssh-key removal triggers an
            # asyncronous process. If user is removed during that, the user might be only partially
            # removed...
            if CONFIG.ldf_adapter.backend == "bwidm":
                self.service_user.delete()
                self.service_user.uninstall_ssh_keys()
            else:
                self.service_user.uninstall_ssh_keys()
                self.service_user.delete()
            return True
        elif CONFIG.approval.enabled and self.pending_deployment.exists():
            logger.info(
                f"No user existed for {self.data.unique_id}, but cleaned up lingering pending/rejected entry for this user."
            )
            self.pending_deployment.remove_data()
            return False
        else:
            logger.info(f"No user existed for {self.data.unique_id}. Nothing to do.")
            return False

    def ensure_suspended(self):
        """Ensure that a user is suspended.
        Return True if the user has been suspended.
        """
        status = self.get_status()
        if status.state in ["deployed", "limited"]:
            if hasattr(self.service_user, "suspend"):
                self.service_user.suspend()
                return True
        logger.debug(f"User {self.data.unique_id} in state {status.state}. Suspending not allowed.")
        return False

    def ensure_limited(self):
        """Ensure that a user has limited access.
        Return True if setting the user is limited.
        """
        status = self.get_status()
        if status.state == "deployed":
            if hasattr(self.service_user, "limit"):
                self.service_user.limit()
                return True
        logger.debug(f"User {self.data.unique_id} in state {status.state}. Limiting not allowed.")
        return False

    def ensure_resumed(self):
        """Ensure that a user is resumed.
        Return True is the user
        """
        status = self.get_status()
        if status.state == "suspended":
            if hasattr(self.service_user, "resume"):
                self.service_user.resume()
                return True
        logger.debug(f"User {self.data.unique_id} in state {status.state}. Resuming not allowed.")
        return False

    def ensure_unlimited(self):
        """Ensure that a user is not limited anymore.
        Return True is the user
        """
        status = self.get_status()
        if status.state == "limited":
            if hasattr(self.service_user, "unlimit"):
                self.service_user.unlimit()
                return True
        logger.debug(f"User {self.data.unique_id} in state {status.state}. Unlimit not allowed.")
        return False

    def ensure_groups_exist(self):
        """Ensure that all the necessary groups exist.

        Create the groups on the service, if necessary.
        Return the names of the groups that were created (or requested to be created).
        """
        group_list = self.service_groups + self.additional_groups
        if self.data.primary_group not in self.data.groups + CONFIG.ldf_adapter.additional_groups:
            group_list.append(self.service_user.primary_group)

        new_groups = []
        for group in filter(lambda grp: not grp.exists() and grp.name is not None, group_list):
            logger.info("Creating group '{}'".format(group.name))
            if CONFIG.approval.enabled:
                if self.pending_deployment.create_group(group):
                    new_groups.append(group.name)
            else:
                group.create()
                new_groups.append(group.name)
        return new_groups

    def ensure_group_memberships(self):
        """Ensure that the user is a member of all the groups in self.service_groups and self.additional_groups.

        Return two lists:
        - the names of all groups the user was added to
        - the names of all groups the user was removed from
        """
        username = self.service_user.get_username()

        group_list = self.service_groups + self.additional_groups
        if self.data.primary_group not in self.data.groups + CONFIG.ldf_adapter.additional_groups:
            group_list.append(self.service_user.primary_group)

        logger.info(
            f"Ensuring user '{username}' ({self.data.unique_id}) is member of these groups: "
            f"{[grp.name for grp in group_list]}"
        )

        if CONFIG.approval.enabled:
            groups_added, groups_removed = self.pending_deployment.mod(
                service_user=self.service_user, supplementary_groups=group_list
            )
            logger.info(
                f"User '{username}' has to be added to the following groups: {groups_added}"
            )
            logger.info(
                f"User '{username}' has to be removed from the following groups: {groups_removed}"
            )
            return groups_added, groups_removed
        else:
            groups_added, groups_removed = self.service_user.mod(supplementary_groups=group_list)
            logger.info(f"User '{username}' was added to the following groups: {groups_added}")
            logger.info(
                f"User '{username}' was removed from the following groups: {groups_removed}"
            )
            return groups_added, groups_removed

    def ensure_credentials_active(self):
        """Install all SSH Keys on the service.

        Return a list of the names/ids of all the keys now active.
        """
        if not CONFIG.approval.enabled:
            self.service_user.install_ssh_keys()
            return ["ssh:{name}/{id}".format(**key) for key in self.data.ssh_keys]
        return []

    @property
    def credentials(self):
        """The Credentials displayed to the user.

        Simply merges all the credentials provided by the service_user with those
        configured in the config file.

        See Deployed.__init__ for details on how this value is used.

        Relevant config:
        login_info -- Everything in this section is merged into the credentials dictionary.
        """
        ssh_user = self.service_user.get_username()
        commandline = "ssh {}@{}".format(ssh_user, CONFIG.login_info.ssh_host)
        return {
            **CONFIG.login_info.to_dict(),
            "ssh_user": ssh_user,
            "commandline": commandline,
        }

    def test(self):
        """Various tests for the admin to check the feudal configuration.

        Test that the notification system is configured correctly if the approval workflow is
        enabled by sending a test notification to the admin.
        """
        if CONFIG.approval.enabled:
            self.pending_deployment.test_notifier()
            msg = "Notification sent successfully."
        else:
            msg = "Approval workflow is not enabled. No notification message was sent."
        logger.info(msg)
        return Status(state="test", message=msg)
