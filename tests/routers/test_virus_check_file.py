from unittest.mock import patch
from fastapi import HTTPException
from io import BytesIO

from src.models.validation_response import ValidationResponse


@patch("src.routers.virus_check_file.clam_av_validator.scan_request")
def test_virus_check_file_with_virus(scan_mock, test_client):
    scan_mock.side_effect = HTTPException(status_code=400, detail="Virus detected")
    files = {
        "file": ("infected_file.txt", BytesIO(b"goodbye world"), "text/plain")
    }

    response = test_client.put("/virus_check_file", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Virus detected"}
    scan_mock.assert_called_once()


def test_virus_check_file_with_no_file(test_client):
    response = test_client.put("/virus_check_file",)

    assert response.status_code == 400
    assert response.json() == {'detail': ['File is required']}


@patch("src.routers.virus_check_file.clam_av_validator.scan_request")
def test_virus_check_file_with_clean_file(scan_mock, test_client):
    scan_mock.return_value = ValidationResponse(200, "")
    files = {"file": ("hello world", BytesIO(), "text/plain")}

    response = test_client.put("/virus_check_file", files=files)

    assert response.status_code == 200
    assert response.json() == {'success': 'No virus found'}
