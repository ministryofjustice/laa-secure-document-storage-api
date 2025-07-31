import os

import requests
import structlog
from cachetools import cached, TTLCache
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, jwk
from jose.exceptions import JWTClaimsError, JWTError, ExpiredSignatureError
from starlette.authentication import AuthenticationBackend, SimpleUser, AuthCredentials, BaseUser, AuthenticationError
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection
from starlette.responses import Response, JSONResponse

from src.models.status_report import ServiceObservations, Outcome
from src.utils.status_reporter import StatusReporter

security = HTTPBearer()
logger = structlog.get_logger()


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


@cached(TTLCache(maxsize=100, ttl=3600))
def fetch_jwks(jwks_uri):
    return requests.get(jwks_uri).json()


def validate_token(token: str, aud: str, tenant_id: str) -> dict:
    try:
        # Fetch the OpenID configuration to get the JWK URI
        oidc_config = fetch_oidc_config(tenant_id)
        jwks_uri = oidc_config['jwks_uri']

        jwks = fetch_jwks(jwks_uri)
        unverified_header = jwt.get_unverified_header(token)
    except Exception as error:
        logger.error(f"Error processing token: {error.__class__.__name__} {error}")
        # Raise any token processing errors as 401 to the client to avoid leaking information
        raise _AuthenticationError(status_code=401, detail="Invalid or expired token")

    rsa_key_data = None
    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key_data = key
            break

    if not rsa_key_data:
        logger.error("No rsa key found")
        raise _AuthenticationError(status_code=401, detail="Invalid or expired token")

    try:
        rsa_key = jwk.construct(rsa_key_data, 'RS256')
        payload = jwt.decode(
            token,
            rsa_key.to_dict(),
            algorithms=['RS256'],
            audience=aud,
            issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        )
    except ExpiredSignatureError as signature_error:
        logger.error(f"Error processing token: Signature invalid {signature_error}")
        raise _AuthenticationError(status_code=401, detail="Invalid or expired token")
    except JWTClaimsError as claims_error:
        logger.error(f"Error processing token: Claims error {claims_error}")
        raise _AuthenticationError(status_code=403, detail="Forbidden")
    except JWTError as error:
        logger.error(f"Unexpected error processing token: {error.__class__.__name__} {error}")
        raise _AuthenticationError(status_code=401, detail="Invalid or expired token")

    # Ensure token has `azp` claim which is used to identify the client
    if payload.get('azp') is None:
        logger.error(f"No verified azp claim. Verified claims {payload.keys()}")
        raise _AuthenticationError(status_code=403, detail="Forbidden")

    roles = payload.get('roles', [])
    if 'LAA_SDS.ALL' not in roles and 'SDS.READ' not in roles:
        logger.error(f"Token validates, but is missing required LAA_SDS.ALL or SDS.READ roles. Got {roles}")
        raise _AuthenticationError(status_code=403, detail="Forbidden")

    return payload


class AuthStatusReporter(StatusReporter):
    label = 'authentication'

    @classmethod
    def get_status(cls) -> ServiceObservations:
        """
        Configured if values set for authenticating.
        Reachable if OIDC can be fetched.
        """
        checks = ServiceObservations()
        configured, reachable = checks.add_checks('configured', 'reachable')

        if os.getenv('AUDIENCE') not in (None, '') and os.getenv('TENANT_ID') not in (None, ''):
            configured.outcome = Outcome.success

        try:
            fetch_oidc_config(os.getenv('TENANT_ID'))
            reachable.outcome = Outcome.success
        except Exception as error:
            logger.error(f"Status check {cls.label} failed: {error.__class__.__name__} {error}")

        return checks
