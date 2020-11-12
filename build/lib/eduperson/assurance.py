"""
Implements the REFEDS Assurance Framework.

As specified in: https://wiki.refeds.org/display/ASS/REFEDS+Assurance+Framework+ver+1.0
"""

import logging
from datetime import timedelta

import regex

PREFIX = 'https://refeds.org/assurance'

class Profile:
    PREFIX = PREFIX + '/profile'

    re = regex.compile(PREFIX + r'/(cappuccino|espresso)')

    def __init__(self, uri):
        match = self.re.fullmatch(uri)

        if not match:
            raise ValueError("Invalid assurance profile '{}'".format(uri))

        self.profile_str = match.group(1)

    @classmethod
    def from_assurance(self, ass):
        profile = None

        if {1,2,3,4} <= ass.identifier_uniqueness.uid_uniqueness_levels and ass.identity_assurance.is_medium and ass.attribute_assurance.user_departure_latency <= timedelta(days=31):
            profile = self.CAPPUCCINO()

            if ass.identity_assurance.is_high:
                profile = self.ESPRESSO()

        return profile

    def is_espresso(self):
        return self.profile_str == 'esspresso'

    def is_cappuccino(self):
        return self.profile_str == 'cappuccino'

    def __repr__(self):
        return self.PREFIX + '/' + self.profile_str

    def __str__(self):
        return '<Profile {}>'.format(self.profile_str)

    @classmethod
    def CAPPUCCINO(self):
        return self(self.PREFIX + '/cappuccino')

    @classmethod
    def ESPRESSO(self):
        return self(self.PREFIX + '/espresso')


class Assurance:
    def __init__(self, uris):
        self.identifier_uniqueness = IdentifierUniqueness(uri for uri in uris if IdentifierUniqueness.re.match(uri))
        self.identity_assurance = IdentityAssurance(uri for uri in uris if IdentityAssurance.re.match(uri))
        self.attribute_assurance = AttributeAssurance(uri for uri in uris if AttributeAssurance.re.match(uri))

    @property
    def profile(self):
        return Profile.from_assurance(self)

    def __str__(self):
        return '<Assurance ID={} IAP={} ATP={}>'.format(
            self.identifier_uniqueness,
            self.identity_assurance,
            self.attribute_assurance
        )


class IdentifierUniqueness:
    PREFIX = PREFIX + '/ID'

    re = regex.compile(PREFIX + r'/(unique|eppn-unique-no-reassign|eppn-unique-reassign-1y)')

    def __init__(self, uris):
        matches = [(uri,self.re.fullmatch(uri)) for uri in uris]
        values = set((match.group(1)
                      if match else raise_(ValueError("Invalid identifier uniqueness '{}'".format(uri))))
                     for (uri,match) in matches)

        if 'eppn-unique-reassign-1y' in values and 'eppn-unique-no-reassign' in values:
            raise ValueError("Conflicting identifier uniqueness values '{}' and '{}' encountered".format(
                'eppn-unique-reassign-1y', 'eppn-unique-no-reassign'))

        self.uid_uniqueness_levels = set()
        self.eppn_uniqueness_levels = set()
        self.eppn_uniqueness_reassign_period = None


        if 'unique' in values:
            self.uid_uniqueness_levels = {1,2,3,4}

        if 'eppn-unique-no-reassign' in values:
            self.eppn_uniqueness_levels = {1,2,3}
        elif 'eppn-unique-reassign-1y' in values:
            self.eppn_uniqueness_levels = {1,2}
            self.eppn_uniqueness_reassign_period = timedelta(days=365)

    @property
    def uid_is_unique(self):
        return {1,2,3,4} <= self.uid_uniqueness_levels

    @property
    def eppn_is_reassignable(self):
        return 3 not in self.eppn_uniqueness_levels

class IdentityAssurance:
    PREFIX =  PREFIX + '/IAP'

    re = regex.compile(PREFIX + r'/(low|medium|high|local-enterprise)')

    def __init__(self, uris):
        matches = [(uri,self.re.fullmatch(uri)) for uri in uris]
        values = set((match.group(1)
                      if match else raise_(ValueError("Invalid identity assurance '{}'".format(uri))))
                     for (uri,match) in matches)

        if 'low' in values:
            self.level = 1

        if 'medium' in values:
            if not 'low' in values:
                raise ValueError("Identity assurance level 'medium' found, but not 'low'")

            self.level = 2

        if 'high' in values:
            if not 'medium' in values:
                raise ValueError("Identity assurance level 'high' found, but not 'medium'")

            self.level = 3

        if 'local-enterprise' in values:
            self.local_enterprise = True
        else:
            self.local_enterprise = False

    @property
    def is_low(self):
        return self.level >= 1

    @property
    def is_medium(self):
        return self.level >= 2

    @property
    def is_high(self):
        return self.level >= 3

    @property
    def level_str(self):
        return ['low', 'medium', 'high'][self.level]

class AttributeAssurance:
    PREFIX = PREFIX + '/ATP'

    re = regex.compile(PREFIX + r'/ePA-(1m|1d)')

    def __init__(self, uris):
        matches = [(uri,self.re.fullmatch(uri)) for uri in uris]
        values = set((match.group(1)
                      if match else raise_(ValueError("Invalid attribute assurance '{}'".format(uri))))
                     for (uri,match) in matches)

        self.user_departure_latencey = None

        if '1m' in values:
            self.user_departure_latency = timedelta(days=31)

        if '1d' in values:
            if not '1m' in values:
                raise ValueError("Attribute assurance 'ePA-1m' found, but not 'ePA-1d'")

            self.user_departure_latency = timedelta(days=1)


def raise_(error):
    raise error
