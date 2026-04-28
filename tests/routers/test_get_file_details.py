
import datetime
from unittest.mock import patch
# test_client is fixture defined in tests/fixtures/auth.py
# audit_service_mock is fixture defined in tests/fixtues/audit.py


def test_get_file_details_missing_key(test_client, audit_service_mock):
    response = test_client.get('/get_file_details')
    assert response.status_code == 400
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'File key is missing'


def test_get_file_details_file_not_found(test_client, audit_service_mock):
    file_key = 'missing_file.txt'
    with patch("src.routers.file_details.list_file_versions", return_value=[]):
        response = test_client.get('/get_file_details', params={"file_key": file_key})
    assert response.status_code == 404
    assert response.json()['detail'] == f"No details found for file: {file_key}"
    audit_service_mock.assert_called()


def test_get_file_details_returns_expected_details_with_1_version(test_client, audit_service_mock):
    file_key = 'file_with_one_version.txt'

    s3_version_details = [{"Key": file_key, "VersionId": "abc123", "IsLatest": True,
                           "Size": 120, "LastModified": datetime.datetime(2026, 4, 27, 12, 30, 45),
                           "SecretThing": "Shhh!"}]

    # Subset of returned results - only includes keys: Key, VersionId, IsLatest, Size and LastModified
    # Anything else excluded (also LastModified is now str, not datetime)
    expected_result = {"version_history": [{"Key": file_key, "VersionId": "abc123",
                                            "IsLatest": True, "Size": 120, "LastModified": "2026-04-27T12:30:45"}]}

    with patch("src.routers.file_details.list_file_versions", return_value=s3_version_details):
        response = test_client.get('/get_file_details', params={"file_key": file_key})
    assert response.status_code == 200
    assert response.json() == expected_result
    audit_service_mock.assert_called()


def test_get_file_details_returns_expected_details_with_2_versions(test_client, audit_service_mock):
    file_key = 'file_with_two_versions.txt'

    s3_version_details = [
        {"Key": file_key, "VersionId": "xyz456", "IsLatest": True,
         "Size": 240, "LastModified": datetime.datetime(2026, 4, 27, 12, 30, 45),
         "SecretThing": "Shhh!"},
        {"Key": file_key, "VersionId": "abc123", "IsLatest": False,
         "Size": 120, "LastModified": datetime.datetime(2026, 3, 20, 11, 29, 44),
         "SecretThing": "Hush!"}]

    expected_result = {"version_history": [{"Key": file_key, "VersionId": "xyz456", "IsLatest": True,
                                            "Size": 240, "LastModified": "2026-04-27T12:30:45"},
                                           {"Key": file_key, "VersionId": "abc123", "IsLatest": False,
                                           "Size": 120, "LastModified": "2026-03-20T11:29:44"}]}

    with patch("src.routers.file_details.list_file_versions", return_value=s3_version_details):
        response = test_client.get('/get_file_details', params={"file_key": file_key})
    assert response.status_code == 200
    assert response.json() == expected_result
    audit_service_mock.assert_called()
