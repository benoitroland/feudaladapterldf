# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=wrong-import-order
# pylint: disable=redefined-outer-name, logging-not-lazy, logging-format-interpolation
# pylint: disable=missing-docstring, trailing-whitespace, trailing-newlines, too-few-public-methods

import os
import sys
from dataclasses import dataclass, fields, field
from typing import Optional, List

from feudal_globalconfig import globalconfig
from configparser import ConfigParser
from pathlib import Path
import logging

from ldf_adapter.utils import to_bool, to_int, to_list

logger = logging.getLogger(__name__)


PARSE_CMDLINE_PARAMETERS = True
if "pytest" in sys.modules:
    PARSE_CMDLINE_PARAMETERS = False
else:
    try:
        PARSE_CMDLINE_PARAMETERS = globalconfig.config["parse_commandline_args"]
    except KeyError as e:
        pass

if PARSE_CMDLINE_PARAMETERS:
    from ldf_adapter.cmdline_params import args


def reload_parser() -> ConfigParser:
    """Reload configuration from disk.

    Config locations, by priority:
    --config option (defaults to /etc/feudal/feudal_adapter.conf)
    $FEUDAL_ADAPTER_CONFIG
    ./feudal_adapter.conf
    ~/.config/feudal/feudal_adapter.conf
    /etc/feudal/feudal_adapter.conf

    processing is stopped, once a give file is found
    """

    files = []

    # If the program has arguments with a config_file: prefer it:
    if PARSE_CMDLINE_PARAMETERS:
        files.insert(0, Path(args.config_file))

    # If the caller of the library has provided a configfile: prefer it:
    logger.debug(f"Files: {files}")
    try:
        globalconf_conf_file = Path(globalconfig.config["CONFIGFILE"])
        logger.debug(f"Trying config of globalconfig: {globalconfig.config['CONFIGFILE']}")
        if globalconf_conf_file.exists():
            files.insert(0, globalconf_conf_file)
    except KeyError:
        pass

    # Finally, check the environment (last means highes priority)
    filename = os.environ.get("FEUDAL_ADAPTER_CONFIG")
    if filename is None:
        filename = os.environ.get("LDF_ADAPTER_CONFIG")
    if filename:
        files.append(Path(filename))

    # default files
    files += [
        Path("feudal_adapter.conf"),
        Path.home() / ".config" / "feudal_adapter.conf",
        Path.home() / ".config" / "feudal" / "feudal_adapter.conf",
        Path("/etc/feudal/feudal_adapter.conf"),
        Path("ldf_adapter.conf"),
        Path.home() / ".config" / "ldf_adapter.conf",
        Path.home() / ".config" / "feudal" / "ldf_adapter.conf",
        Path("/etc/feudal/ldf_adapter.conf"),
    ]

    cp = ConfigParser()
    config_loaded = False
    for f in files:
        if f.exists():
            files_read = cp.read(f)
            logger.debug(f"Using this config file: {files_read}")
            globalconfig.info = {}
            globalconfig.info["config_files_read"] = files_read
            config_loaded = True
            break
    if not config_loaded:
        logger.warning("Could not find any config file")
        logger.debug("Trying to copy config from globalconfig")
        logger.debug(f"type of CONFIG: {type(cp)}")
        # try:
        #     logger.debug(F"type of globalconfig.config['CONFIG']: {type(globalconfig.config['CONFIG'])}")
        # except KeyError:
        # raise Failure(message="Could not find any config (neither file not in globalconfig)")
        logger.error("Could not find any config (neither file not in globalconfig")
        exit(4)
    return cp


