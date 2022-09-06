name = "eduperson"

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
        r"urn:"
        + r"(?P<nid>[^:]+):(?P<delegated_namespace>[^:]+)"  # Namespace-ID and delegated URN namespace
        + r"(:(?P<subnamespace>[^:]+))*?"  # Sub-namespaces
        + r":group:"
        + r"(?P<group>[^:]+)"  # Root group
        + r"(:(?P<subgroup>[^:]+))*?"  # Sub-groups
        + r"(:role=(?P<role>.+))?"  # Role of the user in the deepest group
        + r"#(?P<group_authority>.+)"  # Authoritative soruce of the entitlement (URN)
    )

    def __init__(self, raw):
        """Parse a raw EduPerson entitlement string in the AARC-G002 format."""
        match = self.re.fullmatch(raw)

        if not match:
            raise ValueError("Invalid entitlement attribute")

        [self.namespace_id] = match.captures("nid")
        [self.delegated_namespace] = match.captures("delegated_namespace")

        self.subnamespaces = match.captures("subnamespace")

        [self.group] = match.captures("group")
        self.subgroups = match.captures("subgroup")
        [self.role] = match.captures("role") or [None]

        [self.group_authority] = match.captures("group_authority")

    def __repr__(self):
        """Serialize the entitlement to the AARC-G002 format.

        This is the inverse to `__init__` and thus `ent_str == repr(Entitlement(ent_str))`
        holds for any valid entitlement.
        """
        return (
            "urn:{namespace_id}:{delegated_namespace}{subnamespaces}"
            + ":group:{group}{subgroups}{role}"
            + "#{group_authority}"
        ).format(
            **{
                **self.__dict__,
                **{
                    "subnamespaces": "".join([":{}".format(ns) for ns in self.subnamespaces]),
                    "subgroups": "".join([":{}".format(grp) for grp in self.subgroups]),
                    "role": ":role={}".format(self.role) if self.role else "",
                },
            }
        )

    def __str__(self):
        """Return the entitlement in human-readable string form."""
        return (
            "<Entitlement"
            + " namespace={namespace_id}:{delegated_namespace}{subnamespaces}"
            + " group={group}{subgroups}"
            + "{role}"
            + " auth={group_authority}>"
        ).format(
            **{
                **self.__dict__,
                **{
                    "subnamespaces": "".join([",{}".format(ns) for ns in self.subnamespaces]),
                    "subgroups": "".join([",{}".format(grp) for grp in self.subgroups]),
                    "role": " role={}".format(self.role) if self.role else "",
                },
            }
        )

    @property
    def all_toplevel_groups(self):
        return ["_".join([self.group])]

    @property
    def all_groups(self):
        return ["_".join([self.group] + self.subgroups)]

    @property
    def full_namespace(self):
        return [self.delegated_namespace] + self.subnamespaces
