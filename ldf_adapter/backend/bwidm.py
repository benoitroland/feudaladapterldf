# vim: foldmethod=indent : tw=100
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=logging-fstring-interpolation, logging-not-lazy, logging-format-interpolation
# pylint: disable=missing-docstring, too-few-public-methods
"""
BWIDM backend.

See https://git.scc.kit.edu/simon/reg-app.
"""

import logging
import json
from functools import reduce
from time import sleep
import requests
import os
from urllib.parse import urljoin

from ldf_adapter.config import CONFIG
from ldf_adapter import utils
from ldf_adapter.logsetup import jsonlogger

logger = logging.getLogger(__name__)


class BwIdmConnection:
    """Connection to the BWIDM API."""

    def __init__(self, config=None):
        self.session = requests.Session()
        if config:
            self.session.auth = (
                config.backend.bwidm.http_user,
                config.backend.bwidm.http_pass,
            )

        if not CONFIG.backend.bwidm.log_outgoing_http_requests:
            logging.getLogger("requests").setLevel(logging.CRITICAL)
            logging.getLogger("werkzeug").setLevel(logging.CRITICAL)
            logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    def get(self, *url_fragments, **kwargs):
        return self._request("GET", url_fragments, **kwargs)

    def post(self, *url_fragments, **kwargs):
        return self._request("POST", url_fragments, **kwargs)

    def _request(self, method, url_fragments, **kwargs):
        """
        Arguments:
        method -- HTTP Method (type: str)
        url_fragments -- The components of the URL. Each is url-encoded separately and then they are
                         joined with '/'
        fail=True -- Raise exception on non-200 HTTP status
        **kwargs -- Passed to `requests.Request.__init__`
        """
        fail = kwargs.pop("fail", True)

        url_fragments = map(str, url_fragments)
        url_fragments = map(lambda frag: requests.utils.quote(frag, safe=""), url_fragments)
        url = reduce(
            lambda acc, frag: urljoin(acc, frag) if acc.endswith("/") else urljoin(acc + "/", frag),
            url_fragments,
            CONFIG.backend.bwidm.url,
        )

        # logger.debug(f"BWIDM: {url}")
        # logger.debug(f"BWIDM: {kwargs}")
        req = requests.Request(method, url, **kwargs)
        rsp = self.session.send(self.session.prepare_request(req))

        if fail:
            if not rsp.ok:
                logger.error("Server responded with: {}".format(rsp.content.decode("utf-8")))
            rsp.raise_for_status()

        return rsp


BWIDM = BwIdmConnection(CONFIG)


