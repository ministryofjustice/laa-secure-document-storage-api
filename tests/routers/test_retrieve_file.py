from unittest.mock import patch
from fastapi.testclient import TestClient
from src.main import app
from src.utils.operation_types import OperationType

client = TestClient(app)


def test_retrieve_file_success():
    # Arrange
    file_key = "test_file_key"
    expected_file_url = "https://example.com/test_file"

    # Mock the external service response
    with patch("src.routers.retrieve_file.retrieveFileUrl") as mock_retrieve_file_url, \
            patch("src.routers.retrieve_file.put_item") as mock_put_item:
        mock_retrieve_file_url.return_value = expected_file_url
        mock_put_item.return_value = None

        # Act
        client = TestClient(app)
        response = client.get(f"/retrieve_file/{file_key}")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"fileURL": expected_file_url}
    mock_retrieve_file_url.assert_called_once_with(file_key)
    mock_put_item.assert_called_once_with("equiniti-service-id", file_key, OperationType.READ)


def test_retrieve_file_missing_key():
    client = TestClient(app)
    response = client.get("/retrieve_file/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_retrieve_file_exception():
    # Arrange
    file_key = "invalid_file_key"

    # Mock the external service response
    with patch("src.routers.retrieve_file.retrieveFileUrl") as mock_retrieve_file_url, \
            patch("src.routers.retrieve_file.put_item") as mock_put_item:
        mock_retrieve_file_url.side_effect = Exception("Something went wrong")
        mock_put_item.return_value = None

        # Act
        client = TestClient(app)
        response = client.get(f"/retrieve_file/{file_key}")

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Something went wrong"}
