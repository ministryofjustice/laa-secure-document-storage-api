import os
import re
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from src.models.audit_record import AuditRecord
from src.services.audit_service import put_item

"""
Mocking for put_item function

DynamoDB access depends on 3 connected tiers:
1. Our own AuditService class gets a boto3 DynamoDB client via its
   get_dynamodb_client method.
2. The DynamoDB client gives us a Table object.
3. The Table object is used to update the DynamoDB table.

Mocking approach:
(a) Create a mock Table object that captures its put_item method calls
(b) Create a mock DynamoDB client that returns the mock Table object from (a)
(c) Patch AuditService.get_dynamodb_client method to return the mock DynamoDB
    client from (b), which will cause our mock Table object from (a) to be updated.

In addition the mock Table object also records the table names passed to it. This is
because our put_item function should get the table name from environment variable
AUDIT_TABLE. Recording the table names enables us to check if this is getting
the expected value.

Complication
Original plan was to create mock Table and mock DynamoDB client within each test.
However, this causes problems because AuditService is a singleton class, so mock
values established in one test can persist to the next. So instead the tests deliberately
share the same mock Table object and mock DynamoDB client but use a method to reset
the captured data within the mock Table object.

This also means that the patching of
src.services.audit_service.AuditService.get_dynamodb_client
likely only needs to exist in the first test that's executed but does no harm to
include it in others (and also makes it easier to re-order the tests).
"""


class MockTable:
    def __init__(self):
        self.put_item_calls = []
        self.names_received = []

    # "Item" init-cap to match boto3 original
    def put_item(self, Item):
        self.put_item_calls.append(Item)

    def add_name(self, name):
        "Not a method found in real Table object"
        self.names_received.append(name)

    def reset(self):
        "Not a method found in real Table object"
        self.put_item_calls = []
        self.names_received = []


class MockDynamoDBClient:
    def __init__(self, mock_table=None):
        self.mock_table = mock_table

    # "Table" init-cap to match boto3 original
    def Table(self, table_name):
        self.mock_table.add_name(table_name)
        return self.mock_table


mock_table = MockTable()
mock_client = MockDynamoDBClient(mock_table=mock_table)


@pytest.mark.parametrize("operation_type", ["CREATE", "READ", "UPDATE", "DELETE"])
def test_audit_put_item_with_valid_item_with_empty_created_on(operation_type):
    """
    This test has a manually specified created_on value which is unrealistic
    as this would normally be excluded to receieve default date/time value.
    The direct setting to "" here is just for convenience of the assert
    at the end not needing anything time/date specific. Separate test below
    covers more realistic created_on value.
    """
    audit_record = AuditRecord(
        request_id="abc123",
        filename_position=0,
        service_id="pytest-test",
        file_id="test.txt",
        created_on="",
        operation_type=operation_type,
        error_details="",
    )

    mock_table.reset()
    assert mock_table.put_item_calls == mock_table.names_received == []

    with (
        patch(
            "src.services.audit_service.AuditService.get_dynamodb_client",
            return_value=mock_client,
        ),
        patch.dict(os.environ, {"AUDIT_TABLE": "TEST_AUDIT_1"}),
    ):
        put_item(audit_record)

    assert mock_table.names_received == ["TEST_AUDIT_1"]
    assert mock_table.put_item_calls == [
        {
            "request_id": "abc123",
            "filename_position": 0,
            "service_id": "pytest-test",
            "file_id": "test.txt",
            "created_on": "",
            "operation_type": operation_type,
            "error_details": "",
        }
    ]


@pytest.mark.parametrize("file_info", [{"request_id": "multi1",
                                        "filename_position": 0,
                                        "file_id": "file_a.txt"},
                                       {"request_id": "multi2",
                                        "filename_position": 1,
                                        "file_id": "file_b.txt"},
                                       {"request_id": "multi3",
                                        "filename_position": 2,
                                        "file_id": "file_b.txt"},  # repeat filename
                                       {"request_id": "multi4",
                                        "filename_position": 3,
                                        "file_id": "file_c.txt"}
                                       ])
