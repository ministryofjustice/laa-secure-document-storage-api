import requests
from jose import jwt, jwk
from cachetools import cached, TTLCache
from typing import Tuple


# Define caching functions
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

    # Fetch JWKs
    jwks = fetch_jwks(jwks_uri)

    # Decode the token header
    unverified_header = jwt.get_unverified_header(token)

    rsa_key_data = None
    # Find the key in the JWKs
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
            print(f'The token is invalid: {error}')

    return is_valid, payload
