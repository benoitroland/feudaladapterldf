name = 'ldf_adapter'

import logging
from collections import Mapping
from functools import lru_cache

import regex

from . import backend
from .config import CONFIG
from .results import Deployed, NotDeployed, Rejection, Failure, Question

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
        """
        self.data = data if isinstance(data, UserInfo) else UserInfo(data)
        self.service_user = backend.User(self.data)
        self.service_groups = [backend.Group(grp) for grp in self.data.groups]

    def reach_state(self, target):
        """Attempt to put the user into the desired state on the configured service.

        Arguments:
        target -- The desired state. One of 'deployed' and 'not_deployed'.
        user -- The user to be deployed/undeployed (type: User)
        """
        if not self.data.assurance.is_accepted():
            raise Rejection(message="Your assurance level is insufficient to access this resource")

        if target == 'deployed':
            return self.deploy()
        elif target == 'not_deployed':
            return self.undeploy()
        else:
            raise ValueError(f"Invalid target state: {target}")

    def deploy(self):
        """Deploy the user.

        Ensure that the user exists, is a member in the right groups (and only in those groups)
        and has the correct credentials installed.

        Return a Deployed result, with a message describing what was done.
        """
        was_created = self.ensure_exists()
        new_groups = self.ensure_group_memberships()
        new_credentials = self.ensure_credentials_active()

        what_changed = ''
        if was_created:
            what_changed += 'User was created'
        else:
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
        was_removed = self.ensure_dosent_exist()

        what_changed = ''
        if was_removed:
            what_changed += 'User was removed.'
        else:
            what_changed += 'User didn\'t exist.'

        return NotDeployed(message=what_changed)

    def ensure_exists(self):
        """Ensure that the user exists on the service.

        If the username is already taken on the service, raise a questionaire for a new one. See
        UserInfo.username for details.

        Also ensure that all info about the user is up to date on the service. This is done
        independently of creating the user, so that the user is updated even if they already existed.

        Return True, if the user didn't exist before.
        """
        if self.service_user.exists():
            logger.debug('User for {unique_id} already exists. Nothing to do.'.format(**self.data))
            created = False

        elif self.service_user.name_taken():
            raise Question(
                name='username',
                text='Username {} already taken on this service. Please enter another one.'.format(
                    self.service_user.name
                )
            )
        else:
            logger.info('Creating user {username} for {unique_id}'.format(**self.data))
            self.service_user.create()
            created = True

        self.service_user.update()
        return created

    def ensure_dosent_exist(self):
        """Ensure that the user doesn't exist.

        Before deleting them, uninstall all SSH keys, to be sure that they are really gone.

        Return True, if the user existed before.
        """
        if self.service_user.exists():
            logger.info('Deleting user {username} of {unique_id}'.format(**self.data))
            self.service_user.uninstall_ssh_keys()
            self.service_user.delete()
            return True
        else:
            logger.debug('No user for {unique_id} did exist. Nothing to do.'.format(**self.data))
            return False

    def ensure_group_memberships(self):
        """Ensure that the user is a member of all the groups in self.service_groups.

        Create the groups on the service, if necessary.

        Return the names of all groups the user is now a member of.
        """
        for group in filter(lambda grp: not grp.exists(), self.service_groups):
            logger.info("Creating group {}".format(group.name))
            group.create()

        self.service_user.mod(supplementary_groups=self.service_groups)
        return [grp.name for grp in self.service_groups]

    def ensure_credentials_active(self):
        """Install all SSH Keys on the service.

        Return a list of the names/ids of all the keys now active.
        """
        self.service_user.install_ssh_keys([key['value'] for key in self.data.ssh_keys])
        return ["ssh_key:{name}/{id}".format(**key) for key in self.data.ssh_keys]

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


### Data preprocessing
class UserInfo(Mapping):
    def __init__(self, data):
        self.userinfo = data['user']['userinfo']
        self.answers = data.get('answers', {})
        self.credentials = data['user'].get('credentials', {})

    @property
    @lru_cache(maxsize=None)
    def unique_id(self, allow_question=True):
        return '{sub}@{iss}'.format(
            sub=self._sub_masked_for_bwidm_eppn(),
            iss=self._iss_masked_for_bwidm_eppn()
        )

    def _sub_masked_for_bwidm_eppn(self):
        sub = regex.sub('[^a-zA-Z0-9_!#$%&*+/=?{|}~^.-]', '-', self.userinfo['sub'])

        if sub != self.userinfo['sub']:
            logger.warning("Subject '{}' changed to '{}' for BWIDM compatibilty".format(
                self.userinfo['sub'], sub))

        return sub

    def _iss_masked_for_bwidm_eppn(self):
        stripped_iss = regex.sub('^https?://', '', self.userinfo['iss'])
        iss = regex.sub('[^a-zA-Z0-9.-]', '-', stripped_iss)

        # We don't consider stripping the http[s]-prefix a change, since we always do that anyway,
        # and there shouldn't be two different issuers `http://example.org' and `https://example.org'.
        if iss != stripped_iss:
            logger.warning("Issuer '{}' changed to '{}' for BWIDM compatibilty".format(
                stripped_iss, iss))

        return iss

    @property
    @lru_cache(maxsize=None)
    def username(self, allow_question=True):
        return self.value_or_ask(
            self.userinfo.get('preferred_username'), 'username',
            'You have not set a global username preference. Please enter your preferred username.',
            allow_question
        )

    @property
    @lru_cache(maxsize=None)
    def email(self, allow_question=True):
        return self.userinfo['email']

    @property
    @lru_cache(maxsize=None)
    def given_name(self, allow_question=True):
        return (self.userinfo.get('given_name')
                or ' '.join(self.userinfo['name'].split(' ')[:-1]))

    @property
    @lru_cache(maxsize=None)
    def family_name(self, allow_question=True):
        return (self.userinfo.get('family_name')
                or self.userinfo.get('sn')
                or self.userinfo['name'].split(' ')[-1])

    @property
    @lru_cache(maxsize=None)
    def full_name(self, allow_question=True):
        return (self.userinfo.get('name')
                or ' '.join(filter(None, [given_name, family_name])))

    @property
    @lru_cache(maxsize=None)
    def ssh_keys(self, allow_question=True):
        return self.credentials.get('ssh_key', [])

    @property
    @lru_cache(maxsize=None)
    def entitlement(self, allow_question=True):
        return EduPersonEntitlement(self.userinfo['eduperson_entitlement'])

    @property
    @lru_cache(maxsize=None)
    def groups(self, allow_question=True):
        return [self._group_masked_for_bwidm(grp) for grp in [self.entitlement.group] + self.entitlement.subgroups]

    def _group_masked_for_bwidm(self, orig_grp):
        grp = orig_grp

        # First char has to be [a-z]
        grp = regex.sub('^[A-Z]', lambda m: m.group(0).lower(), grp)
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
        grp = regex.sub('^[^a-z]', 'bwidm_\0', grp)

        # camelCase to snake_case
        grp = regex.sub('([a-z])([A-Z])', lambda m: '{}_{}'.format(m.group(1), m.group(2).lower()), grp)

        # Catch remaining chars
        grp = regex.sub('[^a-z0-9-_]', '-', grp)

        if grp != orig_grp:
            logger.warning("Group name '{}' changed to '{}' for BWIDM compatibilty".format(orig_grp, grp))

        return grp

    @property
    @lru_cache(maxsize=None)
    def assurance(self, allow_question=True):
        return EduPersonAssurance(self.userinfo['eduperson_assurance'])

    def value_or_ask(self, value, answer_name, question_text, allow_question):
        return (self.answers.get(answer_name)
                or value
                or (allow_question and raise_question(
                    name=answer_name,
                    text=question_text
                )))


    def __str__(self):
        attrs = ("{} = {}".format(k, getattr(UserInfo, k).fget(self, allow_question=False)) for k in iter(self))

        return "<UserInfo\n{}\n>".format("\n".join("\t{}".format(attr) for attr in attrs))

    def __getitem__(self, key):
        return getattr(self, key, lambda: (_ for _ in ()).throw(KeyError(key)))

    def __iter__(self):
        return (k for k in dir(UserInfo) if type(getattr(UserInfo, k)) is property)

    def __len__(self, allow_questions=True):
        sum(1 for _ in filter(lambda k: type(getattr(UserInfo, k)) is property, dir(UserInfo)))

    def __hash__(self):
        return id(self) # Good enough for lru_cache

class EduPersonEntitlement:
    # This regex is not compatible with stdlib 're', we need 'regex'!
    # (because of repeated captures, see https://bugs.python.org/issue7132)
    re = regex.compile(
        r'urn:' +
           r'(?P<nid>[^:]+):(?P<delegated_namespace>[^:]+)' +     # Namespace-ID and delegated URN namespace
           r'(:(?P<subnamespace>[^:]+))*?' +                      # Sub-namespaces
        r':group:' +
           r'(?P<group>[^:]+)' +                                  # Root group
           r'(:(?P<subgroup>[^:]+))*?' +                          # Sub-groups
           r'(:role=(?P<role>.+))?' +                             # Role of the user in the deepest group
        r'#(?P<group_authority>.+)'                               # Authoritative soruce of the entitlement (URN)
    )

    def __init__(self, raw):
        match = self.re.fullmatch(raw)

        if not match:
            raise Failure(message="Failed to parse entitlements attribute")

        logger.debug("Parsing entitlement attribute: {}".format(match.capturesdict()))
        try:
            [self.namespace_id] = match.captures('nid')
            [self.delegated_namespace] = match.captures('delegated_namespace')
            self.subnamespaces = match.captures('subnamespace')

            [self.group] = match.captures('group')
            self.subgroups = match.captures('subgroup')
            [self.role] = match.captures('role') or [None]

            [self.group_authority] = match.captures('group_authority')
        except ValueError:
            raise Failure(message="Failed to parse entitlements attribute")

    def __repr__(self):
        return ((
            'urn:{namespace_id}:{delegated_namespace}{subnamespaces}' +
            ':group:{group}{subgroups}{role}' +
            '#{group_authority}'
        ).format(**{
            **self.__dict__, **{
                'subnamespaces': ''.join([':{}'.format(ns) for ns in self.subnamespaces]),
                'subgroups': ''.join([':{}'.format(grp) for grp in self.subgroups]),
                'role': ':role={}'.format(self.role) if self.role else ''
        }}))

    def __str__(self):
        return ((
            '<EduPersonEntitlement' +
            ' namespace={namespace_id}:{delegated_namespace}{subnamespaces}' +
            ' group={group}{subgroups}' +
            '{role}' +
            ' auth={group_authority}>'
        ).format(**{
            **self.__dict__, **{
                'subnamespaces': ''.join([',{}'.format(ns) for ns in self.subnamespaces]),
                'subgroups': ''.join([',{}'.format(grp) for grp in self.subgroups]),
                'role': ' role={}'.format(self.role) if self.role else ''
        }}))

class EduPersonAssurance:
    def __init__(self, level):
        self.level = level

    def is_accepted(self):
        try:
            accepted_levels = [lvl.strip() for lvl in CONFIG['assurance']['accepted_levels'].split(',')]
        except KeyError:
            accepted_levels = None

        accepted_level_regex = regex.compile(CONFIG['assurance'].get('accepted_level_regex', '.*'))

        accepted = True

        if not self.level:
            logger.warning("No assurance level provided. Rejecting.")
            accepted = False

        if accepted_levels is not None and self.level not in accepted_levels:
            logger.warning("Assurance level '{}' is not one of {}. Rejecting.".format(self.level, accepted_levels))
            accepted = False

        if not accepted_level_regex.match(self.level):
            logger.warning("Assurance level '{}' does not match {}. Rejecting.".format(self.level, accepted_level_regex))
            accepted = False

        return accepted

    def __str__(self):
        return ('<EduPersonAssurance level={}>'.format(self.level))

