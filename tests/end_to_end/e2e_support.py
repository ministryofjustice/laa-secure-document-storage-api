import mimetypes
import time
import httpx as client

"""
Everything here is intended to support end-to-end tests.
This is not application code.
"""


class TokenManager:
    def __init__(self, client_id: str, client_secret: str, token_url: str):
        self.token_url = token_url
        self.params = {'client_id':  client_id,
                       'client_secret': client_secret,
                       'grant_type': 'client_credentials',
                       'scope': 'api://laa-sds-local/.default'}

    def get_access_token(self) -> str:
        response = client.post(self.token_url, data=self.params)
        return response.json().get("access_token")

    def get_headers(self) -> dict[str: str]:
        access_token = self.get_access_token()
        return {'Authorization': f'Bearer {access_token}'}


class UploadFileData:
    """
    Helps with file data that's stored in the dictionary format used by
    requests and httpx's files parameter.

    get_data method ensures file's "offset" is returned to the start of the file,
    which is handy when reading the same file more than once. Also gives opportunity
    to assign a different filename within in the payload to be uploaded.
    """

    def __init__(self, file_path: str, new_filename: str = "", autonew: bool = True):
        if new_filename == "" and autonew:
            new_filename = file_path
        self.file_details = {'file': (new_filename,
                                      open(file_path, 'rb'),
                                      get_mimetype(file_path)
                                      )
                             }

    def reset_seek(self, new_reference_point: int = 0):
        self.file_details["file"][1].seek(new_reference_point)

    def update_filename(self, new_filename: str):
        new_tuple = (new_filename,) + self.file_details["file"][1:]
        self.file_details = {"file": new_tuple}

    def get_data(self, new_filename: str = ""):
        if new_filename:
            self.update_filename(new_filename)
        self.reset_seek()
        return self.file_details


def get_mimetype(filename: str) -> str:
    mimetype = mimetypes.guess_type(filename)[0]
    # Bit of a bodge as mimetype.guess_type can fail with text files
    if mimetype is None:
        mimetype = "text/plain"
    return mimetype


def make_unique_name(original_name: str) -> str:
    time.sleep(0.001)
    return f"{time.time()}_{original_name}"


def get_file_data_for_request(filename: str, newfilename: str = "") -> dict[str, tuple]:
    """
    Returns file details/data in format that works with requests' or httpx's
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


def post_a_file(url: str, headers: dict[str: str], filename: str, newfilename: str = "",) -> client.Response:
    """Upload a file for data setup purposes"""
    upload_bucket = '{"bucketName": "sds-local"}'
    file_data = get_file_data_for_request(filename, newfilename)
    response = client.put(f"{url}/save_or_update_file",
                          headers=headers,
                          files=file_data,
                          data={"body": upload_bucket})
    return response
