from io import BytesIO
from typing import Dict

import boto3
import os

import structlog
from botocore.exceptions import ClientError

from src.models.client_config import ClientConfig
from src.models.execeptions.file_not_found import FileNotFoundException
from src.models.status_report import ServiceObservations, Category
from src.services import client_config_service
from src.utils.status_reporter import StatusReporter
from src.services.checksum_service import hex_string_to_base64_encoded

logger = structlog.get_logger()


class S3ClientConfigService:
    """
    Gets client config filenames and files from client config S3 bucket.
    Because these files only change from time-to-time, the details are held within the following
    attributes:
        self.filenames - all filenames
        self.csv_filenames - csv filenames only
        self.json_filenames - json filenames only

    To refresh these details call the populate_filenames method. This will run automatically
    when instance created if auto_populate parameter is True.

    Note this only creates a temporary S3 client each time bucket accessed. Could change,
    not sure what difference this makes - is there a constant connection otherwise? As
    client is presumably sending requests behind the scenes, maybe not?
    """
    def __init__(self, auto_populate: bool = True):
        self.bucket = os.getenv("CLIENT_CONFIG_BUCKET_NAME", "sds-client-configs")
        self.filenames = []
        self.csv_filenames = []
        self.json_filenames = []
        if auto_populate:
            self.populate_filenames()

    def get_s3_client(self):
        # This duplicates S3Serivce.get_s3_client class method
        # Could change this to a free-standing function shared by both classes
        # but keeping separate for now to avoid disruption to existing functionality
        # (alternatively could go for inheritance-based approach but that might overcomplicate things)
        s3_client = boto3.client(
            's3',
            region_name=os.getenv('AWS_REGION', 'eu-west-2'),
            aws_access_key_id=os.getenv('AWS_KEY_ID', ''),
            aws_secret_access_key=os.getenv('AWS_KEY', ''),
            endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
            )
        return s3_client

    def get_details_of_files(self, max_calls: int = 3, max_keys: int = 1000) -> list[dict]:
        s3_client = self.get_s3_client()
        all_file_details = []
        continuation_token: str | None = None
        # Need to iterate because there is a maximum number of files that can be returned in one
        # list_objects_v2 call. Default is 1000 which should be enough, but just in case.
        for _ in range(max_calls):
            if not continuation_token:
                returned_file_details = s3_client.list_objects_v2(Bucket=self.bucket, MaxKeys=max_keys)
            else:
                returned_file_details = s3_client.list_objects_v2(Bucket=self.bucket, MaxKeys=max_keys,
                                                                  ContinuationToken=continuation_token)
            all_file_details.append(returned_file_details)
            # Can stop iteration if returned details NOT truncated (so we must have all)
            if returned_file_details.get("IsTruncated", False) is False:
                break
            else:
                continuation_token = returned_file_details.get("NextContinuationToken")
        s3_client.close()
        return all_file_details

    def populate_filenames(self):
        self.filenames = []
        file_details: list[dict] = self.get_details_of_files()
        for file_collection in file_details:
            contents = file_collection.get("Contents", [])
            self.filenames.extend([c.get("Key") for c in contents])
        # If final file collection has "IsTruncated" True, then we don't have complete set of details
        truncation_flag = file_collection.get("IsTruncated", False)
        if truncation_flag:
            logger.warning("Config file read from S3 failed to read all the files. Could be too many files.")
        self.csv_filenames = [f for f in self.filenames if f.lower().endswith(".csv")]
        self.json_filenames = [f for f in self.filenames if f.lower().endswith(".json")]

    def get_file(self, key: str) -> str:
        """
        Return specified file content as string. Presumably should be
        fine as we're only expecting to read csv and json, not binary.
        """
        s3_client = self.get_s3_client()
        # Could change things so we check file is in self.filenames
        # before atttempting to read it.
        try:
            file_object: dict = s3_client.get_object(Bucket=self.bucket, Key=key)
            file_content = file_object.get("Body").read().decode("utf-8")
        except Exception as exc:
            logger.error(f"Failed to read config file {key}: {exc}")
            file_content = ""
        finally:
            s3_client.close()
        return file_content

    def get_file_lines(self, key: str) -> list[str]:
        """
        Return specified file content as list of line-by-line strings.
        """
        content = self.get_file(key)
        return content.splitlines()


