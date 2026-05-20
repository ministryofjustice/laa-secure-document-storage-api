import os

import requests
import structlog
from cachetools import cached, TTLCache
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jwt import PyJWKClient, PyJWKClientError, decode as jwt_decode
from jwt import InvalidTokenError, ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError
import ssl
import certifi
from starlette.authentication import AuthenticationBackend, SimpleUser, AuthCredentials, BaseUser, AuthenticationError
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection
from starlette.responses import Response, JSONResponse

from src.models.status_report import ServiceObservations, Category
from src.utils.status_reporter import StatusReporter

security = HTTPBearer()
logger = structlog.get_logger()
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class _AuthenticationError(AuthenticationError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.status_code} {self.detail}"


class BearerTokenMiddleware(AuthenticationMiddleware):
    @staticmethod
    def default_on_error(conn: HTTPConnection, exc: Exception) -> Response:
        if hasattr(exc, "status_code") and hasattr(exc, "detail"):
            return JSONResponse({"detail": str(exc.detail)}, status_code=exc.status_code)
        return JSONResponse({"detail": str(exc)}, status_code=401)


class BearerTokenAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection) -> tuple[AuthCredentials, BaseUser] | None:

        # Bypass external authentication when running SDS locally if environment variable
        # LOCAL_CONFIG_SKIP_AUTH has value "true" (case insensitive) and the request has
        # 'test-username' value in its headers.
        # Note environment variables have to be strings, so using "true", "false"
        if (conn.client.host == "127.0.0.1"
            and os.getenv("LOCAL_CONFIG_SKIP_AUTH", "false").lower() == "true"
                and conn.headers.get("test-username")):
            username = conn.headers.get('test-username')
            logger.warning(f"Bypassing authentication with username {username}")
            return AuthCredentials(scopes=[]), SimpleUser(username)

        if "Authorization" not in conn.headers:
            logger.info('No auth headers')
            return None

        authorization: str = conn.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            logger.info(f'Incorrect authorisation scheme {scheme}')
            raise _AuthenticationError(status_code=401, detail="Incorrect authorisation scheme")

        payload = validate_token(param, os.getenv('AUDIENCE'), os.getenv('TENANT_ID'))
        username: str = payload.get("azp")
        auth_creds = AuthCredentials(scopes=[])
        user = SimpleUser(username)
        return auth_creds, user


@cached(TTLCache(maxsize=100, ttl=3600))
def fetch_oidc_config(tenant_id):
    url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
    return requests.get(url).json()


def get_signing_key(token: str, jwks_uri: str, bad_token_exception):
    try:
        client = PyJWKClient(jwks_uri, ssl_context=SSL_CONTEXT)

        key = client.get_signing_key_from_jwt(token)
        return key.key
    except PyJWKClientError:
        logger.error("JWK client error")
        raise bad_token_exception
    except Exception as error:
        logger.error(f"Unexpected key error: {error.__class__.__name__}")
        raise bad_token_exception


def validate_token(token: str, aud: str, tenant_id: str) -> dict:
    # Raise any token processing errors as 401 to the client to avoid leaking information
    bad_token_exception = _AuthenticationError(status_code=401, detail="Invalid or expired token")
    # Note None option included for completeness but unlikely for None to reach this point
    # when token originates from request headers.
    if token in ("", "None", None):
        logger.error(f"Empty or invalid token: '{token}'")
        raise bad_token_exception
    try:
        # Fetch the OpenID configuration to get the JWK URI
        oidc_config = fetch_oidc_config(tenant_id)
        jwks_uri = oidc_config['jwks_uri']

        signing_key = get_signing_key(token, jwks_uri, bad_token_exception)

    except Exception as error:
        logger.error(f"Error processing token: {error.__class__.__name__}")
        raise bad_token_exception

    try:
        payload = jwt_decode(
            token,
            signing_key,
            algorithms=['RS256'],
            audience=aud,
            issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        )
    except ExpiredSignatureError as signature_error:
        logger.error(f"Error processing token: Signature invalid {signature_error}")
        raise bad_token_exception
    except (InvalidAudienceError, InvalidIssuerError) as claims_error:
        logger.error(f"Error processing token: Claims error {claims_error}")
        raise _AuthenticationError(status_code=403, detail="Forbidden")
    except InvalidTokenError as error:
        logger.error(f"Unexpected error processing token: {error.__class__.__name__} {error}")
        raise bad_token_exception

    # Ensure token has `azp` claim which is used to identify the client
    if payload.get('azp') is None:
        logger.error(f"No verified azp claim. Verified claims {payload.keys()}")
        raise _AuthenticationError(status_code=403, detail="Forbidden")

    roles = payload.get('roles', [])
    if 'LAA_SDS.ALL' not in roles and 'SDS.READ' not in roles:
        logger.error(f"Token validates, but is missing required LAA_SDS.ALL or SDS.READ roles. Got {roles}")
        raise _AuthenticationError(status_code=403, detail="Forbidden")

    return payload


class AuthServiceStatusReporter(StatusReporter):

    @classmethod
    def get_status(cls) -> ServiceObservations:
        """
        Configured if values set for authenticating.
        Reachable if OIDC can be fetched.
        """
        checks = ServiceObservations(label='authentication')
        configured, reachable = checks.add_checks('configured', 'reachable')

        if os.getenv('AUDIENCE') not in (None, '') and os.getenv('TENANT_ID') not in (None, ''):
            configured.category = Category.success

        try:
            fetch_oidc_config(os.getenv('TENANT_ID'))
            reachable.category = Category.success
        except Exception as error:
            logger.error(f"Status check {cls.label} failed: {error.__class__.__name__} {error}")

        return checks
