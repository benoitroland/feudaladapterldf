"""Information about the user. 
    This serves as a wrapper around the plain userinfo-dict
"""
from collections.abc import Mapping
from functools import lru_cache
from itertools import chain
import urllib
from unidecode import unidecode
import logging
import regex

from ldf_adapter import eduperson
from ldf_adapter.config import CONFIG
from ldf_adapter.results import raise_question

logger = logging.getLogger(__name__)


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
        self.userinfo = data["user"]["userinfo"]
        self.answers = data.get("answers", {})
        self.credentials = data["user"].get("credentials", {})
        self.allow_question = CONFIG.ldf_adapter.interactive

    @property
    def sub(self):
        return self.userinfo["sub"]

    @property
    def iss(self):
        return self.userinfo["iss"]

    @property
    @lru_cache(maxsize=None)
    def size(self):
        the_size = 0
        for x in self.userinfo.keys():
            the_size += 1
        return the_size

    @property
    @lru_cache(maxsize=None)
    def unique_id(self):
        """Globally and uniquely identifies the user.

        This can be easily used to find out the identity of the user in the data source.

        Percent-Encodes subject and issuer and concatenates them with an '@'

        """
        return "{sub}@{iss}".format(
            sub=self._sub_masked_for_bwidm_extid(),
            iss=self._iss_masked_for_bwidm_extid(),
        )

    def _sub_masked_for_bwidm_extid(self):
        return urllib.parse.quote_plus(self.userinfo["sub"])

    def _iss_masked_for_bwidm_extid(self):
        return urllib.parse.quote_plus(self.userinfo["iss"])

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
        return "{sub}@{iss}".format(
            sub=self._sub_masked_for_bwidm_eppn(), iss=self._iss_masked_for_bwidm_eppn()
        )

    def _sub_masked_for_bwidm_eppn(self):
        """Replace invalid characters with a dash ('-').

        Usually subjects are only numbers and ascii-chars separeted by dashes, so this should not be
        much of a problem.
        """
        # FIXME: Changing the sub of a user is potentially terrible
        sub = self.userinfo["sub"]

        sub = regex.sub("[^a-zA-Z0-9_!#$%&*+/=?{|}~^.-]", "-", sub)

        if sub != self.userinfo["sub"]:
            logger.warning(
                "sub '{}' changed to '{}' to avoid confusion".format(self.userinfo["sub"], sub)
            )
        return sub

    def _iss_masked_for_bwidm_eppn(self):
        """Strip URI-scheme, transliterate to ASCII and replace invalid characters with a dash ('-').

        Usually there is only one issuer per FQDN (which is mostly left untouched, apart from
        transliteration, since most FQDNS consist only of alphanumerics, dashes and dots), so this
        should not be much of a problem.
        """
        stripped_iss = regex.sub("^https?://", "", self.userinfo["iss"])
        iss = unidecode(stripped_iss)
        iss = regex.sub("[^a-zA-Z0-9.-]", "-", iss)

        # We don't consider stripping the http[s]-prefix a change, since we always do that anyway,
        # and there shouldn't be two different issuers `http://example.org' and `https://example.org'.
        if iss != stripped_iss:
            if CONFIG.messages.log_name_changes:
                logger.warning(
                    "Issuer '{}' changed to '{}' for general compatibilty".format(stripped_iss, iss)
                )
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
                self.userinfo.get("preferred_username"),
                "username",
                "You have not set a global username preference. Please enter your preferred username.",
                self.allow_question,
            )
        return self.userinfo.get("preferred_username", None)

    @property
    @lru_cache(maxsize=None)
    def email(self):
        """Return the user's E-Mail Address."""
        try:
            return self.userinfo["email"]
        except KeyError:
            return None

    @property
    @lru_cache(maxsize=None)
    def given_name(self):
        """Return the user's given name. If none is provided, try to extract it from the full name."""
        try:
            given_name_from_name = " ".join(self.userinfo["name"].split(" ")[:-1])
        except KeyError:
            given_name_from_name = None
        return self.userinfo.get("given_name") or given_name_from_name or None

    @property
    @lru_cache(maxsize=None)
    def family_name(self):
        """Return the user's family name. If none is provided, try to extract it from the full name."""
        try:
            family_name_from_sn = self.userinfo.get("sn")
        except KeyError:
            family_name_from_name = None

        try:
            family_name_from_name = self.userinfo["name"].split(" ")[-1]
        except KeyError:
            family_name_from_name = None

        return self.userinfo.get("family_name") or family_name_from_sn or family_name_from_name

    @property
    @lru_cache(maxsize=None)
    def full_name(self):
        """Return the user's full name. If none is provided, try to assemple it from the first and given name."""
        return self.userinfo.get("name") or " ".join(
            filter(None, [self.given_name, self.family_name])
        )

    @property
    @lru_cache(maxsize=None)
    def ssh_keys(self):
        """Return the user's SSH keys."""
        return self.credentials.get("ssh_key", [])

    @property
    def entitlement(self):
        """Return the parsed entitlement attribute of the user. See `eduperson.Entitlement` for details."""
        attr = self.userinfo.get("eduperson_entitlement", [])
        if not isinstance(attr, list):
            attr = [attr]

        def try_entitlement(attr):
            try:
                return eduperson.Entitlement(attr)
            except (ValueError):
                return None

        return filter(lambda x: x, map(try_entitlement, attr))

    @property
    def group(self):
        """Return the unparsed group attribute of the user"""
        attr = self.userinfo.get("groups", [])
        if not isinstance(attr, list):
            attr = [attr]
        return attr

    @property
    @lru_cache(maxsize=None)
    def groups(self):
        """Return the homogenised names of the groups the user should be a member of."""
        # A shitty way to see if the entitlement is empty or not:
        if len([x for x in self.entitlement]) == 0:
            logger.debug("Using plain groups from 'groups' claim")
            grouplist = self.groups_from_grouplist()
        else:
            logger.debug("Using aarc-g002 groups from 'entitlements' claim")
            grouplist = self.groups_from_entitlement()
        return [self._group_masked_for_bwidm(grp) for grp in grouplist]

    def groups_from_entitlement(self):
        """Gropus are extracted from the entitlement. Any additional 'group'-keys in the input are ignored.

        Group names are prefixed with the delegated namespace from the entitlement.
        """
        if CONFIG.username_generator.strip_sub_groups:
            logger.debug("Stripping all subgroups")
            return set(
                filter(
                    None,
                    [
                        "{}_{}".format(ns, grp)
                        for (ns, grp) in chain.from_iterable(
                            (
                                (
                                    "-".join([ent.delegated_namespace] + ent.subnamespaces),
                                    grp,
                                )
                                for grp in ent.all_toplevel_groups
                            )
                            for ent in self.entitlement
                        )
                    ],
                )
            )
        return set(
            filter(
                None,
                [
                    "{}_{}".format(ns, grp)
                    for (ns, grp) in chain.from_iterable(
                        (
                            (
                                "-".join([ent.delegated_namespace] + ent.subnamespaces),
                                grp,
                            )
                            for grp in ent.all_groups
                        )
                        for ent in self.entitlement
                    )
                ],
            )
        )

    def groups_from_grouplist(self):
        """Gropus are extracted from the groups claim"""
        return set([grp for grp in self.group])

    def _group_masked_for_bwidm(self, orig_grp):
        """Convert camelCase to snake_case, fixup beginning of name and replace invalid chars with a dash ('-')"""
        grp = orig_grp

        # camelCase to snake_case
        grp = regex.sub(
            "([a-z])([A-Z])",
            lambda m: "{}_{}".format(m.group(1), m.group(2).lower()),
            grp,
        )

        # Lowercase all
        grp = regex.sub("[A-Z]", lambda m: m.group(0).lower(), grp)

        # Catch remaining chars
        grp = regex.sub("[^a-z0-9-_]", "-", grp)

        # First char has to be [a-z]
        grp = regex.sub("^[-_]*", "", grp)
        grp = regex.sub("^0", "zero_", grp)
        grp = regex.sub("^1", "one_", grp)
        grp = regex.sub("^2", "two_", grp)
        grp = regex.sub("^3", "three_", grp)
        grp = regex.sub("^4", "four_", grp)
        grp = regex.sub("^5", "five_", grp)
        grp = regex.sub("^6", "six_", grp)
        grp = regex.sub("^7", "seven_", grp)
        grp = regex.sub("^8", "eight_", grp)
        grp = regex.sub("^9", "nine_", grp)

        if grp != orig_grp:
            if CONFIG.messages.log_name_changes:
                logger.warning(
                    "Group name '{}' changed to '{}' for general compatibilty".format(orig_grp, grp)
                )

        return grp

    @property
    @lru_cache(maxsize=None)
    def assurance(self):
        """Return the assurance levels of the user."""
        return self.userinfo.get("eduperson_assurance", [])

    @property
    @lru_cache(maxsize=None)
    def primary_group(self):
        config_group = CONFIG.ldf_adapter.primary_group
        logger.debug(f"Using configured primary group: {config_group}")
        if config_group:
            return config_group
        elif len(self.groups) == 1:
            # lousy way to access a set element:
            for group in self.groups:
                return group
        elif len(self.groups) > 1:
            if self.allow_question:
                return self.value_or_ask(
                    self.userinfo.get(0),
                    "primary_group",
                    "You are a member of multiple groups. Please select your desired primary group.",
                    self.allow_question,
                    list(self.groups),
                )
            else:  # make something up, regarding the primary group:
                if CONFIG.messages.log_primary_group_definition:
                    logger.warning(
                        "/----- No primary group issue --------------------------------------------\\"
                    )
                    logger.warning(
                        f"    We have a user with mutiple primary groups, and no default primary group set in the config."
                    )
                    logger.warning(
                        f"    Furthermore, we are in non-interactive mode, so we can't ask the user."
                    )
                    logger.warning(
                        f"    Therefore, we just take the first group: '{sorted(list(self.groups))[0]}'"
                    )
                    nl = "\n                            "
                    # logger.warning(F"    Available groups are: {nl}{nl.join(self.groups)}")
                    logger.warning(
                        "\\--------------------------------------------------------------------------------/"
                    )
                return sorted(list(self.groups))[0]

        else:
            old_answer = self.answers.get("primary_group", None)
            if old_answer is not None:
                return old_answer

            else:  # still no group found.
                fallback_group = CONFIG.ldf_adapter.fallback_group
                if fallback_group:
                    return fallback_group
                else:
                    logger.warning(
                        "Not a single group found; This may be ok, depending on the request type"
                    )
            # raise Failure(message="No groups in userinfo and no global primary group configured")

    @property
    @lru_cache(maxsize=None)
    def preferred_username(self):
        """Return the prefrred username of the user."""
        return self.userinfo.get("preferred_username", None)

    def value_or_ask(self, value, answer_name, question_text, allow_question, default=None):
        """Return the submitted answer, the default value or raise a questionaire."""
        previous_answer = self.answers.get(answer_name)
        return (
            previous_answer
            or value
            or (
                allow_question
                and raise_question(
                    name=answer_name,
                    text=question_text,
                    default=default,
                )
            )
        )

    def __str__(self):
        attrs = ("{} = {}".format(k, getattr(UserInfo, k).fget(self)) for k in iter(self))

        return "<UserInfo\n{}\n>".format("\n".join("\t{}".format(attr) for attr in attrs))

    def __getitem__(self, key):
        return getattr(self, key, lambda: (_ for _ in ()).throw(KeyError(key)))

    def __iter__(self):
        return (k for k in dir(UserInfo) if type(getattr(UserInfo, k)) is property)

    def __len__(self):
        return sum(
            1 for _ in filter(lambda k: type(getattr(UserInfo, k)) is property, dir(UserInfo))
        )

    def __hash__(self):
        return id(self)  # Good enough for lru_cache
