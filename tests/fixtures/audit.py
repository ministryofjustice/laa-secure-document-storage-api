import pytest
from unittest.mock import patch
from src.services import audit_service


@pytest.fixture
def audit_service_mock():
    """
    Mock audit service for saving audit events.
    :return:
    """
    with patch.object(
        audit_service, "put_item",
        return_value=True,
    ) as mock:
        yield mock
