from unittest.mock import patch
import pytest
import structlog
from fastapi.testclient import TestClient
from jose import jwt, JWTError
from jose.exceptions import JWTClaimsError

from src.main import app

test_client = TestClient(app)
logger = structlog.get_logger()


class FakeKey:
    def to_dict(self):
        return {'key': 'value'}

MOCK_OIDC_CONFIG = {'jwks_uri': 'mock_uri'}
MOCK_JWKS = {'keys': [{'kid': 'mock_value'}, ]}
MOCK_HEADER = MOCK_JWKS['keys'][0]
MOCK_KEY = FakeKey()


@pytest.mark.normal_auth
def test_incorrect_auth_scheme(audit_service_mock):
    response = test_client.get('/retrieve_file?file_key=README.md', headers={'Authorization': 'Notbearer token'})
    assert response.status_code == 401


@pytest.mark.normal_auth
@patch('src.middleware.auth.jwt.decode')
@patch('src.middleware.auth.jwk.construct')
@patch('src.middleware.auth.jwt.get_unverified_header')
@patch('src.middleware.auth.fetch_jwks')
@patch('src.middleware.auth.fetch_oidc_config')
def test_missing_azp_claim(oidc_mock, jwks_mock, unv_header_mock, key_construct_mock, decode_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    jwks_mock.return_value = MOCK_JWKS
    unv_header_mock.return_value = MOCK_HEADER
    key_construct_mock.return_value = MOCK_KEY

    decode_mock.return_value = {'sub': 'test_user', 'iss': 'https://login.microsoftonline.com/123456'}

    response = test_client.get('/retrieve_file?file_key=README.md', headers={'Authorization': 'Bearer token'})
    decode_mock.assert_called_once()
    assert response.status_code == 403


@pytest.mark.normal_auth
@patch('src.middleware.auth.jwt.decode')
@patch('src.middleware.auth.jwk.construct')
@patch('src.middleware.auth.jwt.get_unverified_header')
@patch('src.middleware.auth.fetch_jwks')
@patch('src.middleware.auth.fetch_oidc_config')
def test_incorrect_roles(oidc_mock, jwks_mock, unv_header_mock, key_construct_mock, decode_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    jwks_mock.return_value = MOCK_JWKS
    unv_header_mock.return_value = MOCK_HEADER
    key_construct_mock.return_value = MOCK_KEY

    decode_mock.return_value = {
        'sub': 'test_user', 'iss': 'https://login.microsoftonline.com/123456', 'azp': 'test_user', 'roles': ['MISS', ]
    }

    response = test_client.get('/retrieve_file?file_key=README.md', headers={'Authorization': 'Bearer token'})
    decode_mock.assert_called_once()
    assert response.status_code == 403


@pytest.mark.normal_auth
@patch('src.middleware.auth.jwt.decode')
@patch('src.middleware.auth.jwk.construct')
@patch('src.middleware.auth.jwt.get_unverified_header')
@patch('src.middleware.auth.fetch_jwks')
@patch('src.middleware.auth.fetch_oidc_config')
def test_token_decode_expired_signature(oidc_mock, jwks_mock, unv_header_mock, key_construct_mock, decode_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    jwks_mock.return_value = MOCK_JWKS
    unv_header_mock.return_value = MOCK_HEADER
    key_construct_mock.return_value = MOCK_KEY

    decode_mock.side_effect = jwt.ExpiredSignatureError()
    decode_mock.return_value = {'sub': 'test_user', 'iss': 'https://login.microsoftonline.com/123456', 'azp': 'test_user'}

    response = test_client.get('/retrieve_file?file_key=README.md', headers={'Authorization': 'Bearer token'})
    decode_mock.assert_called_once()
    assert response.status_code == 401


@pytest.mark.normal_auth
@patch('src.middleware.auth.jwt.decode')
@patch('src.middleware.auth.jwk.construct')
@patch('src.middleware.auth.jwt.get_unverified_header')
@patch('src.middleware.auth.fetch_jwks')
@patch('src.middleware.auth.fetch_oidc_config')
def test_token_decode_jwterror(oidc_mock, jwks_mock, unv_header_mock, key_construct_mock, decode_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    jwks_mock.return_value = MOCK_JWKS
    unv_header_mock.return_value = MOCK_HEADER
    key_construct_mock.return_value = MOCK_KEY

    decode_mock.side_effect = JWTError()
    decode_mock.return_value = {'sub': 'test_user', 'iss': 'https://login.microsoftonline.com/123456', 'azp': 'test_user'}

    response = test_client.get('/retrieve_file?file_key=README.md', headers={'Authorization': 'Bearer token'})
    decode_mock.assert_called_once()
    assert response.status_code == 401


@pytest.mark.normal_auth
@patch('src.middleware.auth.jwt.decode')
@patch('src.middleware.auth.jwk.construct')
@patch('src.middleware.auth.jwt.get_unverified_header')
@patch('src.middleware.auth.fetch_jwks')
@patch('src.middleware.auth.fetch_oidc_config')
def test_token_decode_jwtclaimserror(oidc_mock, jwks_mock, unv_header_mock, key_construct_mock, decode_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    jwks_mock.return_value = MOCK_JWKS
    unv_header_mock.return_value = MOCK_HEADER
    key_construct_mock.return_value = MOCK_KEY

    decode_mock.side_effect = JWTClaimsError()
    decode_mock.return_value = {'sub': 'test_user', 'iss': 'https://login.microsoftonline.com/123456', 'azp': 'test_user'}

    response = test_client.get('/retrieve_file?file_key=README.md', headers={'Authorization': 'Bearer token'})
    decode_mock.assert_called_once()
    assert response.status_code == 401


@pytest.mark.normal_auth
@patch('src.middleware.auth.jwt.decode')
@patch('src.middleware.auth.jwk.construct')
@patch('src.middleware.auth.jwt.get_unverified_header')
@patch('src.middleware.auth.fetch_oidc_config')
def test_jwks_uri_invalid(oidc_mock, unv_header_mock, key_construct_mock, decode_mock, audit_service_mock):
    # Tests the processing chain when the jwks_uri is not found or malformed
    oidc_mock.return_value = {'jwks_uri': 'mock_uri'}
    unv_header_mock.return_value = MOCK_HEADER
    key_construct_mock.return_value = MOCK_KEY

    decode_mock.return_value = {'sub': 'test_user', 'iss': 'https://login.microsoftonline.com/123456', 'azp': 'test_user'}

    response = test_client.get('/retrieve_file?file_key=README.md', headers={'Authorization': 'Bearer token'})
    decode_mock.assert_not_called()

    assert response.status_code == 401


@pytest.mark.normal_auth
@patch('src.middleware.auth.jwt.decode')
@patch('src.middleware.auth.jwk.construct')
@patch('src.middleware.auth.jwt.get_unverified_header')
@patch('src.middleware.auth.fetch_jwks')
@patch('src.middleware.auth.fetch_oidc_config')
def test_rsa_key_missing(oidc_mock, jwks_mock, unv_header_mock, key_construct_mock, decode_mock, audit_service_mock):
    oidc_mock.return_value = MOCK_OIDC_CONFIG
    jwks_mock.return_value = MOCK_JWKS
    unv_header_mock.return_value = {'kid': 'incorrect_value'}
    key_construct_mock.return_value = MOCK_KEY

    decode_mock.return_value = {'sub': 'test_user', 'iss': 'https://login.microsoftonline.com/123456', 'azp': 'test_user'}

    response = test_client.get('/retrieve_file?file_key=README.md', headers={'Authorization': 'Bearer token'})
    decode_mock.assert_not_called()
    assert response.status_code == 401
