from unittest.mock import patch
import pytest
import structlog
from fastapi.testclient import TestClient

from jwt import (
    ExpiredSignatureError,
    InvalidTokenError,
    InvalidAudienceError,
    InvalidIssuerError,
)

from src.main import app

test_client = TestClient(app)
logger = structlog

MOCK_OIDC_CONFIG = {'jwks_uri': 'https://fake-jwks'}


@pytest.mark.normal_auth
def test_incorrect_auth_scheme(audit_service_mock):
    response = test_client.get(
        '/retrieve_file?file_key=README.md',
        headers={'Authorization': 'Notbearer token'},
    )
    assert response.status_code == 401


@pytest.mark.normal_auth
@pytest.mark.parametrize("bad_headers", [
    {'Authorization': 'Bearer None'},
    {'Authorization': 'Bearer '}
])
def test_empty_token(audit_service_mock, bad_headers):
    response = test_client.get('/retrieve_file?file_key=README.md', headers=bad_headers)
    assert response.status_code == 401
    assert response.text == '{"detail":"Invalid or expired token"}'


#  --- ALL BELOW USE get_signing_key MOCK ---


@pytest.mark.normal_auth
@patch('src.middleware.auth.get_signing_key')
@patch('src.middleware.auth.jwt_decode')
@patch('src.middleware.auth.fetch_oidc_config')
def test_missing_azp_claim(oidc_mock, decode_mock, get_key_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    get_key_mock.return_value = "fake-public-key"

    decode_mock.return_value = {
        'sub': 'test_user',
        'iss': 'https://login.microsoftonline.com/123456',
    }

    response = test_client.get(
        '/retrieve_file?file_key=README.md',
        headers={'Authorization': 'Bearer token'}
    )

    assert response.status_code == 403
    decode_mock.assert_called_once()


@pytest.mark.normal_auth
@patch('src.middleware.auth.get_signing_key')
@patch('src.middleware.auth.jwt_decode')
@patch('src.middleware.auth.fetch_oidc_config')
def test_incorrect_roles(oidc_mock, decode_mock, get_key_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    get_key_mock.return_value = "fake-public-key"

    decode_mock.return_value = {
        'sub': 'test_user',
        'iss': 'https://login.microsoftonline.com/123456',
        'azp': 'client_id',
        'roles': ['MISS'],
    }

    response = test_client.get(
        '/retrieve_file?file_key=README.md',
        headers={'Authorization': 'Bearer token'}
    )

    assert response.status_code == 403
    decode_mock.assert_called_once()


@pytest.mark.normal_auth
@patch('src.middleware.auth.get_signing_key')
@patch('src.middleware.auth.jwt_decode')
@patch('src.middleware.auth.fetch_oidc_config')
def test_expired_signature(oidc_mock, decode_mock, get_key_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    get_key_mock.return_value = "fake-public-key"

    decode_mock.side_effect = ExpiredSignatureError()

    response = test_client.get(
        '/retrieve_file?file_key=README.md',
        headers={'Authorization': 'Bearer token'}
    )

    assert response.status_code == 401
    decode_mock.assert_called_once()


@pytest.mark.normal_auth
@patch('src.middleware.auth.get_signing_key')
@patch('src.middleware.auth.jwt_decode')
@patch('src.middleware.auth.fetch_oidc_config')
def test_invalid_token_generic(oidc_mock, decode_mock, get_key_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    get_key_mock.return_value = "fake-public-key"

    decode_mock.side_effect = InvalidTokenError()

    response = test_client.get(
        '/retrieve_file?file_key=README.md',
        headers={'Authorization': 'Bearer token'}
    )

    assert response.status_code == 401
    decode_mock.assert_called_once()


@pytest.mark.normal_auth
@patch('src.middleware.auth.get_signing_key')
@patch('src.middleware.auth.jwt_decode')
@patch('src.middleware.auth.fetch_oidc_config')
def test_invalid_audience_maps_to_403(oidc_mock, decode_mock, get_key_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    get_key_mock.return_value = "fake-public-key"

    decode_mock.side_effect = InvalidAudienceError()

    response = test_client.get(
        '/retrieve_file?file_key=README.md',
        headers={'Authorization': 'Bearer token'}
    )

    assert response.status_code == 403
    decode_mock.assert_called_once()


@pytest.mark.normal_auth
@patch('src.middleware.auth.get_signing_key')
@patch('src.middleware.auth.jwt_decode')
@patch('src.middleware.auth.fetch_oidc_config')
def test_invalid_issuer_maps_to_403(oidc_mock, decode_mock, get_key_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    get_key_mock.return_value = "fake-public-key"

    decode_mock.side_effect = InvalidIssuerError()

    response = test_client.get(
        '/retrieve_file?file_key=README.md',
        headers={'Authorization': 'Bearer token'}
    )

    assert response.status_code == 403
    decode_mock.assert_called_once()


@pytest.mark.normal_auth
@patch('src.middleware.auth.get_signing_key')
@patch('src.middleware.auth.fetch_oidc_config')
def test_jwks_uri_invalid_or_key_resolution_fails(oidc_mock, get_key_mock, audit_service_mock):
    oidc_mock.return_value = {'jwks_uri': 'https://bad-jwks'}

    get_key_mock.side_effect = Exception("key failure")

    response = test_client.get(
        '/retrieve_file?file_key=README.md',
        headers={'Authorization': 'Bearer token'}
    )

    assert response.status_code == 401