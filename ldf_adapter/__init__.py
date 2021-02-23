name = 'ldf_adapter'
# vim: foldmethod=indent : tw=100
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=logging-fstring-interpolation, logging-not-lazy, logging-format-interpolation
# pylint: disable=missing-docstring, too-few-public-methods

import logging
from collections import Mapping
from functools import lru_cache
from datetime import timedelta
from itertools import chain
import urllib

import regex
from unidecode import unidecode

from . import eduperson

from . import backend
from .config import CONFIG
from .results import Deployed, NotDeployed, Rejection, Failure, Question, raise_question, Status
from .name_generators import FriendlyNameGenerator

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
        self.data = data if isinstance(data, UserInfo) else UserInfo(data)
        self.service_user = backend.User(self.data)
        self.service_groups = [backend.Group(grp) for grp in self.data.groups]

        if CONFIG.get('ldf_adapter', 'backend_supports_preferring_existing_user', fallback = False):
            if self.service_user.exists():
                self.update_username_from_existing()

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
        ass = CONFIG['assurance']
        prefix = ass['prefix']
        prefix=prefix.rstrip('/') + '/'

        tokens = regex.findall('&|\||\(|\)|[^\s()&|]+', ass['require'])

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
            if len(seq) > 0 and seq[0] == '|':
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
            if len(seq) > 0 and seq[0] == '&':
                seq.pop(0)
                rhs = parse_primary(seq)
                expr = lambda values: lhs(values) and rhs(values)
                return parse_konjunction2(seq, expr)
            else:
                return lhs

        #  PRIMARY -> "(" DISJ ")"
        #          -> ASSURANCE
        def parse_primary(seq):
            if len(seq) > 0 and seq[0] == '(':
                seq.pop(0)
                subexpr = parse_disjunction(seq)
                if len(seq) > 0 and seq.pop(0) != ')':
                    raise ValueError("Missing ')' while parsing")
                return subexpr
            else:
                return parse_assurance(seq)

        #  ASSURANCE -> string
        #            -> "*"
        #            -> "+"
        def parse_assurance(seq):
            value = seq.pop(0)
            if value == '+':
                return lambda values: len(values) > 0
            elif value == '*':
                return lambda values: True
            else:
                value = value if regex.match('https?://', value) else prefix + value
                return lambda values: value in values

        return parse_expr(tokens)

    def reach_state(self, target):
        """Attempt to put the user into the desired state on the configured service.

        Arguments:
        target -- The desired state. One of 'deployed' and 'not_deployed'.
        user -- The user to be deployed/undeployed (type: User)
        """

        username="not yet assigned"
        if self.service_user.exists():
            username = self.service_user.get_username()
        try:
            logger.info(F"Incoming request to reach '{target}' for user with email: '{self.data.email}' ({self.data.unique_id}) username: {username}")
        except AttributeError:
            logger.info(F"Incoming request to reach '{target}' for user with name: '{self.data.full_name}' ({self.data.unique_id}) username: {username}")
        except AttributeError:
            logger.info(F"Incoming request to reach '{target}' for user with unique_id: '{self.data.unique_id}' username: {username}")

        if target == 'deployed':
            if not CONFIG.get('assurance', 'skip', fallback="No") =="Yes, do as I say!":
                if not self.assurance_verifier()(self.data.assurance):
                    raise Rejection(message="Your assurance level is insufficient to access this resource")

            logger.debug(F"User comes with these groups")
            for g in self.service_groups:
                logger.debug(F"    {g.name}")

            return self.deploy()
        elif target == 'not_deployed':
            if not CONFIG.get('assurance', 'skip', fallback="No") =="Yes, do as I say!":
                if not self.assurance_verifier()(self.data.assurance):
                    if not CONFIG.getboolean('assurance', 'verified_undeploy', fallback=False):
                        logger.warning("Assurance level is insufficient. Undeploying anyway.")
                    else:
                        raise Rejection(message="Your assurance level is insufficient to access this resource")
            return self.undeploy()
        elif target == 'get_status':
            return self.get_status()
        elif target == 'resumed':
            return self.resume()
        elif target == 'suspended':
            return self.suspend()
        elif target == 'limited':
            return self.limit()
        else:
            raise ValueError(f"Invalid target state: {target}")

    def deploy(self):
        """Deploy the user.

        Ensure that the user exists, is a member in the right groups (and only in those groups)
        and has the correct credentials installed.

        Return a Deployed result, with a message describing what was done.
        """
        self.ensure_groups_exist()
        was_created = self.ensure_exists()
        new_groups = self.ensure_group_memberships()
        new_credentials = self.ensure_credentials_active()

        what_changed = ''
        if was_created:
            what_changed += 'User was created'
        else:
            # FIXME: a user that was not created might not exist for other reasons.
            #        the code probably relies on Failures rosen.
            #        A "pending" flow might require additional Classes for return
            what_changed += 'User already existed'

        if new_groups:
            what_changed += ' and was added to groups {}'.format(",".join(new_groups))

        what_changed += '.'

        if new_credentials:
            what_changed += ' Credentials {} were activated.'.format(",".join(new_credentials))

        return Deployed(credentials=self.credentials, message=what_changed)

    def undeploy(self):
        """Ensure that the user dosen't exist.

        Return a NotDeployed result with a message saying if the user previously existed.
        """
        username = self.service_user.get_username()
        was_removed = self.ensure_dosent_exist()

        what_changed = ''
        if was_removed:
            what_changed += F"User '{username} ({self.data.unique_id})' was removed."
        else:
            what_changed += F"No user for '{self.data.unique_id}' existed. "+\
                            F"User '{username}' was not changed"

        return NotDeployed(message=what_changed)

    def suspend(self):
        """Ensure that the user is suspended.

        Return a Status result with a message describing what was done.
        """
        was_suspended = self.ensure_suspended()
        what_changed = ''
        if was_suspended:
            # FIXME: I'm not sure if this ought to be self.data.username
            what_changed += F"User '{self.data.unique_id}' was suspended."
            state = "suspended"
        else:
            state = self.get_status().state
            what_changed += F"Suspending user '{self.data.unique_id}' was not possible from the '{state}' state. "+\
                            F"User was not changed."
        return Status(state, message=what_changed)

    def resume(self):
        """Ensure that a suspended user is active again in state 'deployed'.

        Return a Status result with a message describing what was done.
        """
        was_resumed = self.ensure_resumed()
        what_changed = ''
        state = self.get_status().state
        if was_resumed:
            # FIXME: I'm not sure if this ought to be self.data.username
            what_changed += F"User '{self.data.unique_id}' was resumed."
        else:
            what_changed += F"Resuming user '{self.data.unique_id}' was not possible from the '{state}' state. "+\
                            F"User was not changed."
        return Status(state, message=what_changed)

    def limit(self):
        """Ensure that a user has limited access.

        Return a Status result with a message describing what was done.
        """
        was_limited = self.ensure_limited()
        what_changed = ''
        if was_limited:
            # FIXME: I'm not sure if this ought to be self.data.username
            what_changed += F"User '{self.data.unique_id}' was limited."
            state = "limited"
        else:
            state = self.get_status().state
            what_changed += F"Limiting user '{self.data.unique_id}' was not possible from the '{state}' state. "+\
                            F"User was not changed."
        return Status(state, message=what_changed)

    def unlimit(self):
        """Ensure that a limited user is active again in state 'deployed'.

        Return a Status result with a message describing what was done.
        """
        was_unlimited = self.ensure_unlimited()
        what_changed = ''
        if was_unlimited:
            # FIXME: I'm not sure if this ought to be self.data.username
            what_changed += F"User '{self.data.unique_id}' was unlimited."
            state = "deployed"
        else:
            state = self.get_status().state
            what_changed += F"Resuming user '{self.data.unique_id}' was not possible from the '{state}' state. "+\
                            F"User was not changed."
        return Status(state, message=what_changed)

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
        
        msg="No message"
        try:
            if not self.service_user.exists():
                return Status("not_deployed", message=msg)
            msg=F"username {self.service_user.get_username()}"
            if hasattr(self.service_user, "is_rejected"):
                if self.service_user.is_rejected():
                    return Status("rejected", message=msg)
            if hasattr(self.service_user, "is_suspended"):
                if self.service_user.is_suspended():
                    return Status("suspended", message=msg)
            if hasattr(self.service_user, "is_pending"):
                if self.service_user.is_pending():
                    return Status("pending", message=msg)
            if hasattr(self.service_user, "is_limited"):
                if self.service_user.is_limited():
                    return Status("limited", message=msg)
            return Status("deployed", message=msg)
        except Exception as e:
            logger.error(F'User {self.data.unique_id} is in an undefined state.: {e}')
            return Status("unknown", message=msg)

    def ensure_exists(self):
        """Ensure that the user exists on the service.

        If the username is already taken on the service, raise a questionaire for a new one. See
        UserInfo.username for details.

        Also ensure that all info about the user is up to date on the service. This is done
        independently of creating the user, so that the user is updated even if they already existed.

        Return True, if the user didn't exist before.
        """
        logger.debug('Ensuring user {unique_id} exits'.format(**self.data))

        is_new_user = not self.service_user.exists()

        if is_new_user:
            unique_id= self.data.unique_id
            logger.info(F'Creating user for "{unique_id}"')
            username = self.data.username

            # Raise question in case of existing username in case we're interactive
            if CONFIG.getboolean('ldf_adapter', 'interactive', fallback=False): # interactive
                if self.service_user.name_taken(username):
                    logger.info(F'Username "{username}" is already taken, asking user to pick a new one')
                    raise Question(
                        name='username',
                        text=F'Username "{username}" already taken on this service. Please enter another one.'
                    )

            else: # non-interactive
                try:
                    logger.info(F"initial try: {username}")
                except AttributeError:
                    pass
                fng = FriendlyNameGenerator(self.data)
                proposed_name = username if username is not None else fng.suggest_name()
                while self.service_user.name_taken(proposed_name):
                    proposed_name = fng.suggest_name()
                logger.info(F'Using: {proposed_name}')
                if proposed_name is None:
                    raise Rejection(message=F"I cannot create usernames. "
                                    F"The list of tried ones is: {', '.join(fng.tried_names())}.")
                self.service_user.set_username(proposed_name)
            self.service_user.create()
        else: # The user exists
            # Update service_user.name if unique_id already points to a username:
            logger.debug('User for "{unique_id}" already exists. Nothing to do.'.format(**self.data))

        logger.debug(F"  This is a new user: {is_new_user}")

        self.service_user.update()
        return is_new_user

    def update_username_from_existing(self):
        """ Update self.service_user.name, if a user with matching
        unique_id can be found, and if the backend implements 'set_username'
        """
        try:
            existing_username = self.service_user.get_username()
            if existing_username is not None:
                if hasattr(self.service_user, 'set_username'):
                    logger.debug(F"Setting username to {existing_username} ({self.data.unique_id})")
                    self.service_user.set_username(existing_username)
                logger.info(F'Found existing username: {existing_username}')
        except AttributeError:
            # the currently used service_user class has to method get_username
            existing_username = None

    def ensure_dosent_exist(self):
        """Ensure that the user doesn't exist.

        Before deleting them, uninstall all SSH keys, to be sure that they are really gone.

        Return True, if the user existed before.
        """
        if self.service_user.exists():
            self.service_user.username = self.service_user.get_username()
            logger.info(F"Deleting user '{self.service_user.username}' ({self.data.unique_id})")
            # bwIDM requires prior removal of the user, because ssh-key removal triggers an 
            # asyncronous process. If user is removed during that, the user might be only partially
            # removed...
            if CONFIG.get('ldf_adapter','backend', fallback="") == 'bwidm':
                self.service_user.delete()
                self.service_user.uninstall_ssh_keys()
            else:
                self.service_user.uninstall_ssh_keys()
                self.service_user.delete()
            return True
        else:
            logger.debug(F'No user for {self.data.unique_id} did exist. Nothing to do.')
            return False

    def ensure_suspended(self):
        """Ensure that a user is suspended.
        Return True if the user has been suspended.
        """
        status = self.get_status()
        if status.state in ["deployed", "limited"]:
            if hasattr(self.service_user, 'suspend'):
                self.service_user.suspend()
                return True
        logger.debug(F'User {self.data.unique_id} in state {status.state}. Suspending not allowed.')
        return False

    def ensure_limited(self):
        """Ensure that a user has limited access.
        Return True if setting the user is limited.
        """
        status = self.get_status()
        if status.state == "deployed":
            if hasattr(self.service_user, 'limit'):
                self.service_user.limit()
                return True
        logger.debug(F'User {self.data.unique_id} in state {status.state}. Limiting not allowed.')
        return False

    def ensure_resumed(self):
        """Ensure that a user is resumed.
        Return True is the user
        """
        status = self.get_status()
        if status.state == "suspended":
            if hasattr(self.service_user, 'resume'):
                self.service_user.resume()
                return True
        logger.debug(F'User {self.data.unique_id} in state {status.state}. Resuming not allowed.')
        return False

    def ensure_unlimited(self):
        """Ensure that a user is not limited anymore.
        Return True is the user
        """
        status = self.get_status()
        if status.state == "limited":
            if hasattr(self.service_user, 'unlimit'):
                self.service_user.unlimit()
                return True
        logger.debug(F'User {self.data.unique_id} in state {status.state}. Unlimit not allowed.')
        return False

    def ensure_groups_exist(self):
        """Ensure that all the necessary groups exist.

        Create the groups on the service, if necessary.
        """
        for group in filter(lambda grp: not grp.exists(), [self.service_user.primary_group] + self.service_groups):
            logger.info("Creating group {}".format(group.name))
            group.create()

    def ensure_group_memberships(self):
        """Ensure that the user is a member of all the groups in self.service_groups.

        Return the names of all groups the user is now a member of.
        """
        self.service_user.mod(supplementary_groups=self.service_groups)
        return [grp.name for grp in self.service_groups]

    def ensure_credentials_active(self):
        """Install all SSH Keys on the service.

        Return a list of the names/ids of all the keys now active.
        """
        self.service_user.install_ssh_keys()
        return ["ssh:{name}/{id}".format(**key) for key in self.data.ssh_keys]

    @property
    def credentials(self):
        """The Credentials displayed to the user.

        Simply merges all the credentials provided by the service_user with those configured for
        the backend in the config file.

        See Deployed.__init__ for details on how this value is used.

        Relevant config:
        ldf_adapter.backend -- The backend to be used
        backend.{}.login_info -- Everything in this section is merged into the credentials dictionary.
        """
        return {
            **self.service_user.credentials,
            **CONFIG['backend.{}.login_info'.format(CONFIG['ldf_adapter']['backend'])]
        }


