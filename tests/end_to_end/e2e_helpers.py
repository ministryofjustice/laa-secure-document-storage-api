import mimetypes
import time
import json
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


def post_a_file(url: str, headers: dict[str, str], file_data: dict[str, tuple]) -> client.Response:
    "Upload a file for data setup purposes"
    upload_bucket = '{"bucketName": "sds-local"}'
    response = client.put(f"{url}/save_or_update_file",
                          headers=headers,
                          files=file_data,
                          data={"body": upload_bucket})
    return response


def read_postman_env_file(postman_environment_json_file: str
                          = "Postman/SDSLocal.postman_environment.json") -> dict[str, str]:
    """
    The environment files used by our Postman tests are a potential source of test environment data.
    This function extracts the application URL and token URL from one of these files.
    """
    environment_info = {}

    with open(postman_environment_json_file, "r") as infile:
        extracted_data = json.load(infile)

    environment_info["name"] = extracted_data.get("name")
    # Values should be unique, so a set would seem better choice than a list.
    # However, we later want to remove items during iteration and this
    # is difficult to do with a set.
    keys_to_find = ["SDSBaseUrl", "AzureTokenUrl"]
    for item in extracted_data.get("values", []):
        for key_to_find in keys_to_find:
            if item.get("key") == key_to_find:
                keys_to_find.remove(key_to_find)
                environment_info[key_to_find] = item.get("value")
        if keys_to_find == []:
            break

    return environment_info
