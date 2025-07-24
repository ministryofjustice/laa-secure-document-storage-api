from io import BytesIO
from typing import Dict

import boto3
import os

import structlog
from botocore.exceptions import ClientError

from src.models.client_config import ClientConfig
from src.models.execeptions.file_not_found import FileNotFoundException
from src.models.status_report import ServiceObservations, Outcome
from src.services import client_config_service
from src.utils.status_reporter import StatusReporter

logger = structlog.get_logger()


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

    def get_s3_client(self):
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

    def upload_file_obj(self, file: BytesIO, filename: str, metadata: dict | None = None):
        if metadata is None:
            metadata = {}
        logger.debug(f"Uploading file with name {filename} to S3 bucket {self.client_config.bucket_name}")
        try:
            self.s3_client.put_object(
                Bucket=self.client_config.bucket_name,
                Key=filename,
                Body=file.read(),
                Metadata=metadata
            )
        except Exception as e:
            logger.error(f"{e.__class__.__name__} uploading file to S3: {str(e)}")
            raise e

    def delete_file_obj(self, filename: str):
        try:
            logger.debug(f"Attempting to delete file {filename} from S3 bucket {self.client_config.bucket_name}")
            self.s3_client.head_object(Bucket=self.client_config.bucket_name, Key=filename)
            self.s3_client.delete_object(
                Bucket=self.client_config.bucket_name,
                Key=filename,
            )
            logger.info(f"File {filename} successfully deleted from bucket {self.client_config.bucket_name}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey" or error_code == "404":
                logger.warning(f"File {filename} not found in bucket {self.client_config.bucket_name}")
                raise FileNotFoundError(f"File {filename} not found in bucket {self.client_config.bucket_name}")
            else:
                logger.error(f"{e.__class__.__name__} deleting file from S3: {str(e)}")
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


def save(client: str | ClientConfig, file: BytesIO, file_name: str, metadata: dict | None = None) -> bool:
    if metadata is None:
        metadata = {}

    s3_service = S3Service.get_instance(client)
    s3_service.upload_file_obj(file, file_name, metadata)

    return True


def delete_file(client: str | ClientConfig, file_name: str):
    s3_service = S3Service.get_instance(client)
    s3_service.delete_file_obj(file_name)

    return True


class S3ServiceStatusReporter(StatusReporter):
    label = 'storage'

    @classmethod
    def get_status(cls) -> ServiceObservations:
        """
        Reachable if service responds.
        Responding if service operations respond.
        """
        checks = ServiceObservations()
        reachable, responding = checks.add_checks('reachable', 'responding')

        try:
            # S3 access normally requires a ClientConfig to access the correct bucket, but the config
            # is not needed to validate the connection to the service. So we do not pass a config, and
            # directly get the S3 client.
            s3_service = S3Service(None)
            client = s3_service.get_s3_client()
            # We check for a bucket we know does not exist, and if the service is active it will respond
            # with a Not Found error rather than a Connection Error.
            client.head_bucket(Bucket='does-not-exist')
            logger.error('Unexpectedly succeeded when checking for a resource which should not exist or be available')
        except ClientError as ce:
            # We checked for a non-existent bucket, so check if we have the expected error
            if ce.response['Error']['Code'] == '404':
                reachable.outcome = Outcome.success
                responding.outcome = Outcome.success
        except Exception as e:
            logger.exception(f'Status check {cls.label} failed: {e.__class__.__name__} {e}')

        return checks
