
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field, AfterValidator
from src.utils.operation_types import OperationType


def is_known_operation_type(value: str) -> str:
    expected_values = [m.value for m in OperationType]
    if value not in expected_values:
        raise ValueError(f"'{value}' is not a valid OperationType {expected_values}")
    return value


# Could add version_id ? Original put_item method had this as param
class AuditRecord(BaseModel):
    """
    Contents audit-table row
    Note request_id and filename_position are the audit table's hash_key and range_key
    respectively, and need to align with corresponding definitions in the database table's
    Terraform file.
    Other attributes here are independent of the Terraform file.
    """
    request_id: str
    filename_position: int
    service_id: str
    file_id: str
    created_on: str = Field(default_factory=lambda: datetime.now().isoformat())
    operation_type: Annotated[str, AfterValidator(is_known_operation_type)]
    error_details: str = ""
