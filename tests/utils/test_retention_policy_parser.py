import unittest
from datetime import datetime
from src.utils.retention_policy_parser import (
    get_retention_expiry_date,
    DoNotDeleteRetentionError,
    UnknownRetentionPolicyError,
    InvalidRetentionFormatError
)

class TestRetentionPolicy(unittest.TestCase):

    def setUp(self):
        self.start_date = datetime(2025, 1, 1)

    # Valid retention policies
    def test_valid_days(self):
        result = get_retention_expiry_date("10d", self.start_date)
        self.assertEqual(result, datetime(2025, 1, 11))

    def test_valid_months(self):
        result = get_retention_expiry_date("2m", self.start_date)
        self.assertEqual(result, datetime(2025, 3, 1))

    def test_valid_years(self):
        result = get_retention_expiry_date("1y", self.start_date)
        self.assertEqual(result, datetime(2026, 1, 1))

    # Special cases
    def test_do_not_delete(self):
        with self.assertRaises(DoNotDeleteRetentionError):
            get_retention_expiry_date("DO NOT DELETE", self.start_date)

    def test_unknown_policy(self):
        with self.assertRaises(UnknownRetentionPolicyError):
            get_retention_expiry_date("UNKNOWN", self.start_date)

    # Invalid formats
    def test_invalid_unit(self):
        with self.assertRaises(InvalidRetentionFormatError):
            get_retention_expiry_date("10x", self.start_date)

    def test_missing_unit(self):
        with self.assertRaises(InvalidRetentionFormatError):
            get_retention_expiry_date("10", self.start_date)

    def test_non_numeric_value(self):
        with self.assertRaises(ValueError):
            get_retention_expiry_date("xd", self.start_date)
    
    def test_negative_numeric_value(self):
        with self.assertRaises(ValueError):
            get_retention_expiry_date("-7y", self.start_date)

    # Default start date
    def test_default_start_date(self):
        result = get_retention_expiry_date("1d")
        self.assertTrue(isinstance(result, datetime))

if __name__ == "__main__":
    unittest.main()
