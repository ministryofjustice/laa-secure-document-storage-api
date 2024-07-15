import os
from typing import Tuple

import requests
import structlog
from cachetools import cached, TTLCache
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, jwk
from starlette.responses import JSONResponse

security = HTTPBearer()
logger = structlog.get_logger()


async def bearer_token_middleware(request: Request, call_next):
    try:
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            raise HTTPException(status_code=403, detail="Not authenticated")
        is_valid, payload = validate_token(param, os.getenv('AUDIENCE'), os.getenv('TENANT_ID'))
        if is_valid:
            request.state.payload = payload
            response = await call_next(request)
            return response
        else:
            raise HTTPException(status_code=403, detail="Not authenticated")
    except HTTPException as http_exc:
        return JSONResponse({"detail": http_exc.detail}, http_exc.status_code)
    except Exception as e:
        return JSONResponse({"detail": "Something went wrong"}, 500)  # Replace this with proper logging




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
            logger.debug(f'The token is invalid: {error}')

    return is_valid, payload








