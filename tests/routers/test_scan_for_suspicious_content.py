
from unittest.mock import patch
from io import BytesIO
# test_client is fixture from tests/fixtures/auth.py


@patch("src.routers.scan_for_suspicious_content.suspicious_content_validator.ScanForSuspiciousContent.validate")
def test_scan_for_suspicious_content_with_malicious_csv_content(validate_mock, test_client):
    validate_mock.return_value = (400, "Malicious content detected")
    files = {
        "file": ("malicious.csv", BytesIO(b"name,age\n<script>alert(Malicious Business)</script>,30"), "text/csv")
    }

    response = test_client.put("/scan_for_suspicious_content", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Malicious content detected"}
    validate_mock.assert_called_once()


@patch("src.routers.scan_for_suspicious_content.suspicious_content_validator.ScanForSuspiciousContent.validate")
def test_scan_for_suspicious_content_with_malicious_xml_content(validate_mock, test_client):
    validate_mock.return_value = (400, "Suspicious content detected")
    # Note file extension not XML because XML detection relies on mimetype
    files = {
        "file": ("malicious.zzz", BytesIO(b"<xml> DROP TABLE students;--"), "text/xml")
    }

    response = test_client.put("/scan_for_suspicious_content", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "(XML Scan) Suspicious content detected"}
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
def test_scan_for_suspicious_content_with_clean_csv_file(validate_mock, test_client):
    validate_mock.return_value = (200, "")
    files = {
        "file": ("clean.csv", BytesIO(b"name,age\nAlice,30\nBob,25"), "text/csv")
    }

    response = test_client.put("/scan_for_suspicious_content", files=files)

    assert response.status_code == 200
    assert response.json() == {"success": "No malicious content detected"}
    validate_mock.assert_called_once()


@patch("src.routers.scan_for_suspicious_content.suspicious_content_validator.ScanForSuspiciousContent.validate")
def test_scan_for_suspicious_content_with_clean_xml_file(validate_mock, test_client):
    validate_mock.return_value = (200, "")
    files = {
        "file": ("clean.zzz", BytesIO(b"<xml> mostly harmless"), "text/xml")
    }

    response = test_client.put("/scan_for_suspicious_content", files=files)

    assert response.status_code == 200
    assert response.json() == {"success": "(XML Scan) No malicious content detected"}
    validate_mock.assert_called_once()
