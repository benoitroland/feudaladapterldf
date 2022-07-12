"""
Manages a user and groups via standard UNIX shadow-utils(8).
"""
# vim: foldmethod=expr : tw=100
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=logging-fstring-interpolation, logging-not-lazy, logging-format-interpolation
# pylint: disable=raise-missing-from, missing-docstring, too-few-public-methods

import subprocess
from subprocess import CalledProcessError
from pathlib import Path
from os import chown
from datetime import datetime
import logging

# from typing import Union

import regex
from unidecode import unidecode

from ..config import CONFIG
from ..results import Failure

logger = logging.getLogger(__name__)

DEFAULT_SHELL = "/bin/sh"
DEFAULT_HOME_BASE = "/home"


class User:
    def __init__(self, userinfo):
        """
        Arguments:
        userinfo -- Only these attributes are used:
                `username` (which is passed through `make_shadow_compatible`),
                `primary_group`
                `unique_id`  stored in gecos, used to find the user
                `ssh_keys`
        """
        self.unique_id = userinfo.unique_id
        logger.debug(f"backend processing: {userinfo.unique_id}")
        if self.exists():
            logger.debug(f"This user does actually exist. The name is: {self.get_username()}")
            self.set_username(self.get_username())
        else:
            self.set_username(userinfo.username)

        self.ssh_keys = [key["value"] for key in userinfo.ssh_keys]
        self.primary_group = Group(userinfo.primary_group)
        self.credentials = {}

    @staticmethod
    def ROOT():
        """ROOT directory for user db
        only used for testing purposes, defaults to '/' otherwise"""
        return "/"

    def exists(self):
        """Check wheter a user (identified by the unique_id) exists"""
        return bool(
            self.unique_id
            in [entry["gecos"] for entry in User.__all_passwd_entries("gecos").values()]
        )

    def is_rejected(self):
        """Optional, only if the backend supports it.
        Inform the user whether a user was rejected"""
        return False

    def is_suspended(self):
        """Optional, only if the backend supports it.
        Inform the user whether a user was suspended (e.g. due to a security incident)"""
        if self.exists():
            options = ["-l"]
            try:
                result = subprocess.run(
                    ["chage"] + options + [self.name],
                    stdout=subprocess.PIPE,
                    check=True,
                )
            except CalledProcessError as e:
                msg = (e.stderr or e.stdout or b"").decode("utf-8").strip()
                logger.error(
                    "Error executing '{}': {}".format(" ".join(e.cmd), msg or "<no output>")
                )
                raise Failure(message=f"Cannot get info for user: {msg or '<no output>'}")
            try:
                pattern = regex.compile(r"Account expires\s+: (.*)")
                match = pattern.search(result.stdout.decode("utf-8"))
                if match:
                    expiration_date = match.group(1)
                    if expiration_date == "never":
                        return False
                    expiration_date_sec = int(
                        datetime.strptime(expiration_date, "%b %d, %Y").strftime("%s")
                    )
                    if expiration_date_sec - datetime.now().timestamp() <= 0:
                        return True
            except Exception as e:
                logger.error(e)
                raise Failure(message=f"Could not get: {e or '<no output>'}")
        return False

    def is_pending(self):
        """Optional, only if the backend supports it.
        Inform the user whether his creation is pending"""
        return False

    def is_limited(self):
        """Optional, only if the backend supports it.
        Inform the user whether a user has limited access"""
        # if shell is nologin
        try:
            shell = self.__passwd_entry.get("shell", None)
            return shell in ["/sbin/nologin", "/usr/bin/nologin", "/bin/nologin"]
        except KeyError:
            return False

    def name_taken(self, name):
        """Check if a username is already taken by *another* user"""
        name = make_shadow_compatible(name)
        taken = name in [entry["login"] for entry in User.__all_passwd_entries("login").values()]
        logger.debug(f"name_taken: {taken}")
        return taken and name != self.get_username()

    def get_username(self):
        """Return username based on unique_id"""
        try:
            return User.__all_passwd_entries("gecos")[self.unique_id]["login"]
        except KeyError:
            return None

    def set_username(self, username):
        """Set local username on the service."""
        self.name = make_shadow_compatible(username)

    def create(self):
        logger.debug(f"Creating user '{self.name}' for {self.unique_id} ")
        try:
            shell = CONFIG["backend.local_unix"].get("shell", DEFAULT_SHELL)
            home_base =  CONFIG["backend.local_unix"].get("home_base", DEFAULT_HOME_BASE).rstrip("/")
            subprocess.run(
                [
                    "useradd",
                    "--comment",
                    self.unique_id,
                    "-g",
                    self.primary_group.name,
                    "--shell",
                    shell,
                    "-b",
                    home_base,
                    "-m",
                    self.name,
                ],
                check=True,
            )
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b"").decode("utf-8").strip()
            logger.error("Error executing '{}': {}".format(" ".join(e.cmd), msg or "<no output>"))
            raise Failure(message=f"Cannot create user ({msg or '<no output>'})")

    def update(self):
        self.credentials["ssh_user"] = self.name
        self.credentials["ssh_host"] = CONFIG["backend.local_unix.login_info"].get(
            "ssh_host", "undefined"
        )
        self.credentials["commandline"] = "ssh {}@{}".format(
            self.credentials["ssh_user"], self.credentials["ssh_host"]
        )

    def delete(self):
        if not self.exists():
            raise Failure(message=f"Cannot delete user: no user found for {self.unique_id}.")

        name = self.__passwd_entry["login"]

        try:
            subprocess.run(["/usr/bin/pkill", "-u", name], check=True)
        except CalledProcessError:
            pass
        try:
            subprocess.run(["userdel", name], check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b"").decode("utf-8").strip()
            logger.error("Error executing '{}': {}".format(" ".join(e.cmd), msg or "<no output>"))
            raise Failure(message=f"Cannot delete user: {msg or '<no output>'}")

    def mod(self, supplementary_groups=None):
        """Adds user to given groups.
        param list supplementary_groups: a list of Group objects;
        the corresponding unix groups are assumed to exist.
        """
        options = []
        if supplementary_groups is not None:
            logger.debug(
                "Ensuring user '{}' is member of these groups {}".format(
                    self.name, [g.name for g in supplementary_groups]
                )
            )
            options += ["--groups", ",".join([g.name for g in supplementary_groups])]

        try:
            subprocess.run(["usermod"] + options + [self.name], check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b"").decode("utf-8").strip()
            logger.error("Error executing '{}': {}".format(" ".join(e.cmd), msg or "<no output>"))
            raise Failure(message=f"Cannot modify user: {msg or '<no output>'}")

    def __expire(self, expiration_date=datetime.today().strftime("%Y-%m-%d")):
        options = ["-E", expiration_date]
        try:
            subprocess.run(["chage"] + options + [self.name], check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b"").decode("utf-8").strip()
            logger.error("Error executing '{}': {}".format(" ".join(e.cmd), msg or "<no output>"))
            raise Failure(message=f"Cannot set expiration date for user: {msg or '<no output>'}")

    def suspend(self):
        self.__expire(datetime.today().strftime("%Y-%m-%d"))

    def resume(self):
        self.__expire("-1")

    def __set_shell(self, shell):
        try:
            subprocess.run(["usermod", "-s", shell, self.name], check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b"").decode("utf-8").strip()
            logger.error("Error executing '{}': {}".format(" ".join(e.cmd), msg or "<no output>"))
            raise Failure(message=f"Cannot modify user: {msg or '<no output>'}")

    def limit(self):
        self.__set_shell("/sbin/nologin")

    def unlimit(self):
        shell = CONFIG["backend.local_unix"].get("shell", DEFAULT_SHELL)
        self.__set_shell(shell)

    def install_ssh_keys(self):
        try:
            if len(self.ssh_keys) > 0:
                if CONFIG["backend.local_unix"].getboolean("deploy_user_ssh_keys", True):
                    logger.debug(f"Deploying these ssh keys: {self.ssh_keys}")
                    self.__authorized_keys.parent.mkdir(parents=True, exist_ok=True)
                    self.__authorized_keys.parent.chmod(0o700)
                    chown(self.__authorized_keys.parent, self.__uid, self.__gid)

                    self.__authorized_keys.write_text("\n".join(self.ssh_keys))
                    self.__authorized_keys.chmod(0o600)
                    chown(self.__authorized_keys, self.__uid, self.__gid)
        except IOError as e:
            logger.error(e)
            raise Failure(message=f"Could not write new ssh keys: {e or '<no output>'}")
        except Exception as e:
            logger.error(e)
            raise Failure(message=f"Cannot change owner or permissions: {e or '<no output>'}")

    def uninstall_ssh_keys(self):
        """Remove any SSH keys stored in the users .authorized_keys file."""
        try:
            self.__authorized_keys.unlink()
        except FileNotFoundError:
            pass

    @property
    def __authorized_keys(self):
        return Path(self.__passwd_entry["home"]) / ".ssh" / "authorized_keys"

    @property
    def __uid(self):
        try:
            return int(self.__passwd_entry.get("uid", None))
        except TypeError as e:
            logger.error(e)
            raise Failure(message=f"Could not get uid: {e or '<no output>'}")

    @property
    def __gid(self):
        try:
            return int(self.__passwd_entry.get("gid", None))
        except TypeError as e:
            logger.error(e)
            raise Failure(message=f"Could not get gid: {e or '<no output>'}")

    @property
    def __passwd_entry(self):
        return User.__all_passwd_entries("gecos").get(self.unique_id, {})

    @staticmethod
    def __all_passwd_entries(ID_FIELD="gecos") -> dict:
        PASSWD_PATH = Path(User.ROOT()) / "etc" / "passwd"
        PASSWD_FIELDS = ["login", "pw", "uid", "gid", "gecos", "home", "shell"]

        try:
            raw = PASSWD_PATH.read_text()
        except IOError as e:
            logger.error(e)
            raise Failure(
                message="Could not get information about "
                f"existing users on system: {e or '<no output>'}"
            )
        else:
            # for empty file return empty dict
            if raw.strip() == "":
                return {}
            users = [dict(zip(PASSWD_FIELDS, line.split(":"))) for line in raw.strip().split("\n")]

            # import json
            # thedata={user[ID_FIELD]: user for user in users}
            # str_str = json.dumps(thedata, sort_keys=True, indent=4, separators=(',', ': '))
            # logger.debug(str_str)
            # x = {user[ID_FIELD]: user for user in users}
            # logger.debug(F"whattttt: {x}")
            return {user[ID_FIELD]: user for user in users}


