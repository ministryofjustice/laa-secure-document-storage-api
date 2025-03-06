import os
from typing import Tuple
import requests
import structlog
from cachetools import cached, TTLCache
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, jwk, JWTError
from starlette.authentication import AuthenticationBackend, SimpleUser, AuthCredentials, BaseUser, AuthenticationError
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse, Response

security = HTTPBearer()
logger = structlog.get_logger()


class DetailedAuthenticationError(AuthenticationError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.status_code} {self.detail}"


class BearerTokenMiddleware(AuthenticationMiddleware):
    @staticmethod
    def default_on_error(conn: HTTPConnection, exc: Exception) -> Response:
        if isinstance(exc, AuthenticationError) and hasattr(exc, "status_code"):
            return PlainTextResponse(str(exc), status_code=exc.status_code)
        return PlainTextResponse(str(exc), status_code=401)


class BearerTokenAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection) -> tuple[AuthCredentials, BaseUser] | None:
        if "Authorization" not in conn.headers:
            logger.info('No auth headers')
            return None

        authorization: str = conn.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            logger.info(f'Incorrect authorisation scheme {scheme}')
            raise DetailedAuthenticationError(status_code=401, detail="Incorrect authorisation scheme")

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

    # Fetch the OpenID configuration to get the JWK URI
    oidc_config = fetch_oidc_config(tenant_id)
    jwks_uri = oidc_config['jwks_uri']

    jwks = fetch_jwks(jwks_uri)

    unverified_header = jwt.get_unverified_header(token)

    rsa_key_data = None

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key_data = key
            break

    if not rsa_key_data:
        logger.error(f"No rsa key found")
        raise DetailedAuthenticationError(status_code=401, detail="Invalid or expired token")

    try:
        rsa_key = jwk.construct(rsa_key_data, 'RS256')
        payload = jwt.decode(
            token,
            rsa_key.to_dict(),
            algorithms=['RS256'],
            audience=aud,
            issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        )
    except Exception as error:
        logger.error(f"The token is invalid: {error.__class__.__name__} {error}")
        raise DetailedAuthenticationError(status_code=401, detail="Invalid or expired token")

    # Ensure token has `azp` claim which is used to identify the client
    if payload.get('azp') is None:
        logger.error(f"No verified azp claim. Verified claims {payload.keys()}")
        raise DetailedAuthenticationError(status_code=403, detail="Not authenticated")

    roles = payload.get('roles', [])
    if 'LAA_SDS.ALL' not in roles and 'SDS.READ' not in roles:
        logger.error(f"Token validates, but is missing required LAA_SDS.ALL or SDS.READ roles. Got {roles}")
        raise DetailedAuthenticationError(status_code=403, detail="Not authenticated")

    return payload
