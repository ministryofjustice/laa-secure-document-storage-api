import os
import boto3
from botocore.exceptions import ClientError
from io import BytesIO
from dotenv import load_dotenv

bucket = 'ss-poc-test'
load_dotenv()

def save(file: BytesIO, filename: str) -> bool:
    region_name = os.getenv("AWS_REGION")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")

    s3_client = boto3.client('s3', region_name=region_name, endpoint_url=endpoint_url)
    try:
        s3_client.upload_fileobj(file, bucket, filename)
    except ClientError:
        return False
    return True