class UserInfo(Mapping):
    """Information about the user.

    This serves as a wrapper around the plain userinfo-dict passed to us by FEUDAL, exposing only
    the required information. Provides reconstruction of attributes in case of missing information
    in the userinfo-dict (if possible), homogenisation of the values by mapping them (non-
    bijectively!) to reduced character ranges, without lobotomizing the original input to much, as
    this risks collisions.

    E.g., everything returned by this is compatible with BWIDM, but not necessarily with UNIX
    shadow-utils(7), as the latter has very strict requiremnts which probably one does not want to
    apply to all services. This, if your backend has stricter requirements, you need to perform
    further homogenisation on your own.

    Any change made to values is logged with level WARNING.

    The values are exposed as properties, calculated lazily only when needed (they are cached
    however).  Any instance can also be used as a dict, i.e. `userinfo.foo == userinfo['foo']`.

    All properties (when called as a function) take an optional boolean `allow_question`, indicating
    whether it should be allowed to raise a `Questionaire` if needed.
    """
    def __init__(self, data):
        """
        Arguments:
        data -- Input as recieved by FEUDAL
        """
        self.userinfo = data['user']['userinfo']
        self.answers = data.get('answers', {})
        self.credentials = data['user'].get('credentials', {})
        self.allow_question = CONFIG.getboolean('ldf_adapter', 'interactive', fallback=False)

    @property
    @lru_cache(maxsize=None)
    def size(self):
        the_size = 0
        for x in self.userinfo.keys():
            the_size+=1
        return the_size

    @property
    @lru_cache(maxsize=None)
    def unique_id(self):
        """Globally and uniquely identifies the user.

        This can be easily used to find out the identity of the user in the data source.

        Percent-Encodes subject and issuer and concatenates them with an '@'

        """
        return '{sub}@{iss}'.format(
            sub=self._sub_masked_for_bwidm_extid(),
            iss=self._iss_masked_for_bwidm_extid()
        )

    def _sub_masked_for_bwidm_extid(self):
        return urllib.parse.quote_plus(self.userinfo['sub'])

    def _iss_masked_for_bwidm_extid(self):
        return urllib.parse.quote_plus(self.userinfo['iss'])

    @property
    @lru_cache(maxsize=None)
    def eppn(self):
        """Uniquely identifies the user.

        At least almost. Due to homogenisations, there might be collisions. E.g. the following users
        are all indistinguishable:

        klammer(affe)@https://example.org/oauth-2
        klammer(affe)@https://example.org/oauth/2
        klammer-affe-@https://example.org/oauth-2
        klammer(affe)@http://example.org-oauth-2
        klammer-affe-@example.org-oauth-2
        """
        return '{sub}@{iss}'.format(
            sub=self._sub_masked_for_bwidm_eppn(),
            iss=self._iss_masked_for_bwidm_eppn()
        )

    def _sub_masked_for_bwidm_eppn(self):
        """Replace invalid characters with a dash ('-').

        Usually subjects are only numbers and ascii-chars separeted by dashes, so this should not be
        much of a problem.
        """
        # FIXME: Changing the sub of a user is potentially terrible
        sub = self.userinfo['sub']

        sub = regex.sub('[^a-zA-Z0-9_!#$%&*+/=?{|}~^.-]', '-', sub)

        if sub != self.userinfo['sub']:
            logger.warning("sub '{}' changed to '{}' for BWIDM compatibilty".format(
                self.userinfo['sub'], sub))

        return sub

    def _iss_masked_for_bwidm_eppn(self):
        """Strip URI-scheme, transliterate to ASCII and replace invalid characters with a dash ('-').

        Usually there is only one issuer per FQDN (which is mostly left untouched, apart from
        transliteration, since most FQDNS consist only of alphanumerics, dashes and dots), so this
        should not be much of a problem.
        """
        stripped_iss = regex.sub('^https?://', '', self.userinfo['iss'])
        iss = unidecode(stripped_iss)
        iss = regex.sub('[^a-zA-Z0-9.-]', '-', iss)

        # We don't consider stripping the http[s]-prefix a change, since we always do that anyway,
        # and there shouldn't be two different issuers `http://example.org' and `https://example.org'.
        if iss != stripped_iss:
            if CONFIG.getboolean('messages', 'log_name_changes', fallback=True):
                logger.warning("Issuer '{}' changed to '{}' for BWIDM compatibilty".format(
                    stripped_iss, iss))

        return iss

    @property
    @lru_cache(maxsize=None)
    def username(self):
        """Return the user's name, this may be:
            - preferred_username if that was provided
            - if in interactive mode, we prompt the user
            - otherwise, None"""
        # FIXME: If this function is called, even when there is already a local user with an existing
        # name, this is a bug in the flow, that MUST be fixed
        #
        # Simply not having a "preferred_username" does not mean that we have to bother the user!!!
        # TODO (DG): does this still need to be fixed? it should work => test 

        if self.allow_question:
            return self.value_or_ask(
                self.userinfo.get('preferred_username'), 'username',
                'You have not set a global username preference. Please enter your preferred username.',
                self.allow_question
            )
        return self.userinfo.get('preferred_username', None)

    @property
    @lru_cache(maxsize=None)
    def email(self):
        """Return the user's E-Mail Address."""
        try:
            return self.userinfo['email']
        except KeyError:
            return None

    @property
    @lru_cache(maxsize=None)
    def given_name(self):
        """Return the user's given name. If none is provided, try to extract it from the full name."""
        return (self.userinfo.get('given_name')
                or ' '.join(self.userinfo['name'].split(' ')[:-1]))

    @property
    @lru_cache(maxsize=None)
    def family_name(self):
        """Return the user's family name. If none is provided, try to extract it from the full name."""
        return (self.userinfo.get('family_name')
                or self.userinfo.get('sn')
                or self.userinfo['name'].split(' ')[-1])

    @property
    @lru_cache(maxsize=None)
    def full_name(self):
        """Return the user's full name. If none is provided, try to assemple it from the first and given name."""
        return (self.userinfo.get('name')
                or ' '.join(filter(None, [self.given_name, self.family_name])))

    @property
    @lru_cache(maxsize=None)
    def ssh_keys(self):
        """Return the user's SSH keys."""
        return self.credentials.get('ssh_key', [])

    @property
    def entitlement(self):
        """Return the parsed entitlement attribute of the user. See `eduperson.Entitlement` for details."""
        attr = self.userinfo.get('eduperson_entitlement', [])
        if not isinstance(attr, list):
            attr = [attr]

        def try_entitlement(attr):
            try:
                return eduperson.Entitlement(attr)
            except(ValueError):
                return None

        return filter(lambda x: x, map(try_entitlement, attr))

    @property
    def group(self):
        """Return the unparsed group attribute of the user"""
        attr = self.userinfo.get('groups', [])
        if not isinstance(attr, list):
            attr = [attr]
        return attr

    @property
    @lru_cache(maxsize=None)
    def groups(self):
        """Return the homogenised names of the groups the user should be a member of.
        """
        # A shitty way to see if the entitlement is empty or not:
        if len([x for x in self.entitlement]) == 0:
            logger.debug("Using plain groups from 'groups' claim")
            grouplist = self.groups_from_grouplist()
        else:
            logger.debug("Using aarc-g002 groups from 'entitlements' claim")
            grouplist = self.groups_from_entitlement()
        return ([self._group_masked_for_bwidm(grp) for grp in grouplist])

    def groups_from_entitlement(self):
        """Gropus are extracted from the entitlement. Any additional 'group'-keys in the input are ignored.

        Group names are prefixed with the delegated namespace from the entitlement.
        """
        return set(filter(
            None,
            ['{}_{}'.format(ns, grp) for (ns, grp) in chain.from_iterable(
                 (("-".join([ent.delegated_namespace] + ent.subnamespaces), grp) for grp in ent.all_groups)
                 for ent in self.entitlement)]
        ))
    def groups_from_grouplist(self):
        """Gropus are extracted from the groups claim
        """
        return (set( [grp for grp in self.group]))

    def _group_masked_for_bwidm(self, orig_grp):
        """Convert camelCase to snake_case, fixup beginning of name and replace invalid chars with a dash ('-')"""
        grp = orig_grp

        # camelCase to snake_case
        grp = regex.sub('([a-z])([A-Z])', lambda m: '{}_{}'.format(m.group(1), m.group(2).lower()), grp)

        # Lowercase all
        grp = regex.sub('[A-Z]', lambda m: m.group(0).lower(), grp)

        # Catch remaining chars
        grp = regex.sub('[^a-z0-9-_]', '-', grp)

        # First char has to be [a-z]
        grp = regex.sub('^[-_]*', '', grp)
        grp = regex.sub('^0', 'zero_', grp)
        grp = regex.sub('^1', 'one_', grp)
        grp = regex.sub('^2', 'two_', grp)
        grp = regex.sub('^3', 'three_', grp)
        grp = regex.sub('^4', 'four_', grp)
        grp = regex.sub('^5', 'five_', grp)
        grp = regex.sub('^6', 'six_', grp)
        grp = regex.sub('^7', 'seven_', grp)
        grp = regex.sub('^8', 'eight_', grp)
        grp = regex.sub('^9', 'nine_', grp)

        if grp != orig_grp:
            if CONFIG.getboolean('messages', 'log_name_changes', fallback=True):
                logger.warning("Group name '{}' changed to '{}' for BWIDM compatibilty".format(orig_grp, grp))

        return grp

    @property
    @lru_cache(maxsize=None)
    def assurance(self):
        """Return the assurance levels of the user."""
        return self.userinfo.get('eduperson_assurance', [])

    @property
    @lru_cache(maxsize=None)
    def primary_group(self):
        config_group = CONFIG['ldf_adapter'].get("primary_group")
        if config_group:
            return config_group
        elif len(self.groups) == 1:
            # lousy way to access a set element:
            for group in self.groups:
                return group
        elif len(self.groups) > 1:
            if self.allow_question:
                return self.value_or_ask(
                    self.userinfo.get(0), "primary_group",
                    "You are a member of multiple groups. Please select your desired primary group.",
                    self.allow_question, list(self.groups)
                )
            else: # make something up, regarding the primary group:
                if CONFIG.getboolean('messages', 'log_primary_group_definition', fallback=True):
                    logger.warning("/----- No primary group issue --------------------------------------------\\")
                    logger.warning(F"    We have a user with mutiple primary groups, and no default primary group set in the config.")
                    logger.warning(F"    Furthermore, we are in non-interactive mode, so we can't ask the user.")
                    logger.warning(F"    Therefore, we just take the first group: '{list(self.groups)[0]}'")
                    nl="\n                            "
                    logger.warning(F"    Available groups are: {nl}{nl.join(self.groups)}")
                    logger.warning("\\--------------------------------------------------------------------------------/")
                return list(self.groups)[0]

        else:
            old_answer = self.answers.get("primary_group", None)
            if old_answer is not None:
                return old_answer

            else:  # still no group found.
                fallback_group = CONFIG['ldf_adapter'].get("fallback_group", None)
                if fallback_group:
                    return fallback_group
                else:
                    logger.warning("Not a single group found; This may be ok, depending on the request type")
            # raise Failure(message="No groups in userinfo and no global primary group configured")

    @property
    @lru_cache(maxsize=None)
    def preferred_username(self):
        """Return the prefrred username of the user."""
        return self.userinfo.get('preferred_username', None)



    def value_or_ask(self, value, answer_name, question_text, allow_question, default=None):
        """Return the submitted answer, the default value or raise a questionaire."""
        previous_answer = self.answers.get(answer_name)
        return (previous_answer
                or value
                or (allow_question and raise_question(
                    name=answer_name,
                    text=question_text,
                    default=default,
                )))


    def __str__(self):
        attrs = ("{} = {}".format(k, getattr(UserInfo, k).fget(self)) for k in iter(self))

        return "<UserInfo\n{}\n>".format("\n".join("\t{}".format(attr) for attr in attrs))

    def __getitem__(self, key):
        return getattr(self, key, lambda: (_ for _ in ()).throw(KeyError(key)))

    def __iter__(self):
        return (k for k in dir(UserInfo) if type(getattr(UserInfo, k)) is property)

    def __len__(self):
        sum(1 for _ in filter(lambda k: type(getattr(UserInfo, k)) is property, dir(UserInfo)))

    def __hash__(self):
        return id(self) # Good enough for lru_cache
