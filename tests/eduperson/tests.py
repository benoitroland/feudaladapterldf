from unittest import TestCase

import pytest

from datetime import timedelta

# from eduperson.assurance import *


@pytest.mark.skip(reason='The tested code seems to be missing ?!')
class TestIdentifierUniqueness(TestCase):
    def test_empty(self):
        ass = []
        id = IdentifierUniqueness(ass)
        self.assertFalse(id.uid_uniqueness_levels)
        self.assertFalse(id.eppn_uniqueness_levels)
        self.assertFalse(id.eppn_uniqueness_reassign_period)

    def test_unique(self):
        ass = [
            "https://refeds.org/assurance/ID/unique",
        ]
        id = IdentifierUniqueness(ass)
        self.assertEqual(id.uid_uniqueness_levels, {1,2,3,4})
        self.assertFalse(id.eppn_uniqueness_levels)
        self.assertFalse(id.eppn_uniqueness_reassign_period)

    def test_no_reassign(self):
        ass = [
            "https://refeds.org/assurance/ID/eppn-unique-no-reassign",
        ]
        id = IdentifierUniqueness(ass)
        self.assertFalse(id.uid_uniqueness_levels)
        self.assertEqual(id.eppn_uniqueness_levels, {1,2,3})
        self.assertFalse(id.eppn_uniqueness_reassign_period)

    def test_1y(self):
        ass = [
            "https://refeds.org/assurance/ID/eppn-unique-reassign-1y",
        ]
        id = IdentifierUniqueness(ass)
        self.assertFalse(id.uid_uniqueness_levels)
        self.assertEqual(id.eppn_uniqueness_levels, {1,2})
        self.assertEqual(id.eppn_uniqueness_reassign_period, timedelta(days=365))

    def test_conflict(self):
        ass = [
            "https://refeds.org/assurance/ID/eppn-unique-no-reassign",
            "https://refeds.org/assurance/ID/eppn-unique-reassign-1y",
        ]
        with self.assertRaises(ValueError):
            IdentifierUniqueness(ass)


    def test_combine(self):
        ass = [
            "https://refeds.org/assurance/ID/unique",
            "https://refeds.org/assurance/ID/eppn-unique-no-reassign",
        ]
        id = IdentifierUniqueness(ass)
        self.assertEqual(id.uid_uniqueness_levels, {1,2,3,4})
        self.assertEqual(id.eppn_uniqueness_levels, {1,2,3})
        self.assertFalse(id.eppn_uniqueness_reassign_period)