class User:
    ATTR_USERNAME = "urn:oid:0.9.2342.19200300.100.1.1"
    ATTR_ORG_ID = "http://bwidm.de/bwidmOrgId"
    VALUE_USER_ACTIVE = "ACTIVE"
    VALUE_USER_INACTIVE = "ON_HOLD"

    def __init__(self, userinfo):
        self.info = userinfo
        self.primary_group = Group(userinfo.primary_group)
        self.force_username = None

    def exists(self):
        """
        Inactive users ('ON_HOLD') are treated as nonexistent.
        """
        return self._exists() and self._is_active()

    def _exists(self):
        exists = b"no such user" not in self.reg_info(json=False, fail=False)
        logger.debug(
            "User {} {} on service BWIDM".format(
                self.info.unique_id, "exists" if exists else "doesn't exist"
            )
        )
        return exists

    def _is_active(self):
        status = self.reg_info()["userStatus"]
        logger.debug("User {} is {} on service BWIDM".format(self.info.unique_id, status))
        return status == self.VALUE_USER_ACTIVE

    def _is_registered(self):
        """
        find if the user is already registered for a given
        service, identified by its service short name
        """
        # FIXME: Consider putting this request into the global user object (to reduce load on regapp)
        ssn = CONFIG.backend.bwidm.service_name
        registrations = BWIDM.get("external-reg", "find", "externalId", self.info.unique_id)
        # find registrations
        number_of_registrations = 0
        try:
            logger.debug("logging registrations to jsonlog")
            jsonlogger.debug(
                json.dumps(registrations.json, sort_keys=True, indent=4, separators=(",", ": "))
            )
        except TypeError:
            pass
        for reg in registrations.json():
            if reg["serviceShortName"] == ssn:
                if reg["registryStatus"] == "ACTIVE":
                    number_of_registrations += 1
        logger.debug(f"Number of registrations found: {number_of_registrations}")
        if number_of_registrations > 0:
            return True
        return False

    def name_taken(self, name):
        """
        If there is a user for our unique_id with our username, treat the name as available. This
        might happen if the our user is ON_HOLD on the service.
        """
        # TODO: argument "name" was added, check if given "name" (instead of info.username) is taken by *another* user
        logger.debug(f"checking for name taken of {name}")
        users_with_name = BWIDM.get(
            "external-user", "find", "attribute", self.ATTR_USERNAME, name
        ).json()

        other_users_with_name = [
            user for user in users_with_name if user["externalId"] != self.info.unique_id
        ]
        # logger.debug (F"other_users: {other_users_with_name}")
        logger.debug(f"Found {len(other_users_with_name)} with same username")
        # FIXME: Why < ?
        if len(other_users_with_name) < len(users_with_name):
            logger.debug("Username '{}' is reserved for us".format(self.info.username))

        if other_users_with_name:
            logger.error(
                "Username '{}' is already used by\n    {}".format(
                    self.info.username,
                    ",\n    ".join(map(lambda u: u["externalId"], other_users_with_name)),
                )
            )
        else:
            logger.debug("Username '{}' is available".format(name))

        return bool(other_users_with_name)

    def get_username(self):
        """Check if a user exists based on unique_id and return the name"""

        def safe_resp_conversion(resp):
            """Safely convert a response to json"""
            if resp.status_code != 200:
                logger.debug(
                    "Error %d reading from remote: \n%s\n" % (resp.status_code, str(resp.text))
                )
                os._exit(1)  # or raise or return None?
            try:
                resp_json = resp.json()
            except json.JSONDecodeError:
                logging.error("Could not decode json that I obtained from rest server")
                raise
            return resp_json

        username = None
        bwIdmOrgId = ""
        resp = BWIDM.get("external-user", "find", "externalId", self.info.unique_id)
        resp_json = safe_resp_conversion(resp)

        try:
            username = resp_json["attributeStore"]["urn:oid:0.9.2342.19200300.100.1.1"]
            bwIdmOrgId = resp_json["attributeStore"]["http://bwidm.de/bwidmOrgId"]
            logger.debug(f"retuning username: {bwIdmOrgId}_{username}")
            return f"{bwIdmOrgId}_{username}"
        except KeyError as e:
            logger.error("Error: I could not find the username in the database.")
            logger.error("  Most likely the user is not registered for this service\n")
            logger.error(f"  {e}")
            logger.error(json.dumps(resp_json, sort_keys=True, indent=4, separators=(",", ": ")))
        return None

    def set_username(self, username):
        """Update the internal representation of the user with the incoming username"""
        logger.debug(f"set_username: setting {username}")
        self.force_username = username

    def set_prefixed_username(self, prefixed_username):
        """Update the internal representation of the user with the incoming username"""
        bwIdmOrgId = CONFIG.backend.bwidm.org_id
        username = prefixed_username.lstrip(f"{bwIdmOrgId}_")
        self.set_username(username)

    def create(self):
        """Create or activate user."""
        if self._exists() and not self._is_active():
            logger.info("Activating user {unique_id}".format(**self.info))
            BWIDM.get("external-user", "activate", "externalId", self.info.unique_id)
        else:
            logger.info("Creating user {unique_id}".format(**self.info))
            BWIDM.post("external-user", "create", json={"externalId": self.info.unique_id})

    def register(self):
        """register user for the configured service"""

        def get_active_reg_info(ext_id):
            rsp = BWIDM.get("external-reg", "find", "externalId", ext_id)

            try:
                return next(filter(lambda reg: reg["registryStatus"] == "ACTIVE", rsp.json()))
            except StopIteration:
                return {"lastReconcile": None}

        old_reg = get_active_reg_info(self.info.unique_id)
        # We wait until the 'lastReconciled' timestamp changes, which means that our update was sucessfully deployed
        reg = old_reg
        while reg["lastReconcile"] == old_reg["lastReconcile"]:
            sleep(0.3)
            logger.debug(
                "Received registration reconciled at {}. That is not up-to-date. Checking again.".format(
                    reg["lastReconcile"]
                )
            )

            rsp = BWIDM.get(
                "external-reg",
                "register",
                "externalId",
                self.info.unique_id,
                "ssn",
                CONFIG.backend.bwidm.service_name,
            )

            if rsp.status_code == 204:
                reg = get_active_reg_info(self.info.unique_id)
            else:
                reg = rsp.json()

        logger.debug(
            "Registration confirmed reconciled at {}. Looks like the update went through.".format(
                reg["lastReconcile"]
            )
        )
        logger.debug(f"user is now registered: {self._is_registered()}")

    def update(self):
        # FIXME: Consider putting this request into the global user object (to reduce load on regapp)

        self.external_user_update(
            {
                "externalId": self.info.unique_id,
                "eppn": self.info.eppn,
                "email": self.info.email,
                "givenName": self.info.given_name,
                "surName": self.info.family_name,
                "primaryGroup": {"id": self.primary_group.reg_info()["id"]},
                "attributeStore": {
                    self.ATTR_USERNAME: self.force_username or self.info.username,
                    self.ATTR_ORG_ID: CONFIG.backend.bwidm.org_id,
                },
            }
        )
        # if the user is already registered for the service, we're done here
        if not self._is_registered():
            self.register()

        logger.debug(f"user is active: {self._is_active()}")
        logger.debug(f"user is registered: {self._is_registered()}")

    def delete(self):
        """Deregister the user from the given service in BWIDM."""
        BWIDM.get(
            "external-reg",
            "deregister",
            "externalId",
            self.info.unique_id,
            "ssn",
            CONFIG.backend.bwidm.service_name,
        )

    def deactivate(self):
        """Deactivate the user, this does not delete from BWIDM, but sets
        the status to ON_HOLD, thereby disabling the user from ALL
        services."""
        BWIDM.get("external-user", "deactivate", "externalId", self.info.unique_id)

    def mod(self, supplementary_groups=None):
        reg_info = self.reg_info()

        if supplementary_groups is not None:
            current_groups = [grp for grp in reg_info["secondaryGroups"]]
            new_groups = [grp.reg_info(short=True) for grp in supplementary_groups]
            new_groups += [self.primary_group.reg_info()]

            # NL = "\n    "
            # logger.debug(
            #     f"Incoming groups: {NL}{NL.join([g['name'] for g in new_groups])}"
            # )

            # Remove user from groups he should not be a member of
            to_be_removed_from = [
                g for g in current_groups if g["id"] not in (ng["id"] for ng in new_groups)
            ]

            # Only add user to groups she is not already a member of
            to_be_added_to = [
                g for g in new_groups if g["id"] not in (cg["id"] for cg in current_groups)
            ]

            if to_be_removed_from:
                logger.info(
                    "Remove user {} from groups {}".format(
                        self.info.username,
                        ",".join(g["name"] for g in to_be_removed_from),
                    )
                )
            for grp in to_be_removed_from:
                BWIDM.get(
                    "group-admin",
                    "remove",
                    "groupId",
                    grp["id"],
                    "userId",
                    reg_info["id"],
                )

            if to_be_added_to:
                logger.info(
                    "Add user {} to groups {}".format(
                        self.info.username, ",".join(g["name"] for g in to_be_added_to)
                    )
                )
            grp_add_retvals = []
            for grp in to_be_added_to:
                grp_add_retvals.append(
                    BWIDM.get(
                        "group-admin",
                        "add",
                        "groupId",
                        grp["id"],
                        "userId",
                        reg_info["id"],
                        fail=False,
                    )
                )
            if len(grp_add_retvals) > 0:
                logger.debug(f"Group add retvals: {grp_add_retvals}")
            return to_be_added_to, to_be_removed_from
        return [], []

    def install_ssh_keys(self):
        self.external_user_update(
            {
                "externalId": self.info.unique_id,
                "genericStore": {
                    **self.reg_info()["genericStore"],
                    "ssh_key": json.dumps(self.info.ssh_keys),
                },
            }
        )

    def uninstall_ssh_keys(self):
        """Uninstall any SSH keys stored in BWIDM."""
        self.external_user_update(
            {"externalId": self.info.unique_id, "genericStore": {"ssh_key": None}}
        )

    def external_user_update(self, state_updates):
        """Apply new attributes to the user, performing sensible merging of dicts.

        BWIDM is a bit weird about this, due to technical restrictions in the Java-Software stack.

        This comes down to:
        {..., k: val, ...} means `state[k] = val`
        {..., k: None, ...} means `del state[k]` or `state[k]=None`
        {..., k: {}, ...} means no change to k
        {..., k: val={...}, ...} means `state[k]=merge state[k] with val`

        This is applied recursivly.

        """
        current_state = self.reg_info()
        new_state = utils.dictmerge(current_state, state_updates)
        utils.log_dictdiff(utils.dictdiff(current_state, new_state), log_function=logger.info)
        try:
            logger.debug(
                f"current_state: {current_state['attributeStore']['urn:oid:0.9.2342.19200300.100.1.1']}"
            )

            logger.debug(
                f"new_state:     {new_state['attributeStore']['urn:oid:0.9.2342.19200300.100.1.1']}    "
            )
            logger.debug(
                f"state_updates: {state_updates['attributeStore']['urn:oid:0.9.2342.19200300.100.1.1']}"
            )

        except KeyError:
            pass

        for k in list(new_state):
            if new_state[k] is None:
                new_state[k] = {}

        try:
            formatted_json = json.dumps(
                state_updates, sort_keys=True, indent=4, separators=(",", ": ")
            )
            logger.debug("  logging state_updates to jsonlog")
            jsonlogger.debug(f"state_updates:  {formatted_json}")

            formatted_json = json.dumps(
                current_state, sort_keys=True, indent=4, separators=(",", ": ")
            )
            logger.debug("  logging current_state_updates to jsonlog")
            jsonlogger.debug(f"current_state: {formatted_json}")

            logger.debug("  logging new_to jsonlog")
            formatted_json = json.dumps(new_state, sort_keys=True, indent=4, separators=(",", ": "))
            jsonlogger.debug(f"new state for regapp:  {formatted_json}")
        except:
            pass
        BWIDM.post("external-user", "update", json=new_state)

    def reg_info(self, json=True, **kwargs):
        # FIXME: Cache this functions results!
        rsp = BWIDM.get("external-user", "find", "externalId", self.info.unique_id, **kwargs)
        return rsp.json() if json else rsp.content


class Group:
    def __init__(self, name):
        self.name = name

    def exists(self):
        # FIXME: Group existence needs to be checked with using also
        # CONFIG.backend.bwidm.service_name
        return (
            b"no such group"
            not in BWIDM.get("group-admin", "find", "name", self.name, fail=False).content
        )

    def create(self):
        rsp = BWIDM.get(
            "group-admin", "create", CONFIG.backend.bwidm.service_name, self.name
        ).json()

        if self.name != rsp["name"]:
            logger.warning(
                "Groupname changed from {} to {} by BWIDM".format(self.name, rsp["name"])
            )
            self.name = rsp["name"]

        self.id = rsp["id"]

    def delete(self):
        # groupdel
        raise NotImplementedError("Do we even need this function?")

    def mod(self):
        # groupmod
        raise NotImplementedError("Do we even need this function?")

    def reg_info(self, json=True, short=False, **kwargs):
        rsp = BWIDM.get(
            "group-admin",
            "find" if short else "find-detail",
            "name",
            self.name,
            **kwargs,
        )
        return rsp.json() if json else rsp.content

    @property
    def members(self):
        raise NotImplementedError("Do we even need this function?")
