import os
import boto3
from dotenv import load_dotenv

class S3Service:
    _instance = None

    def __init__(self):
        if S3Service._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            S3Service._instance = self
            self._s3_client = None

    @staticmethod
    def getInstance():
        if S3Service._instance is None:
            S3Service()
        return S3Service._instance

    def __call__(self):
        if self._s3_client is None:
            load_dotenv()
            env = os.getenv("ENV", "dev")
            if env == "dev":  # Local Environment
                # Reads from .env file
                region_name = os.getenv("AWS_REGION")
                endpoint_url = os.getenv("AWS_ENDPOINT_URL")
                self._s3_client = boto3.client('s3', region_name=region_name, endpoint_url=endpoint_url)
            else:  # Production Environment
                # Defaults to environment settings
                self._s3_client = boto3.client('s3')
        return self._s3_client