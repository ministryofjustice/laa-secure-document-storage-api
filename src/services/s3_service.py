import os
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

bucket = 'ss-poc-test'
load_dotenv()

class S3Service:
    _instance = None
    
    def __init__(self):
        if S3Service._instance is not None:
            raise Exception("This class a singleton!")
        else:
            S3Service._instance = self
            self._s3_client = boto3.client('s3', region_name='us-east-1',
                                           endpoint_url="http://localhost:4566")
            self._s3_client = None
            
    @staticmethod
    def getInstance():
        if S3Service._instance is None:
            S3Service()
        return S3Service._instance

def save(file: BytesIO, filename: str) -> bool:
    region_name = os.getenv("AWS_REGION")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")

    s3_client = boto3.client('s3', region_name=region_name, endpoint_url=endpoint_url)
    try:
        s3_client.upload_fileobj(file, bucket, filename)
    except ClientError:
        return False
    return True