class Group:
    def __init__(self, name):
        logger.debug(F"my own group name: {name}")
        if name is None:
            self.name = None
        else:
            self.original_name = name
            self.name = make_shadow_compatible(name)
            self.name_v004 = make_shadow_compatible_v044(name)

    @staticmethod
    def ROOT():
        """ROOT directory for user db
        only used for testing purposes, defaults to '/' otherwise"""
        return "/"

    def exists(self):
        return bool(self.__group_entry)

    def create(self):
        try:
            subprocess.run(["groupadd", self.name], check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b"").decode("utf-8").strip()
            logger.error("Error executing '{}': {}".format(" ".join(e.cmd), msg or "<no output>"))
            raise Failure(message=f"Cannot create group: {msg or '<no output>'}")

    def delete(self):
        # groupdel
        raise NotImplementedError("Do we even need this function?")

    def mod(self):
        # groupmod
        raise NotImplementedError("Do we even need this function?")

    @property
    def members(self):
        members = self.__group_entry.get("members", [])
        logger.debug(f"GROUP MEMBERS: {members}")
        return self.__group_entry.get("members", [])

    @property
    def __group_entry(self):
        return Group.__all_group_entries().get(self.name, {})


    @staticmethod
    def __rename(original_name, old_name, new_name):
        logger.warning(f"Local group already exists for {original_name} with an old naming convention.")
        logger.warning(f"Renaming group {old_name} to {new_name}.")
        try:
            subprocess.run(["groupmod", "--new-name", new_name, old_name], check=True)
        except CalledProcessError as e:
            msg = (e.stderr or e.stdout or b"").decode("utf-8").strip()
            logger.error("Error executing '{}': {}".format(" ".join(e.cmd), msg or "<no output>"))
            raise Failure(message=f"Cannot create group: {msg or '<no output>'}")

    @staticmethod
    def __fix_duplicates(fix_id, original_name, old_name, new_name):
        logger.error(f"{fix_id}: Two local groups exist for {original_name}, created with different versions of make_shadow_compatible.")
        logger.error(f"{fix_id}: Please make sure all files owned by group {old_name} are owned by group {new_name} before removing group {old_name}.")

    def fix_group_names(self):
        """Apply fix for groups that were created with different make_shadow_compatible versions.

        3 use cases:
        - group with broken name does not exist: nothing to do
        - group with broken name exists, but new name does not exist yet: rename broken group
        - both group names exist: log this for an admin to merge the groups
        """
        if self.name is None or self.name_v004 is None:
            return
        if self.name == self.name_v004:
            return
        all_groups = Group.__all_group_entries()
        if self.name_v004 in all_groups:
            if self.name not in all_groups:
                Group.__rename(self.original_name, self.name_v004, self.name)
            else:
                Group.__fix_duplicates("FIX v0.4.4", self.original_name, self.name_v004, self.name)

    @staticmethod
    def __all_group_entries():
        GROUP_PATH = Path(Group.ROOT()) / "etc" / "group"
        GROUP_FIELDS = ["name", "password", "gid", "members"]
        ID_FIELD = "name"
        LIST_FIELD = "members"

        try:
            raw = GROUP_PATH.read_text()
        except IOError as e:
            logger.error(e)
            raise Failure(
                message="Could not get information about "
                f"existing users on system: {e or '<no output>'}"
            )
        else:
            # for empty file return empty dict
            if raw.strip() == "":
                return {}
            users = [dict(zip(GROUP_FIELDS, line.split(":"))) for line in raw.strip().split("\n")]

            for user in users:
                user[LIST_FIELD] = user[LIST_FIELD].split(",")  # type: ignore

            return {user[ID_FIELD]: user for user in users}


