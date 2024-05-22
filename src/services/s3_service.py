import boto3
import os

import structlog
from botocore.exceptions import ClientError

from src.models.execeptions.file_not_found import FileNotFoundException
logger = structlog.get_logger()

class S3Service:
    _instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if S3Service._instance is None:
            S3Service()
        return S3Service._instance

    def __init__(self):
        """ Virtually private constructor. """
        if S3Service._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            S3Service._instance = self
            self.s3_client = self.get_s3_client()

    def get_s3_client(self):
        if os.getenv('ENV') != 'local':
            s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION'))  # add appropriate AWS region
        else:  # for local S3 like localstack
            s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_KEY'),
                region_name=os.getenv('AWS_REGION'),
                endpoint_url='http://localhost:4566')  # change this to actual localstack s3 endpoint
        return s3_client

    def generate_file_url(self, bucket_name, key, expiration=60):
        try:
            # Check if the file exists by trying to get its metadata
            self.s3_client.head_object(Bucket=bucket_name, Key=key)

            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': key},
                ExpiresIn=expiration)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundException(f'The file {key} could not be found.', key)
            else:
                # If it was a different kind of error, re-raise the original exception
                raise
        except Exception as e:
            logger.debug(f"Error generating file URL from S3: {str(e)}")

    def read_file_from_s3_bucket(self, bucket_name, key):
        try:
            file_object = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            return file_object["Body"].read().decode('utf-8')
        except Exception as e:
            logger.debug(f"Error reading file from S3: {str(e)}")


def retrieveFile(fileName: str):
    s3_service = S3Service.getInstance()
    return s3_service.read_file_from_s3_bucket(os.getenv('BUCKET_NAME'), fileName)


def retrieveFileUrl(fileName: str):
    s3_service = S3Service.getInstance()
    return s3_service.generate_file_url(os.getenv('BUCKET_NAME'), fileName)
