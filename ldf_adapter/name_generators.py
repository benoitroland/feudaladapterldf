"""
Generate useful user or group names
"""

# vim: foldmethod=indent : tw=100
# pylint: disable=invalid-name, superfluous-parens
# pylint: disable=logging-fstring-interpolation, logging-not-lazy, logging-format-interpolation
# pylint: disable=raise-missing-from, missing-docstring, too-few-public-methods

import logging
from .config import CONFIG

logger = logging.getLogger(__name__)


class FriendlyNameGenerator():
    """
    FNG != FunnyNameGenerator
    Create Names from UserInfo. 
    Don't return the same name twice per run
    """
    dont_use_these_names  = []
    dont_use_these_names.append('[]')
    dont_use_these_names.append('none')
    strategies = [
            "{self.userinfo.preferred_username}",
            "{self.userinfo.given_name}",
            "{self.userinfo.given_name:.3}{self.userinfo.family_name:.3}",
            "{self.userinfo.family_name}",
            "{self.userinfo.given_name:.4}{self.userinfo.family_name:.3}",
            "{self.userinfo.given_name:.5}{self.userinfo.family_name:.3}",
            "{self.userinfo.given_name:.2}{self.userinfo.family_name:.3}",
            "{self.userinfo.given_name:.4}{self.userinfo.family_name:.4}",
            "{self.userinfo.given_name:.5}{self.userinfo.family_name:.4}",
            "{self.userinfo.given_name:.2}{self.userinfo.family_name:.4}",
            "{self.userinfo.given_name:.4}{self.userinfo.family_name:.5}",
            "{self.userinfo.given_name:.5}{self.userinfo.family_name:.5}",
            "{self.userinfo.given_name:.2}{self.userinfo.family_name:.5}",
            "{self.userinfo.given_name:.4}{self.userinfo.family_name:.2}",
            "{self.userinfo.given_name:.5}{self.userinfo.family_name:.2}",
            "{self.userinfo.given_name:.2}{self.userinfo.family_name:.2}",
            "{self.userinfo.email}",
            ]
    next_strategy_idx = -1

    def __init__(self, userinfo):
        """Generate a useful name"""
        self.userinfo = userinfo
    def suggest_name(self, suggestion=None, forbidden_names = None):
        # Copy forbidden names:
        for name in forbidden_names or []:
            if name.lower() not in self.dont_use_these_names:
                self.dont_use_these_names.append(name.lower())

        while True:

            self.next_strategy_idx += 1
            try:
                candidate_name = self.strategies[self.next_strategy_idx].format(**locals()).lower().replace('@','-')
            except KeyError as e:
                pass
                continue
            except AttributeError as e:
                pass
                continue
            except IndexError:
                NL="\n    "
                logger.error(F"Ran out of strategies for generating a friendly username")
                logger.error(F"The list of tried usernames is: \n {NL.join(self.dont_use_these_names)}")
                raise
                return None

            if candidate_name.lower() not in self.dont_use_these_names:
                self.dont_use_these_names.append(candidate_name)
                if CONFIG.getboolean('messages', 'log_username_creation', fallback=False):
                    logger.info(F"Potential username: '{candidate_name}'")
                return candidate_name.lower()
            else:
                self.dont_use_these_names.append(candidate_name.lower())

        return None
    def tried_names(self):
        return self.dont_use_these_names