class S3Service:
    _instances: Dict = {}

    @staticmethod
    def get_instance(client: str | ClientConfig) -> 'S3Service':
        """ Static access method. """
        if isinstance(client, ClientConfig):
            username = client.azure_client_id
            client_config = client
        elif isinstance(client, str):
            username = client
            client_config = client_config_service.get_config_for_client(username)
        else:
            raise ValueError(f"Invalid type for client: {type(client)}")

        if username not in S3Service._instances:
            S3Service._instances[username] = S3Service(client_config)

        return S3Service._instances[username]

    @staticmethod
    def clear_cache():
        logger.info(f'Clearing {len(S3Service._instances)} cached S3Service instances')
        S3Service._instances.clear()

    def __init__(self, client_config: ClientConfig):
        self.client_config = client_config
        self.s3_client = self.get_s3_client()

    @classmethod
    def get_s3_client(cls):
        if os.getenv('ENV') == 'local':
            s3_client = boto3.client(
                's3',
                region_name=os.getenv('AWS_REGION', 'eu-west-2'),
                aws_access_key_id=os.getenv('AWS_KEY_ID', ''),
                aws_secret_access_key=os.getenv('AWS_KEY', ''),
                endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
            )
        else:
            s3_client = boto3.client(
                's3',
                region_name=os.getenv('AWS_REGION', 'eu-west-2')
            )
        return s3_client

    def generate_file_url(self, key, expiration=60):
        try:
            logger.info(f"Generating URL for file {key} from bucket {self.client_config.bucket_name}")
            # Check if the file exists by trying to get its metadata
            self.s3_client.head_object(Bucket=self.client_config.bucket_name, Key=key)
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.client_config.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundException(f'The file {key} could not be found.', key)
            else:
                # If it was a different kind of error, re-raise the original exception
                raise
        except Exception as e:
            logger.error(f"{e.__class__.__name__} generating file URL from S3: {str(e)}")

    def read_file_from_s3_bucket(self, key):
        try:
            file_object = self.s3_client.get_object(Bucket=self.client_config.bucket_name, Key=key)
            return file_object["Body"].read().decode('utf-8')
        except Exception as e:
            logger.debug(f"{e.__class__.__name__} reading file from S3: {str(e)}")

    def upload_file_obj(self, file: BytesIO, filename: str, checksum: str, metadata: dict | None = None):
        if metadata is None:
            metadata = {}
        logger.debug(f"Uploading file with name {filename} to S3 bucket {self.client_config.bucket_name}")
        checksum_base64 = hex_string_to_base64_encoded(checksum)
        try:
            self.s3_client.put_object(
                Bucket=self.client_config.bucket_name,
                Key=filename,
                Body=file.read(),
                ChecksumAlgorithm="SHA256",
                ChecksumSHA256=checksum_base64,
                Metadata=metadata
            )
        except Exception as e:
            logger.error(f"{e.__class__.__name__} uploading file to S3: {str(e)}")
            raise e

    def list_object_versions(self, file_key):
        try:
            response = self.s3_client.list_object_versions(
                Bucket=self.client_config.bucket_name,
                Prefix=file_key
            )
            return response.get('Versions', [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list versions for {file_key}: {e}")

    def delete_object_version(self, filename: str, version_id: str):
        try:
            logger.debug(
                f"Attempting to delete version {version_id} of file {filename} "
                f"from S3 bucket {self.client_config.bucket_name}"
            )

            self.s3_client.delete_object(
                Bucket=self.client_config.bucket_name,
                Key=filename,
                VersionId=version_id
            )
            logger.info(
                f"Version {version_id} of file {filename} "
                f"successfully deleted from bucket {self.client_config.bucket_name}"
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey" or error_code == "404":
                logger.warning(
                    f"Version {version_id} of file {filename} not found in bucket {self.client_config.bucket_name}"
                )
                raise FileNotFoundError(
                    f"Version {version_id} of file {filename} not found in bucket {self.client_config.bucket_name}"
                )
            else:
                logger.error(
                    f"{e.__class__.__name__} deleting version {version_id} of file {filename} from S3: {str(e)}"
                )
                raise

    def file_exists_in_bucket(self, key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.client_config.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                return False  # file doesn't exist
            else:
                raise e  # something else went wrong (e.g. permissions)


def file_exists(client: str | ClientConfig, file_name: str) -> bool:
    s3_service = S3Service.get_instance(client)
    return s3_service.file_exists_in_bucket(file_name)


def retrieve_file(client: str | ClientConfig, file_name: str):
    s3_service = S3Service.get_instance(client)
    return s3_service.read_file_from_s3_bucket(file_name)


def retrieve_file_url(client: str | ClientConfig, file_name: str):
    s3_service = S3Service.get_instance(client)
    logger.info(f"bucket name is {s3_service.client_config.bucket_name}")
    return s3_service.generate_file_url(file_name)


def save(client: str | ClientConfig, file: BytesIO, file_name: str,
         checksum: str, metadata: dict | None = None) -> bool:
    if metadata is None:
        metadata = {}

    s3_service = S3Service.get_instance(client)
    s3_service.upload_file_obj(file, file_name, checksum, metadata)

    return True


def list_file_versions(client: str | ClientConfig, file_name: str):
    s3_service = S3Service.get_instance(client)
    return s3_service.list_object_versions(file_name)


def delete_file_version(client: str | ClientConfig, file_name: str, version_id: str):
    s3_service = S3Service.get_instance(client)
    return s3_service.delete_object_version(file_name, version_id)


class S3ServiceStatusReporter(StatusReporter):

    @classmethod
    def get_status(cls) -> ServiceObservations:
        """
        Reachable if service responds.
        Responding if service operations respond.
        """
        checks = ServiceObservations(label='storage')
        reachable, responding = checks.add_checks('reachable', 'responding')

        try:
            # S3 access normally requires a ClientConfig to access the correct bucket, but the config
            # is not needed to validate the connection to the service. So we do not pass a config, and
            # directly get the S3 client.
            client = S3Service.get_s3_client()
            # We check for a bucket we know does not exist, and if the service is active it will respond
            # with a Not Found error rather than a Connection Error.
            client.head_bucket(Bucket='does-not-exist')
            logger.error('Unexpectedly succeeded when checking for a resource which should not exist or be available')
        except ClientError as ce:
            # We checked for a non-existent bucket, so check if we have the expected error
            if ce.response['Error']['Code'] == '404' or ce.response['Error']['Code'] == '403':
                reachable.category = Category.success
                responding.category = Category.success
            else:
                logger.error('Unexpected error type')
        except Exception as e:
            logger.error(f'Status check {cls.label} failed: {e.__class__.__name__} {e}')

        return checks
