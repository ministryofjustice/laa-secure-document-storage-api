import os
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError
from io import BytesIO

import src.services.s3_service
from src.models.execeptions.file_not_found import FileNotFoundException
from src.models.client_config import ClientConfig
from src.services.s3_service import S3Service
import structlog

logger = structlog.get_logger()


@pytest.fixture(scope='module')
def s3_service():
    os.environ['ENV'] = 'local'
    os.environ['AWS_REGION'] = 'us-west-1'
    os.environ['AWS_KEY_ID'] = 'your_access_key_id'
    os.environ['AWS_KEY'] = 'your_secret_access_key'
    os.environ['BUCKET_NAME'] = 'test_bucket'
    with patch.object(src.services.s3_service, 'get_config_for_client', return_value=ClientConfig(
        client='test_user', bucket_name=os.getenv('BUCKET_NAME'), service_id='test', region_name=os.getenv('AWS_REGION')
    )) as mock_config:
        instance = S3Service.get_instance('test_user')
        mock_config.assert_called()
        return instance


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
    mocker.patch.object(s3_service.s3_client, 'head_object').return_value = {'anything other than exception'}
    s3_service.generate_file_url('test_key')
    mock_generate_presigned_url.assert_called_once_with(
        'get_object',
        Params={'Bucket': 'test_bucket', 'Key': 'test_key'},
        ExpiresIn=60
    )


def test_generate_file_url_missing_file(s3_service, mocker):
    mocker.patch.object(s3_service.s3_client, 'head_object').side_effect = ClientError(
        error_response={'Error': {'Code': '404', 'Message': 'Not Found'}}, operation_name='head')
    try:
        s3_service.generate_file_url('test_key')

    except FileNotFoundException as e:
        # Assert
        assert str(e.message) == 'The file test_key could not be found.'
        assert str(e.filename) == 'test_key'


def test_upload_file_obj_success(s3_service, mocker):
    # Arrange
    mock_put_object = mocker.patch.object(s3_service.s3_client, 'put_object')

    file = BytesIO(b"Test data")
    bucket_name = 'test_bucket'
    filename = 'test_file'
    metadata = {'key1': 'value1'}

    # Act
    s3_service.upload_file_obj(file, filename, metadata)

    # Assert
    mock_put_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=filename,
        Body=file.getvalue(),
        Metadata=metadata
    )


def test_upload_file_obj_bucket_non_existent(s3_service, mocker):
    # Arrange
    error_response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'The specified bucket does not exist'}}
    mocker.patch.object(
        s3_service.s3_client,
        'put_object',
        side_effect=ClientError(error_response=error_response, operation_name='PutObject')
    )

    file = BytesIO(b"Test data")
    bucket_name = 'test_bucket'
    filename = 'test_file'
    metadata = {'key1': 'value1'}

    # Act and Assert
    with pytest.raises(ClientError) as ex:
        s3_service.upload_file_obj(file, filename, metadata)

    assert ex.value.response['Error']['Code'] == 'NoSuchBucket'
    assert str(
        ex.value) == ('An error occurred (NoSuchBucket) when calling the PutObject operation: '
                      'The specified bucket does not exist')
