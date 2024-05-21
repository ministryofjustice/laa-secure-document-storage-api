import os
import boto3
import pytest
from botocore.exceptions import ClientError

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
    mocker.patch.object(s3_service.s3_client,'head_object').return_value = {'anything other than exception'}
    s3_service.generate_file_url('test_bucket', 'test_key')
    mock_generate_presigned_url.assert_called_once_with(
        'get_object',
        Params={'Bucket': 'test_bucket', 'Key': 'test_key'},
        ExpiresIn=60
    )

def test_generate_file_url_missing_file(s3_service, mocker):
    mocker.patch.object(s3_service.s3_client,'head_object').side_effect = ClientError(error_response={'Error': {'Code': '404', 'Message': 'Not Found'}},operation_name='head')
    try:
        s3_service.generate_file_url('test_bucket', 'test_key')

    except Exception as e:
        # Assert
        assert str(e) == 'The file test_key could not be found.'


