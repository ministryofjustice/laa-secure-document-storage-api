import os
import boto3
import pytest
from src.services.s3_service import S3Service


@pytest.fixture(scope='module')
def s3_service():
    os.environ['ENV'] = 'local'
    os.environ['AWS_REGION'] = 'us-west-1'
    os.environ['AWS_KEY_ID'] = 'your_access_key_id'
    os.environ['AWS_KEY'] = 'your_secret_access_key'
    os.environ['BUCKET_NAME'] = 'your_bucket_name'
    return S3Service.getInstance()


def test_get_s3_client_local(s3_service, mocker):
    mock_client = mocker.patch.object(boto3, 'client')
    s3_service.get_s3_client()
    mock_client.assert_called_once_with(
        's3',
        aws_access_key_id=os.getenv('AWS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_KEY'),
        region_name=os.getenv('AWS_REGION'),
        endpoint_url='http://localhost:4566'
    )


def test_generate_file_url(s3_service, mocker):
    mock_generate_presigned_url = mocker.patch.object(s3_service.s3_client, 'generate_presigned_url')
    s3_service.generate_file_url('test_bucket', 'test_key')
    mock_generate_presigned_url.assert_called_once_with(
        'get_object',
        Params={'Bucket': 'test_bucket', 'Key': 'test_key'},
        ExpiresIn=60
    )


def read_file_from_s3_bucket(self, bucket_name, key):
    try:
        file_object = self.s3_client.get_object(Bucket=bucket_name, Key=key)
        file_content = file_object["Body"].read().decode('utf-8')
        return file_content  # Return the file content
    except Exception as e:
        print(f"Error reading file from S3: {str(e)}")
