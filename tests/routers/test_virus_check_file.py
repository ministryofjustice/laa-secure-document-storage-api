from unittest.mock import patch
from fastapi import HTTPException
from io import BytesIO


@patch("src.routers.virus_check_file.run_virus_check")
def test_virus_check_file_with_virus(scan_mock, test_client):
    scan_mock.side_effect = HTTPException(status_code=400, detail="Virus Found")
    files = {
        "file": ("infected_file.txt", BytesIO(b"goodbye world"), "text/plain")
    }

    response = test_client.put("/virus_check_file", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Virus Found"}
    scan_mock.assert_called_once()


@patch("src.routers.virus_check_file.run_virus_check")
def test_virus_check_file_with_unexpected_virus_scan_result(scan_mock, test_client):
    scan_mock.side_effect = HTTPException(status_code=500, detail="Virus scan gave non-standard result")
    files = {
        "file": ("unlucky_file.txt", BytesIO(b"What in the world?"), "text/plain")
    }

    response = test_client.put("/virus_check_file", files=files)

    assert response.status_code == 500
    assert response.json() == {"detail": "Virus scan gave non-standard result"}
    scan_mock.assert_called_once()


def test_virus_check_file_with_no_file(test_client):
    response = test_client.put("/virus_check_file",)

    assert response.status_code == 400
    assert response.json() == {'detail': 'File is required'}


@patch("src.routers.virus_check_file.run_virus_check")
def test_virus_check_file_with_clean_file(scan_mock, test_client):
    scan_mock.return_value = (200, "")
    files = {"file": ("hello world", BytesIO(), "text/plain")}

    response = test_client.put("/virus_check_file", files=files)

    assert response.status_code == 200
    assert response.json() == {'success': 'No virus found'}
