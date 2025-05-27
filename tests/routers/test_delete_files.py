from unittest.mock import patch
from fastapi import HTTPException


def test_delete_files_missing_key(test_client):
    response = test_client.delete('/delete_files')

    assert response.status_code == 400
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'File key is missing'


@patch("src.services.authz_service.enforce_or_error")
def test_delete_files_permission_denied(authz_mock, test_client):
    authz_mock.side_effect = HTTPException(status_code=403, detail="Forbidden")
    file_key = 'test_file.md'

    response = test_client.delete(f'/delete_files?file_keys={file_key}')

    assert response.status_code == 403


@patch("src.routers.delete_files.s3_service.delete_file")
def test_delete_files_missing_file(s3_delete_mock, test_client, audit_service_mock):
    s3_delete_mock.side_effect = FileNotFoundError()
    file_key = 'test_file.md'

    response = test_client.delete(f'/delete_files?file_keys={file_key}')

    assert response.status_code == 202
    assert file_key in response.json()
    assert response.json()[file_key] == 404


@patch("src.routers.delete_files.s3_service.delete_file")
def test_delete_files_unexpected_error(s3_delete_mock, test_client, audit_service_mock):
    s3_delete_mock.side_effect = RuntimeError()
    file_key = 'test_file.md'

    response = test_client.delete(f'/delete_files?file_keys={file_key}')

    assert response.status_code == 202
    assert file_key in response.json()
    assert response.json()[file_key] == 500


@patch("src.routers.delete_files.s3_service.delete_file")
def test_delete_files_single_key(s3_delete_mock, test_client, audit_service_mock):
    s3_delete_mock.return_value = True
    file_key = 'test_file.md'

    response = test_client.delete(f'/delete_files?file_keys={file_key}')

    assert response.status_code == 202
    assert file_key in response.json()
    assert response.json()[file_key] == 204


@patch("src.routers.delete_files.s3_service.delete_file")
def test_delete_files_multiple_keys(s3_delete_mock, test_client, audit_service_mock):
    s3_delete_mock.return_value = True
    file_a = 'test_file_a.md'
    file_b = 'test_file_b.md'

    response = test_client.delete(f'/delete_files?file_keys={file_a}&file_keys={file_b}')

    assert response.status_code == 202
    for file_key in [file_a, file_b]:
        assert file_key in response.json()
        assert response.json()[file_key] == 204


@patch("src.routers.delete_files.s3_service.delete_file")
def test_delete_files_multiple_status(s3_delete_mock, test_client, audit_service_mock):
    s3_delete_mock.side_effect = [
        True,
        FileNotFoundError(),
        RuntimeError()
    ]
    file_a = 'file_a.md'
    file_b = 'file_b.md'
    file_c = 'file_c.md'

    response = test_client.delete(f'/delete_files?file_keys={file_a}&file_keys={file_b}&file_keys={file_c}')
    outcomes = response.json()

    assert response.status_code == 202
    assert outcomes[file_a] == 204
    assert outcomes[file_b] == 404
    assert outcomes[file_c] == 500