def make_shadow_compatible(orig_word) -> str:
    """Ensure that orig_word is a valid user/group name for standard shadow utils.

    While this could in theory be achived by simply substituting all non-allowed chars with a valid
    one, we try to translitare sensibly, so that usernames look nicer and to avoid collisions. See
    inline comments for further details.

    Any change made to the word is logged with level WARNING.

    """
    if orig_word is None:
        return None
        # For some reason "None" still comes in on the docker-compose setup.
        # raise Failure(message="Cannot use username 'None' in make_shadow_compatible")
    # Encode German Umlauts
    word = orig_word.translate(
        str.maketrans(
            {
                "ä": "ae",
                "ö": "oe",
                "ü": "ue",
                "Ä": "Ae",
                "Ö": "Oe",
                "Ü": "Ue",
                "ß": "ss",
                "!": "i",
                "$": "s",
                "*": "x",
                "@": "_at_",
            }
        )
    )

    # Unicode -> Ascii
    word = unidecode(word)

    # Downcase
    word = word.lower()

    # Das ist der doofe part. Für die ganzen Sonderzeichen gibt es nicht wirklich
    # eine transliterierung in [-0-9_a-z], daher nehme ich einfach underscore,
    # was ggf. zu Kollisionen führen kann. Witzig: Shadow erlaubt '$' im namen,
    # aber nur *ganz* am Ende ...
    # word = regex.sub(r'[^-0-9_a-z]', '_', word[:-1]) + regex.sub(r'[^-0-9_a-z$]', '_', word[-1])
    # since we already replace $ with s, no need to check for $ at the end
    word = regex.sub(r"[^-0-9_a-z]", "_", word)

    # Shadow will das Namen mit Kleinbuchstaben oder Underscore anfangen
    if regex.match(r"^[a-z_]", word):
        word = word
    else:
        if len(word) >= 32:
            word = "_" + word[1:]
        else:
            word = "_" + word

    # usernames and group names can only be 32 characters long.
    # My fix is to remove characters a) after the first '_' if there is one.
    #                                b) from the beginning if there is none
    # Also adds two dots as an indicator for where the shortening took place

    excess_chars = len(word) - 32
    if excess_chars > 0:

        if len(word.split("_")) == 1:  # no '_' found:
            word = "__" + word[excess_chars + 2 :]
            # logger.warning(F"shortened {orig_word} to {word}")

        elif len(word.split("_")) > 1:  # at least one '_' found:
            fragments = word.split("_")
            if (
                len(fragments[1]) > excess_chars
            ):  # we're fine, we can cut excess chars from fragments alone
                fragments[1] = ".." + fragments[1][excess_chars + 2 :]
                # TODO: fix case when len(fragments[1]) == excess_chars + 1
                word = "_".join(fragments)
            else:
                logger.error(f"User or group name is too long: {word} ({len(word)})")
                raise (ValueError)
                # TODO: fix case when removing chars from one fragment is not enough
                # to shorten the word
                # i.e. len(fragments[1] <= excess_chars)
            # logger.warning(F"shortened {orig_word} to {word}")

    if word != orig_word:
        logger.debug("Name '{}' changed to '{}' for shadow compatibilty".format(orig_word, word))

    return word