@dataclass
class ConfigSection:
    @classmethod
    def __section__name__(cls):
        return "DEFAULT"

    @classmethod
    def load(cls, config: ConfigParser):
        """Sets only the fields that are present in the config file"""
        try:
            return cls(**config[cls.__section__name__()])
        except KeyError:
            logger.debug(
                "Missing config section %s, using default values.", cls.__section__name__()
            )
            return cls()

    def __post_init__(self):
        """Converts some of the fields to the correct type"""
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            field_type = field.type
            if field.type.__module__ == "typing":
                if field.type.__str__().startswith(
                    "typing.Optional"
                ) or field.type.__str__().startswith("typing.Union"):
                    field_type = field.type.__args__[0]  # get the type of the field
                elif field.type.__str__().startswith("typing.List"):
                    field_type = list  # treat as a list
                else:
                    return  # no conversion
            # if the field does not have the hinted type, convert it if possible
            if not isinstance(value, field_type):
                if field_type == int:
                    setattr(self, field.name, to_int(value))
                if field_type == bool:
                    setattr(self, field.name, to_bool(value))
                if field_type in [List, List[str], list]:
                    setattr(self, field.name, to_list(value))

    def to_dict(self) -> dict:
        """Converts the config to a dict"""
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass
class ConfigListOfSections:
    @classmethod
    def load(cls, config: ConfigParser):
        """Loads all config sub-sections that start with the given section name"""
        sections = {}
        for field in fields(cls):
            try:
                field_type = field.type.__args__[0]  # assume Optional[ConfigSection]
            except:
                field_type = field.type
            field_name = field.name
            subsection = field_type.__section__name__()
            if subsection in config:
                sections[field_name] = field_type.load(config)
            else:
                logger.debug(f"Missing config section [{subsection}].")
        return cls(**sections)

    def to_dict(self) -> dict:
        """Converts the config to a dict"""
        return {
            field.name: getattr(self, field.name).to_dict()
            for field in fields(self)
            if field is not None
        }


@dataclass
class ConfigLdfAdapter(ConfigSection):
    """Config section for ldf_adapter."""

    backend: str = "local_unix"
    backend_supports_preferring_existing_user: bool = False
    primary_group: Optional[str] = None
    fallback_group: Optional[str] = None
    additional_groups: list = field(default_factory=list)
    interactive: bool = False

    @classmethod
    def __section__name__(cls):
        return "ldf_adapter"


@dataclass
class ConfigMessages(ConfigSection):
    """Config section for messages. Selects which information will be logged"""

    log_file: str = "/var/log/feudal/adapter.log"
    log_level: Optional[str] = None
    log_to_console: str = ""
    log_name_changes: bool = True
    log_primary_group_definition: bool = True
    log_username_creation: bool = False

    @classmethod
    def __section__name__(cls):
        return "messages"


@dataclass
class ConfigApproval(ConfigSection):
    """Config section for approval workflow"""

    enabled: bool = False
    user_db_location: str = "/var/lib/feudal/pending_users.db"
    notifier: str = "email"

    @classmethod
    def __section__name__(cls):
        return "approval"


@dataclass
class ConfigEmail(ConfigSection):
    """Config section for email notifier"""

    smtp_server: str = "localhost"
    smtp_port: int = 25
    use_ssl: bool = False
    sent_from: str = "admin@localhost"
    sent_from_password: Optional[str] = None
    admin_email: str = "admin@localhost"
    templates_dir: str = "/etc/feudal/templates"

    @classmethod
    def __section__name__(cls):
        return "notifier.email"


@dataclass
class ConfigCourier(ConfigSection):
    """Config section for courier notifier"""

    api_key: str = "foo"

    @classmethod
    def __section__name__(cls):
        return "notifier.courier"


@dataclass
class ConfigAssurance(ConfigSection):
    """Config section for assurance"""

    prefix: str = "https://refeds.org/assurance/"
    require: str = "profile/cappuccino"
    verified_undeploy: bool = False
    skip: bool = False

    @classmethod
    def __section__name__(cls):
        return "assurance"


@dataclass
class ConfigUsernameGenerator(ConfigSection):
    """Config section for username generation"""

    mode: str = "friendly"
    pool_prefix: Optional[str] = None
    pool_digits: int = 3
    strip_sub_groups: bool = False

    @classmethod
    def __section__name__(cls):
        return "username_generator"


