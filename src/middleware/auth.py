import os
from typing import Tuple
import requests
import structlog
from cachetools import cached, TTLCache
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, jwk, JWTError
from starlette.authentication import AuthenticationBackend, SimpleUser, AuthCredentials, BaseUser
from starlette.requests import HTTPConnection

security = HTTPBearer()
logger = structlog.get_logger()


class BearerTokenAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection) -> tuple[AuthCredentials, BaseUser] | None:
        if "Authorization" not in conn.headers:
            logger.info('No auth headers')
            return
        try:
            authorization: str = conn.headers.get("Authorization")
            scheme, param = get_authorization_scheme_param(authorization)
            if scheme.lower() != "bearer":
                logger.info(f'Incorrect authorisation scheme {scheme}')
                raise HTTPException(status_code=403, detail="Not authenticated")

            is_valid, payload = validate_token(param, os.getenv('AUDIENCE'), os.getenv('TENANT_ID'))
        except JWTError as e:
            logger.error(f"Invalid JWT token: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        except Exception as e:
            logger.error(f"Error processing bearer token: {str(e)}")
            raise HTTPException(status_code=500, detail="Something went wrong")
        if not is_valid:
            raise HTTPException(status_code=403, detail="Not authenticated")
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


def validate_token(token: str, aud: str, tenant_id: str) -> Tuple[bool, dict]:

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

    is_valid = False
    payload = {}

    if rsa_key_data:
        try:
            rsa_key = jwk.construct(rsa_key_data, 'RS256')
            payload = jwt.decode(
                token,
                rsa_key.to_dict(),
                algorithms=['RS256'],
                audience=aud,
                issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0"
            )
            is_valid = True

        except Exception as error:
            logger.error(f"The token is invalid: {error.__class__.__name__} {error}")

            token_aud = jwt.get_unverified_claims(token).get('aud')
            if token_aud != aud:
                logger.error(f"The token audience does not match the expected audience: {token_aud} != {aud}")

        # We use the azp claim as the client username
        if payload.get('azp') is None:
            unverified_claims = jwt.get_unverified_claims(token).keys()
            logger.error(f"No azp claim. Verified claims {payload.keys()}, Unverified claims {unverified_claims}")
            is_valid = False

    return is_valid, payload
