import httpx as client


def get_access_token(token_creds: dict[str: str]) -> str:
    params = {
        'client_id':  token_creds["client_id"],
        'client_secret': token_creds["client_secret"],
        'grant_type': 'client_credentials',
        'scope': 'api://laa-sds-local/.default'
        }
    response = client.post(token_creds["token_url"], data=params)
    return response.json().get("access_token")


def get_authorised_headers(token_creds: dict[str: str]) -> dict[str: str]:
    access_token = get_access_token(token_creds)
    return {'Authorization': f'Bearer {access_token}'}
