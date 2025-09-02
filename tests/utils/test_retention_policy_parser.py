import pytest
from datetime import datetime
from src.utils.retention_policy_parser import (
    get_retention_expiry_date,
    DoNotDeleteRetentionError,
    UnknownRetentionPolicyError,
    InvalidRetentionFormatError
)

@pytest.fixture
def start_date():
    return datetime(2025, 1, 1)

# Valid retention policies
def test_valid_days(start_date):
    result = get_retention_expiry_date("10d", start_date)
    assert result == datetime(2025, 1, 11)

def test_valid_months(start_date):
    result = get_retention_expiry_date("2m", start_date)
    assert result == datetime(2025, 3, 1)

def test_valid_years(start_date):
    result = get_retention_expiry_date("1y", start_date)
    assert result == datetime(2026, 1, 1)

# Special cases
def test_do_not_delete(start_date):
    with pytest.raises(DoNotDeleteRetentionError):
        get_retention_expiry_date("DO NOT DELETE", start_date)

def test_unknown_policy(start_date):
    with pytest.raises(UnknownRetentionPolicyError):
        get_retention_expiry_date("UNKNOWN", start_date)

# Invalid formats
def test_invalid_unit(start_date):
    with pytest.raises(InvalidRetentionFormatError):
        get_retention_expiry_date("10x", start_date)

def test_missing_unit(start_date):
    with pytest.raises(InvalidRetentionFormatError):
        get_retention_expiry_date("10", start_date)

def test_non_numeric_value(start_date):
    with pytest.raises(ValueError):
        get_retention_expiry_date("xd", start_date)

def test_negative_numeric_value(start_date):
    with pytest.raises(ValueError):
        get_retention_expiry_date("-7y", start_date)

def test_non_int_numeric_value(start_date):
    with pytest.raises(ValueError):
        get_retention_expiry_date('5.6y', start_date)

def test_mixed_units(start_date):
    with pytest.raises(ValueError):
        get_retention_expiry_date('5y6m', start_date)

# Default start date
def test_default_start_date():
    result = get_retention_expiry_date("1d")
    assert isinstance(result, datetime)
