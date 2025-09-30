from unittest.mock import patch
from fastapi import HTTPException


def test_delete_files_missing_file_key(test_client):
    response = test_client.delete('/delete_files')

    assert response.status_code == 400
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'File key is missing'


def test_delete_files_permission_denied(test_client):
    file_key = 'test_file.md'

    with patch("src.services.authz_service.enforce_or_error") as authz_mock:
        authz_mock.side_effect = HTTPException(status_code=403, detail="Forbidden")

        response = test_client.delete(f'/delete_files?file_keys={file_key}')

        assert response.status_code == 403


def test_delete_files_missing_file(test_client):
    file_key = 'test_file.md'

    with patch("src.routers.delete_files.s3_service.list_file_versions") as list_versions_mock:

        list_versions_mock.return_value = []

        response = test_client.delete(f'/delete_files?file_keys={file_key}')

        assert response.status_code == 202
        assert response.json()[file_key] == 404


def test_delete_files_unexpected_error(test_client):
    file_key = 'test_file.md'

    with patch("src.routers.delete_files.s3_service.list_file_versions") as list_versions_mock:

        list_versions_mock.side_effect = RuntimeError("Unexpected failure")

        response = test_client.delete(f'/delete_files?file_keys={file_key}')

        assert response.status_code == 202
        assert response.json()[file_key] == 500


def test_delete_files_single_key(test_client):
    file_key = 'test_file.md'

    with patch("src.routers.delete_files.s3_service.list_file_versions") as list_versions_mock, \
         patch("src.routers.delete_files.s3_service.delete_file_version") as delete_version_mock:

        list_versions_mock.return_value = [{"VersionId": "v1"}]
        delete_version_mock.return_value = True

        response = test_client.delete(f'/delete_files?file_keys={file_key}')

        assert response.status_code == 202
        assert response.json()[file_key] == 204


def test_delete_files_multiple_keys(test_client):
    file_a = 'test_file_a.md'
    file_b = 'test_file_b.md'

    with patch("src.routers.delete_files.s3_service.list_file_versions") as list_versions_mock, \
         patch("src.routers.delete_files.s3_service.delete_file_version") as delete_version_mock:

        list_versions_mock.return_value = [{"VersionId": "v1"}]
        delete_version_mock.return_value = True

        response = test_client.delete(f'/delete_files?file_keys={file_a}&file_keys={file_b}')

        assert response.status_code == 202
        for file_key in [file_a, file_b]:
            assert response.json()[file_key] == 204


def test_delete_files_multiple_status(test_client):
    file_a = 'file_a.md'
    file_b = 'file_b.md'
    file_c = 'file_c.md'

    with patch("src.routers.delete_files.s3_service.list_file_versions") as list_versions_mock, \
         patch("src.routers.delete_files.s3_service.delete_file_version") as delete_version_mock:

        list_versions_mock.side_effect = [
            [{"VersionId": "v1"}],  # file_a: success
            [],                     # file_b: not found
            RuntimeError()          # file_c: error
        ]
        delete_version_mock.return_value = True

        response = test_client.delete(f'/delete_files?file_keys={file_a}&file_keys={file_b}&file_keys={file_c}')
        outcomes = response.json()

        assert response.status_code == 202
        assert outcomes[file_a] == 204
        assert outcomes[file_b] == 404
        assert outcomes[file_c] == 500


def test_delete_files_partial_version_failure(test_client):
    file_a = 'file_a.md'

    with patch("src.routers.delete_files.s3_service.list_file_versions") as list_versions_mock, \
         patch("src.routers.delete_files.s3_service.delete_file_version") as delete_version_mock:

        list_versions_mock.return_value = [{"VersionId": "v1"}, {"VersionId": "v2"}]
        delete_version_mock.side_effect = [True, RuntimeError("Failed to delete v2")]

        response = test_client.delete(f'/delete_files?file_keys={file_a}')
        outcomes = response.json()

        assert response.status_code == 202
        assert outcomes[file_a] == 500


def test_delete_files_missing_version_id(test_client):
    file_key = 'file_with_bad_version.md'

    with patch("src.routers.delete_files.s3_service.list_file_versions") as list_versions_mock, \
         patch("src.routers.delete_files.s3_service.delete_file_version") as delete_version_mock:

        # Simulate a version dictionary missing the "VersionId" key
        list_versions_mock.return_value = [{"NoVersionId": "oops"}]
        delete_version_mock.return_value = True  # Shouldn't be called
        response = test_client.delete(f'/delete_files?file_keys={file_key}')
        outcomes = response.json()

        assert response.status_code == 202
        assert outcomes[file_key] == 500
