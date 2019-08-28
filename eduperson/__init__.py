name = 'eduperson'

import logging

import regex

logger = logging.getLogger(__name__)

class Entitlement:
    """EduPerson Entitlement attribute (de-)serialisation.

    As specified in: https://aarc-project.eu/guidelines/aarc-g002/
    """

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
        """Parse a raw EduPerson entitlement string in the AARC-G002 format."""
        match = self.re.fullmatch(raw)

        if not match:
            raise ValueError("Invalid entitlement attribute")

        [self.namespace_id] = match.captures('nid')
        [self.delegated_namespace] = match.captures('delegated_namespace')

        self.subnamespaces = match.captures('subnamespace')

        [self.group] = match.captures('group')
        self.subgroups = match.captures('subgroup')
        [self.role] = match.captures('role') or [None]

        [self.group_authority] = match.captures('group_authority')

    def __repr__(self):
        """Serialize the entitlement to the AARC-G002 format.

        This is the inverse to `__init__` and thus `ent_str == repr(Entitlement(ent_str))`
        holds for any valid entitlement.
        """
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
        """Return the entitlement in human-readable string form."""
        return ((
            '<Entitlement' +
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


    @property
    def all_groups(self):
        return [self.group] + self.subgroups

    @property
    def full_namespace(self):
        return [self.delegated_namespace] + self.subnamespaces

class Assurance:
    """EduPerson assurance management.

    This is currently only a dummy implementation, verifying the assurance level against a
    preconfigured set of assurances.
    """
    accepted_levels = []

    @classmethod
    def accept(self, level):
        """Accept the given level from now on.

        Arguments:
        level -- The acceptable level (type: Regex/str)
        """
        if self.accepted_levels is not None:
            self.accepted_levels += [level]

    @classmethod
    def accept_all(self):
        """Blindly accept all levels."""
        self.accepted_levels = None

    @classmethod
    def reject_all(self):
        """Reject all levels.

        This resets all calls to `accept`.
        """
        self.accepted_levels = []


    def __init__(self, level):
        """
        Arguments:
        level -- The raw assurance level
        """
        self.level = level

    def is_accepted(self):
        """Return whether the assurance level should be accepted.

        The level has to be one of those previously configured with `Assurance.accept(lvl)`.

        Unacceptable levels are logged at level WARNING.
        """
        logging.debug("Checking {} against {}".format(self.level, self.accepted_levels))
        if self.accepted_levels is None:
            logger.info("Blindly accepting assurance level '{}'".format(self.level))
            return True
        else:
            for accepted_level in self.accepted_levels:
                logging.debug("Checking {} against {}".format(self.level, accepted_level))
                if isinstance(accepted_level, regex.regex.Pattern):
                    logging.debug("{} {}".format(self.level, type(self.level)))
                    if accepted_level.match(self.level):
                        return True
                else:
                    if accepted_level == self.level:
                        return True
            else:
                logger.warning("No assurance level provided. Rejecting.")
                return False

            logger.warning("Assurance level '{}' is not one of {}. Rejecting.".format(
                self.level, self.accepted_levels))
            return False

        # All checks passed
        return True

    def __str__(self):
        return ('<Assurance level={}>'.format(self.level))