def make_shadow_compatible_v044(orig_word) -> str:
    """
    This is the function in feudalAdapter v0.4.4, needed here to rollback the side-effects incurred by it.

    Ensure that orig_word is a valid user/group name for standard shadow utils.

    While this could in theory be achieved by simply substituting all non-allowed chars with a valid
    one, we try to transliterate sensibly, so that usernames look nicer and to avoid collisions. See
    inline comments for further details.

    Summary of transliteration process:
    - german umlauts are replaced with their phonetic equivalents
    - a few special characters are replaced by sensible equivalents:
        - ! to i
        - $ to s
        - * to x
        - @ to _at_
    - unicode characters are decoded to ascii
    - all other special characters are replaced with _
    - shortening names longer than 32 chars to 32 as follows:
        - fragments (substrings separated by _) are shortened starting with the first fragment
          until the length 32 is reached
        - a fragment is shortened by removing the necessary amount of characters from the end,
          and adding .. at the end to denote the shortening took place, e.g. "abcdef" -> "abc.."
        - the length of any fragment has to be > 3 to be considered for shortening
        - the first character of a fragment is always kept, ie. the strongest shortening of "abcdef" will be "a.."
        - names that are still longer than 32 chars after this process will raise a ValueError

    Any change made to the word is logged with level WARNING.

    """
    if orig_word is None:
        return None
        # For some reason "None" still comes in on the docker-compose setup. 
        # raise Failure(message="Cannot use username 'None' in make_shadow_compatible")
    # Encode German Umlauts
    word = orig_word.translate(
        str.maketrans(
            {
                "ä": "ae",
                "ö": "oe",
                "ü": "ue",
                "Ä": "Ae",
                "Ö": "Oe",
                "Ü": "Ue",
                "ß": "ss",
                "!": "i",
                "$": "s",
                "*": "x",
                "@": "_at_",
            }
        )
    )

    # Unicode -> Ascii
    word = unidecode(word)

    # Downcase
    word = word.lower()

    # Das ist der doofe part. Für die ganzen Sonderzeichen gibt es nicht wirklich
    # eine transliterierung in [-0-9_a-z], daher nehme ich einfach underscore,
    # was ggf. zu Kollisionen führen kann. Witzig: Shadow erlaubt '$' im namen,
    # aber nur *ganz* am Ende ...
    # word = regex.sub(r'[^-0-9_a-z]', '_', word[:-1]) + regex.sub(r'[^-0-9_a-z$]', '_', word[-1])
    # since we already replace $ with s, no need to check for $ at the end
    word = regex.sub(r"[^-0-9_a-z]", "_", word)

    # Shadow will das Namen mit Kleinbuchstaben oder Underscore anfangen
    if not regex.match(r"^[a-z_]", word):
        word = "_" + word
    if regex.match(r"_-", word):
        word = "_" + word[2:]        

    # usernames and group names can only be 32 characters long.
    # split names in fragments and loop over them 
    # to progressively remove the characters in excess.
    # .. used to indicate where the shortening took place.
    orig_excess_chars = len(word) - 32
    excess_chars = len(word) - 32
    fragments = word.split("_")

    if excess_chars > 0:

            for n in range(len(fragments)):
                if len(fragments[n]) <= 3: continue
                if excess_chars == 0: break
                excess_chars += 2

                for nchar in range (len(fragments[n]) - 1):
                        fragments[n] = fragments[n][:len(fragments[n]) - 1]
                        excess_chars -= 1
                        if excess_chars == 0: break

                fragments[n] = fragments[n] + ".."

    if orig_excess_chars > 0:

        if excess_chars > 0:
            return None
        else:
            if len(fragments) > 1:
                word = "_".join(fragments)
            else:
                word = fragments[0]
    return word
