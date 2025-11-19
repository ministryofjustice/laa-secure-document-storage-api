import mimetypes
import time
import json
import os
from dotenv import load_dotenv
from typing import Any
import boto3
import httpx as client


"""
Everything here is intended to support end-to-end tests.
This is not application code.
"""

load_dotenv()


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

    def get_headers(self) -> dict[str, str]:
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
        "Returns file data in dict format that's needed for individual file upload"
        if new_filename:
            self.update_filename(new_filename)
        self.reset_seek()
        return self.file_details

    def get_data_tuple(self, new_filename: str = ""):
        "Returns file data in tuple format that's needed for bulk upload"
        dict_details = self.get_data(new_filename)
        return ('files', dict_details["file"])

    def close_file(self):
        """
        Closing the file will prevent it from being used.
        Only intended for test cleanup step.
        """
        self.file_details["file"][1].close()


def get_mimetype(filename: str) -> str:
    mimetype = mimetypes.guess_type(filename)[0]
    # Bit of a bodge as mimetype.guess_type can fail with text files
    if mimetype is None:
        mimetype = "text/plain"
    return mimetype


class LocalS3:
    """
    Intended to enable independent checks of S3 content to support e2e tests.
    Created to work with Localstack S3 but should work with actual AWS
    as long as the environment variables are set appropriately. The
    default environment values within this class are sufficient for our Localstack.

    Could use SDS application's own S3 service to do the same but this:
    (a) Gives independence, so e2e tests are not dependent on application code
    (b) Is deliberately shorter to be easier to understand
    (c) Has built-in mocking
    """
    def __init__(self, bucket_name: str = "sds-local", mocking_enabled=False):
        """
        mocking_enabled - this flag causes the check_file_exists method to return
        a mock value. This is for circumstances in which actual S3 access is not
        wanted or possble.
        """
        self.client = boto3.client(
            's3',
            region_name=os.getenv('AWS_REGION', 'eu-west-2'),
            aws_access_key_id=os.getenv('AWS_KEY_ID', ''),
            aws_secret_access_key=os.getenv('AWS_KEY', ''),
            endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
            )
        self.bucket_name = bucket_name
        self.mocking_enabled = mocking_enabled

    def check_file_exists(self, key: str, mock_result: Any = "") -> bool:
        if self.mocking_enabled:
            return mock_result
        response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=key)
        for obj in response.get('Contents', []):
            if obj['Key'] == key:
                return True
        return False

    def list_versions(self, key: str, mock_keys: list[str] = None) -> list[str]:
        if self.mocking_enabled:
            # Return mock version IDs if mocking is enabled
            return mock_keys or []
        response = self.client.list_object_versions(
            Bucket=self.bucket_name,
            Prefix=key
        )
        versions = response.get("Versions", [])
        return [v["VersionId"] for v in versions if v["Key"] == key]


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


def get_token_manager() -> TokenManager:
    postman_env_details = read_postman_env_file()
    postman_token_url = postman_env_details.get("AzureTokenUrl")
    return TokenManager(client_id=os.getenv('CLIENT_ID'),
                        client_secret=os.getenv('CLIENT_SECRET'),
                        token_url=os.getenv('TOKEN_URL', postman_token_url)
                        )


def get_host_url() -> str:
    return os.getenv('HOST_URL', 'http://127.0.0.1:8000')


def get_upload_body() -> dict[str, dict[str, str]]:
    return {"body": '{"bucketName": "sds-local"}'}


class AuditDynamoDBClient:
    """
    Enables checks of the DynamoDb audit table contents.
    Created to work with LocalStack database. Unlikely to work in real
    environments as their audit tables are set to write-only.

    Has a mocking_enabled flag that turns off actual database access and
    returns dummy values. Intended for circumstances in which the audit
    table access is not wanted or possible.
    """
    def __init__(self, mocking_enabled=False):
        self.mocking_enabled = mocking_enabled
        self.client = boto3.client(
            service_name='dynamodb',
            region_name=os.getenv('AWS_REGION', 'eu-west-2'),
            aws_access_key_id=os.getenv('AWS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_KEY', 'test'),
            endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://127.0.0.1:4566')
            )
        self.available_table_names = []

    def get_table_names(self) -> list[str]:
        if self.mocking_enabled:
            return ["dummy_table"]
        table_list_response = self.client.list_tables()
        table_names = table_list_response.get("TableNames")
        return table_names

    def get_audit_row(self,
                      request_id: str,
                      filename_position: int | str = "0",
                      table_name: str = "") -> dict:
        if self.mocking_enabled:
            return {'filename_position': {'N': '0'},
                    'operation_type': {'S': 'READ'},
                    'created_on': {'S': '2025-01-01T11:59:59.000000'},
                    'error_details': {'S': ''},
                    'service_id': {'S': 'laa-sds-client-local'},
                    'file_id': {'S': 'dummy.txt'},
                    'request_id': {'S': 'dummy_id_value'}}

        # self.available_table_names *not* populated in __init__ because we need to be
        # able to create an instance in circumstances in which AWS is not available
        # even when mocking_enabled flag is False.
        if not self.available_table_names:
            self.available_table_names = self.get_table_names()

        # Locally should be only one table, so safe to default to 1st one
        if not table_name:
            table_name = self.available_table_names[0]

        # Confusingly the value of filename_postion must be a str even though it's
        # held in database as a number (N), otherwise get "Invalid type for parameter"
        key = {'request_id': {'S': request_id},
               'filename_position': {'N': str(filename_position)}}
        item_response = self.client.get_item(TableName=table_name, Key=key)
        item = item_response.get("Item")
        return item
