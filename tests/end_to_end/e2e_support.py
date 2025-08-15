import mimetypes
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


def get_mimetype(filename: str) -> str:
    mimetype = mimetypes.guess_type(filename)[0]
    # Bit of a bodge as mimetype.guess_type can fail with text files
    if mimetype is None:
        mimetype = "text/plain"
    return mimetype


def get_file_data_for_request(filename: str, newfilename: str = "") -> dict[str, tuple]:
    """Returns file details/data in format that works with requests' or httpx's
    files parameter.
    Optional newfilename parameter enables the filename in the request to be different from the
    name of the file that's read, so we can submit the same file multiple times but assign a
    different filename each time when sending it.
    """
    if not newfilename:
        newfilename = filename
    return {'file': (newfilename,
                     open(filename, 'rb'),
                     get_mimetype(filename)
                     )
            }