def test_audit_put_items_with_different_filename_positions(file_info):
    "Also has empty created_on for convenience"
    audit_record = AuditRecord(
        request_id=file_info["request_id"],
        filename_position=file_info["filename_position"],
        service_id="pytest-position-test",
        file_id=file_info["file_id"],
        created_on="",
        operation_type="DELETE",
        error_details="",
    )

    mock_table.reset()
    assert mock_table.put_item_calls == mock_table.names_received == []

    with (
        patch(
            "src.services.audit_service.AuditService.get_dynamodb_client",
            return_value=mock_client,
        ),
        patch.dict(os.environ, {"AUDIT_TABLE": "TEST_AUDIT_2"}),
    ):
        put_item(audit_record)

    assert mock_table.names_received == ["TEST_AUDIT_2"]
    assert mock_table.put_item_calls == [
        {
            "request_id": file_info["request_id"],
            "filename_position": file_info["filename_position"],
            "service_id": "pytest-position-test",
            "file_id": file_info["file_id"],
            "created_on": "",
            "operation_type": "DELETE",
            "error_details": "",
        }
    ]


def test_audit_put_item_with_valid_item_and_generated_created_on():
    """
    No created_on value supplied, which is normal and results in
    automatically set date/time value.
    """
    audit_record = AuditRecord(
        request_id="xyz456",
        filename_position=0,
        service_id="pytest-test",
        file_id="datetest.txt",
        operation_type="CREATE",
        error_details="",
    )
    expected_created_on = audit_record.created_on
    mock_table.reset()
    assert mock_table.put_item_calls == mock_table.names_received == []

    with (
        patch(
            "src.services.audit_service.AuditService.get_dynamodb_client",
            return_value=mock_client,
        ),
        patch.dict(os.environ, {"AUDIT_TABLE": "TEST_AUDIT_3"}),
    ):
        put_item(audit_record)

    assert mock_table.names_received == ["TEST_AUDIT_3"]
    assert len(mock_table.put_item_calls) == 1
    details = mock_table.put_item_calls[0]
    assert details["request_id"] == "xyz456"
    assert details["file_id"] == "datetest.txt"
    assert details["created_on"] == expected_created_on
    # Regex pattern for ISO8601 date string - copied from online
    ISO8601_date_pattern = ("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                            r"(\.[0-9]+)?([Zz]|([\+-])([01]\d|2[0-3]):?([0-5]\d)?)?")
    assert bool(re.match(ISO8601_date_pattern, details["created_on"])) is True


def test_get_expected_error_when_no_audit_table_environment_variable(monkeypatch):
    """
    Test for circumstance in which AUDIT_TABLE environment variable does not exist.
    """
    audit_record = AuditRecord(
        request_id="no_env_var_abc",
        filename_position=0,
        service_id="pytest-env-test",
        file_id="doomed.txt",
        created_on="",
        operation_type="CREATE",
        error_details=""
        )
    mock_table.reset()
    # Note patch.dict(os.environ, {}) does not remove environment variables
    # but monkeypatch.delenv does work.
    monkeypatch.delenv("AUDIT_TABLE")
    with (patch("src.services.audit_service.AuditService.get_dynamodb_client",
                return_value=mock_client),
          pytest.raises(ValueError) as exc_info):
        put_item(audit_record)
    assert str(exc_info.value) == "Failed to get value from AUDIT_TABLE environment variable"


def test_get_expected_error_with_invalid_operation_type():
    """
    This is a bit of an aside as the validation takes place in the AuditRecord model
    which is created before the audit service is used.
    """
    with pytest.raises(ValidationError) as exc_info:
        _ = AuditRecord(
            request_id="abc123",
            filename_position=0,
            service_id="pytest-test",
            file_id="test.txt",
            created_on="",
            operation_type="SERENADE",
            error_details="",
        )
    assert "Value error, 'SERENADE' is not a valid OperationType" in str(exc_info.value)
