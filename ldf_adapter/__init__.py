name = 'ldf_adapter'

import logging
from collections import Mapping
from functools import lru_cache
from datetime import timedelta
from itertools import chain

import regex
from unidecode import unidecode

import eduperson

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
        ass = CONFIG['assurance']

        profile = ass.get('profile', '*')
        if (profile == 'cappuccino' and not (self.data.assurance.profile and self.data.assurance.profile.is_cappuchino)) \
           or (profile == 'espresso' and not (self.data.assurance.profile and self.data.assurance.profile.is_espresso)) \
           or profile not in ['cappuccino', 'espresso', '*']:
            raise Rejection(message=("Your assurance profile '{}' is insufficient to access this resource: "
                                     + "At least '{}' required").format(
                                         self.data.assurance.profile, profile))

        uid_uniqueness = ass.get('uid_uniqueness', '*')
        if uid_uniqueness == 'unique' and not self.data.assurance.identifier_uniqueness.uid_is_unique:
            raise Rejection(message="Your UID is not unique enough [missing required value 'ID/unique']")

        eppn_uniqueness = ass.get('eppn_uniqueness', '*')
        if eppn_uniqueness == 'no-reassign' and self.data.assurance.identifier_uniqueness.eppn_is_reassignable:
            raise Rejection(message="Your EPPN must be non-reassignable [missing required value 'ID/eppn-unique-no-reassign']")
        if eppn_uniqueness == 'reassign-1y' \
           and self.data.assurance.identifier_uniqueness.eppn_uniqueness_reassign_period > timedelta(days=365):
            raise Rejection(message=("Your EPPN must be reassignable only after 1-year inactivity "
                                     + "[missing required value 'ID/eppn-unique-reassign-1y']"))

        id_ass = ass.get('identity_assurance', '*')
        if (id_ass == 'low' and not self.data.assurance.identity_assurance.is_low) \
           or (id_ass == 'medium' and not self.data.assurance.identity_assurance.is_medium) \
           or (id_ass == 'high' and not self.data.assurance.identity_assurance.is_high) \
           or id_ass not in ['low', 'high', 'medium', '*']:
            raise Rejection(message=("Your Identity assurance level 'IAP/{}' is insufficient to access this resource: "
                                     + "At least 'IAP/{}' required").format(
                                         self.data.assurance.identity_assurance.level_str, id_ass))

        attr_fresh = ass.get('attribute_freshness', '*')
        if attr_fresh == '1m' and self.data.assurance.attribute_assurance.user_departure_latency > timedelta(days=31):
            raise Rejection(message=("Your attributes do not guarantee enough freshness [missing required value 'ATP/ePA-1m']"))
        if attr_fresh == '1d' and self.data.assurance.attribute_assurance.user_departure_latency > timedelta(days=1):
            raise Rejection(message=("Your attributes do not guarantee enough freshness [missing required value 'ATP/ePA-1d']"))

        if ass.getboolean('local_enterprise_identity', 'False') and not self.data.assurance.identity_assurance.local_enterprise:
            raise Rejection(message=("Your identity assurance does not qualify you "
                                     + "to access the Home Organisation's internal administrative systems "
                                     + "[missing required value 'IAP/local-enterprise']"))

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
                    self.data.username
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

    @property
    @lru_cache(maxsize=None)
    def unique_id(self, allow_question=True):
        """Globally and uniquely identifies the user.

        At least almost. Due to homogenisations, there might be collisions. E.g. the following users
        are all indistinguishable:

        klammer(affe)@https://example.org
        klammer(affe)@https://example.org/oauth-2
        klammer(affe)@https://example.org/oauth/2
        klammer-affe-@https://example.org/oauth-2
        klammer(affe)@http://example.org-oauth-2
        klammer-affe-@example.org-oauth-2
        """
        return self.userinfo.get('eduperson_unique_id') or '{sub}@{iss}'.format(
            sub=self._sub_masked_for_bwidm_eppn(),
            iss=self._iss_masked_for_bwidm_eppn()
        )

    @property
    @lru_cache(maxsize=None)
    def eppn(self):
        return self.userinfo.get('eduperson_principal_name', self.unique_id)

    def _sub_masked_for_bwidm_eppn(self):
        """Replace invalid characters with a dash ('-').

        Usually subjects are only numbers and ascii-chars separeted by dashes, so this should not be
        much of a problem.
        """
        sub = self.userinfo['sub']

        sub = regex.sub('-', '', sub) # Unity does this

        sub = regex.sub('[^a-zA-Z0-9_!#$%&*+/=?{|}~^.-]', '-', sub)

        if sub != self.userinfo['sub']:
            logger.warning("Subject '{}' changed to '{}' for BWIDM compatibilty".format(
                self.userinfo['sub'], sub))

        return sub

    def _iss_masked_for_bwidm_eppn(self):
        """Strip URI-scheme, transliterate to ASCII and replace invalid characters with a dash ('-').

        Usually there is only one issuer per FQDN (which is mostly left untouched, apart from
        transliteration, since most FQDNS consist only of alphanumerics, dashes and dots), so this
        should not be much of a problem.
        """
        stripped_iss = regex.sub('^https?://', '', self.userinfo['iss'])
        stripped_iss = regex.sub('/.*$', '', stripped_iss) # Unity does this
        iss = unidecode(stripped_iss)
        iss = regex.sub('[^a-zA-Z0-9.-]', '-', iss)

        # We don't consider stripping the http[s]-prefix a change, since we always do that anyway,
        # and there shouldn't be two different issuers `http://example.org' and `https://example.org'.
        if iss != stripped_iss:
            logger.warning("Issuer '{}' changed to '{}' for BWIDM compatibilty".format(
                stripped_iss, iss))

        return iss

    @property
    @lru_cache(maxsize=None)
    def username(self, allow_question=True):
        """Return the user's preferred username, or ask for one if none was provided."""
        return self.value_or_ask(
            self.userinfo.get('preferred_username'), 'username',
            'You have not set a global username preference. Please enter your preferred username.',
            allow_question
        )

    @property
    @lru_cache(maxsize=None)
    def email(self, allow_question=True):
        """Return the user's E-Mail Address."""
        return self.userinfo['email']

    @property
    @lru_cache(maxsize=None)
    def given_name(self, allow_question=True):
        """Return the user's given name. If none is provided, try to extract it from the full name."""
        return (self.userinfo.get('given_name')
                or ' '.join(self.userinfo['name'].split(' ')[:-1]))

    @property
    @lru_cache(maxsize=None)
    def family_name(self, allow_question=True):
        """Return the user's family name. If none is provided, try to extract it from the full name."""
        return (self.userinfo.get('family_name')
                or self.userinfo.get('sn')
                or self.userinfo['name'].split(' ')[-1])

    @property
    @lru_cache(maxsize=None)
    def full_name(self, allow_question=True):
        """Return the user's full name. If none is provided, try to assemple it from the first and given name."""
        return (self.userinfo.get('name')
                or ' '.join(filter(None, [self.given_name, self.family_name])))

    @property
    @lru_cache(maxsize=None)
    def ssh_keys(self, allow_question=True):
        """Return the user's SSH keys."""
        return self.credentials.get('ssh_key', [])

    @property
    def entitlement(self, allow_question=True):
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
    @lru_cache(maxsize=None)
    def groups(self, allow_question=True):
        """Return the homogenised names of the groups the user should be a member of.

        These are extracted from the entitlement. Any additional 'group'-keys in the input are ignored.
        """
        return set(filter(None, [self._group_masked_for_bwidm(grp)
                                 for grp
                                 in chain(self.userinfo.get('groups', []),
                                          *[ent.subgroups + [ent.group] for ent in self.entitlement])]))

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
            logger.warning("Group name '{}' changed to '{}' for BWIDM compatibilty".format(orig_grp, grp))

        return grp

    @property
    @lru_cache(maxsize=None)
    def assurance(self, allow_question=True):
        """Return the assurance levels of the user. See `eduperson.Assurance` for details"""
        return eduperson.Assurance(self.userinfo.get('eduperson_assurance', []))

    def value_or_ask(self, value, answer_name, question_text, allow_question):
        """Return the submitted answer, the default value or raise a questionaire."""
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
