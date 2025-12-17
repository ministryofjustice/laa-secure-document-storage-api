
from unittest.mock import patch
from fastapi import HTTPException
from io import BytesIO


@patch("src.routers.scan_for_suspicious_content.suspicious_content_validator.ScanForSuspiciousContent.validate")
def test_scan_for_suspicious_content_with_malicious_content(validate_mock, test_client):
    validate_mock.side_effect = HTTPException(status_code=400, detail="Malicious content detected")
    files = {
        "file": ("malicious.csv", BytesIO(b"name,age\n<script>alert(Malicious Business)</script>,30"), "text/csv")
    }

    response = test_client.put("/scan_for_suspicious_content", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Malicious content detected"}
    validate_mock.assert_called_once()


def test_scan_for_suspicious_content_with_no_file(test_client):
    response = test_client.put("/scan_for_suspicious_content")
    body = response.json()

    assert response.status_code == 422
    assert "detail" in body
    assert isinstance(body["detail"], list)
    for e in body["detail"]:
        assert e.get("msg").lower() == "field required"
        assert e.get("type").lower() == "missing"


@patch("src.routers.scan_for_suspicious_content.suspicious_content_validator.ScanForSuspiciousContent.validate")
def test_scan_for_suspicious_content_with_clean_file(validate_mock, test_client):
    validate_mock.return_value = (200, "")
    files = {
        "file": ("clean.csv", BytesIO(b"name,age\nAlice,30\nBob,25"), "text/csv")
    }

    response = test_client.put("/scan_for_suspicious_content", files=files)

    assert response.status_code == 200
    assert response.json() == {"success": "No malicious content detected"}
    validate_mock.assert_called_once()