@dataclass
class ConfigLoginInfo(ConfigSection):
    """Config section for login information"""

    description: str = "Local SSH Test Service"
    login_help: str = "Login via `mccli ssh {ssh_host}`"
    ssh_host: str = "localhost"

    @classmethod
    def __section__name__(cls):
        return "login_info"


@dataclass
class ConfigLocalUnix(ConfigSection):
    """Config section for local unix backend"""

    shell: str = "/bin/sh"
    home_base: str = "/home"
    deploy_user_ssh_keys: bool = True
    punch4nfdi: bool = False

    @classmethod
    def __section__name__(cls):
        return "backend.local_unix"

    def __post_init__(self):
        super().__post_init__()
        self.home_base.rstrip("/")


@dataclass
class ConfigBwIdm(ConfigSection):
    """Config section for bwIDM backend"""

    url: str = "https://bwidm-test.scc.kit.edu/rest"
    org_id: str = "fdl"
    http_user: str = "foo"
    http_pass: str = "bar"
    service_name: str = "sshtest"
    log_outgoing_http_requests: bool = False

    @classmethod
    def __section__name__(cls):
        return "backend.bwidm"


@dataclass
class ConfigLdap(ConfigSection):
    """Config section for ldap backend"""

    mode: str = "read_only"
    host: str = "localhost"
    port: Optional[int] = None
    admin_user: Optional[str] = None
    admin_password: Optional[str] = None
    tls: bool = False
    user_base: str = "ou=users,dc=example"
    group_base: str = "ou=groups,dc=example"
    attribute_oidc_uid: str = "gecos"
    attribute_local_uid: str = "uid"
    shell: str = "/bin/sh"
    home_base: str = "/home"
    uid_min: int = 1000
    uid_max: int = 60000
    gid_min: int = 1000
    gid_max: int = 60000

    def __post_init__(self):
        super().__post_init__()
        if self.port is None:
            self.port = 636 if self.tls else 1389
        self.home_base.rstrip("/")

    @classmethod
    def __section__name__(cls):
        return "backend.ldap"


@dataclass
class ConfigVerboseInfoPlugin(ConfigSection):
    """Config section for verbose plugin"""

    active: bool = False
    filename: str = "/tmp/userinfo/userinfo.json"
    dirname: str = "/tmp/userinfo"

    @classmethod
    def __section__name__(cls):
        return "verbose-info-plugin"


# Add more config sections here by inheriting from ConfigSection and providing a __section__name__
# method that returns the section name.
# Then add the section to either one of the ConfigListOfSections below (if it is a subsection, e.g.
# [backend.<new backend name>]), or directly to the root Configuration class below.


@dataclass
class ConfigNotifiers(ConfigListOfSections):
    """Collection of config sections for all notifiers"""

    email: Optional[ConfigEmail] = None
    courier: Optional[ConfigCourier] = None


@dataclass
class ConfigBackends(ConfigListOfSections):
    """Collection of config sections for all backends"""

    local_unix: ConfigLocalUnix = ConfigLocalUnix()
    ldap: ConfigLdap = ConfigLdap()
    bwidm: ConfigBwIdm = ConfigBwIdm()


@dataclass
class Configuration:
    """All configuration settings for the feudal adapter"""

    ldf_adapter: ConfigLdfAdapter = ConfigLdfAdapter()
    messages: ConfigMessages = ConfigMessages()
    approval: ConfigApproval = ConfigApproval()
    notifier: ConfigNotifiers = ConfigNotifiers()
    assurance: ConfigAssurance = ConfigAssurance()
    username_generator: ConfigUsernameGenerator = ConfigUsernameGenerator()
    login_info: ConfigLoginInfo = ConfigLoginInfo()
    backend: ConfigBackends = ConfigBackends()
    verbose_info_plugin: ConfigVerboseInfoPlugin = ConfigVerboseInfoPlugin()

    @classmethod
    def load(cls, config: ConfigParser):
        """Loads all config settings from the given config parser"""
        return cls(**{f.name: f.type.load(config) for f in fields(cls)})


# Load config on import
CONFIG = Configuration.load(reload_parser())
