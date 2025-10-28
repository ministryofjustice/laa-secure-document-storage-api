import os
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError
from io import BytesIO

import src.services.s3_service
from src.models.execeptions.file_not_found import FileNotFoundException
from src.models.client_config import ClientConfig
from src.services.s3_service import S3Service, S3ServiceStatusReporter
import structlog

logger = structlog.get_logger()


@pytest.fixture(scope='module')
def s3_service():
    os.environ['ENV'] = 'local'
    os.environ['AWS_REGION'] = 'us-west-1'
    os.environ['AWS_KEY_ID'] = 'your_access_key_id'
    os.environ['AWS_KEY'] = 'your_secret_access_key'
    os.environ['BUCKET_NAME'] = 'test_bucket'
    with patch.object(
                src.services.s3_service.client_config_service, 'get_config_for_client',
                return_value=ClientConfig(
                    azure_client_id='test_user',
                    bucket_name=os.getenv('BUCKET_NAME'),
                    azure_display_name='test',
                    file_validators=[]
                )
            ) as mock_config:
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
    checksum = "e27c8214be8b7cf5bccc7c08247e3cb0c1514a48ee1f63197fe4ef3ef51d7e6f"
    metadata = {'key1': 'value1'}

    # Act
    s3_service.upload_file_obj(file, filename, checksum, metadata)

    # Assert (Note ChecksumSHA256 is base 64 encoded version of checksum above)
    mock_put_object.assert_called_once_with(
        Bucket=bucket_name,
        ChecksumAlgorithm="SHA256",
        ChecksumSHA256="4nyCFL6LfPW8zHwIJH48sMFRSkjuH2MZf+TvPvUdfm8=",
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
    filename = 'test_file'
    checksum = "e27c8214be8b7cf5bccc7c08247e3cb0c1514a48ee1f63197fe4ef3ef51d7e6f"
    metadata = {'key1': 'value1'}

    # Act and Assert
    with pytest.raises(ClientError) as ex:
        s3_service.upload_file_obj(file, filename, checksum, metadata)

    assert ex.value.response['Error']['Code'] == 'NoSuchBucket'
    assert str(ex.value) == (
        'An error occurred (NoSuchBucket) when calling the PutObject operation: '
        'The specified bucket does not exist'
    )


def test_upload_file_obj_fails_when_checksum_is_wrong(s3_service, mocker):
    """
    Note this is more of a demonstration that an error message is expected when checksum comparison fails.
    There is not actual checksum comparison here. Comparison is performed by an AWS service when used for real.
    """
    # Arrange
    error_message = ("ClientError uploading file to S3: An error occurred (BadDigest) when calling "
                     "the PutObject operation (reached max retries: 4): The SHA256 you specified did "
                     "not match the calculated checksum.")
    error_response = {'Error': {'Code': 'ClientError', 'Message': error_message}}

    mocker.patch.object(
        s3_service.s3_client,
        'put_object',
        side_effect=ClientError(error_response=error_response, operation_name='PutObject')
    )

    file = BytesIO(b"Test data")
    filename = 'test_file'
    # This checksum is not right for the file content (final character shoudl be "f")
    # Although we're not actually doing a true checksum comparison here, so the value doesn't really matter.
    checksum = "e27c8214be8b7cf5bccc7c08247e3cb0c1514a48ee1f63197fe4ef3ef51d7e6e"
    metadata = {'key1': 'value1'}

    # Act and Assert
    with pytest.raises(ClientError) as ex:
        s3_service.upload_file_obj(file, filename, checksum, metadata)

    assert ex.value.response['Error']['Code'] == 'ClientError'
    assert str(ex.value) == 'An error occurred (ClientError) when calling the PutObject operation: ' + error_message


def test_list_object_versions_success(s3_service, mocker):
    mock_list_versions = mocker.patch.object(
        s3_service.s3_client,
        'list_object_versions',
        return_value={'Versions': [{'VersionId': 'v1'}, {'VersionId': 'v2'}]}
    )

    versions = s3_service.list_object_versions('test_file.md')

    assert versions == [{'VersionId': 'v1'}, {'VersionId': 'v2'}]
    mock_list_versions.assert_called_once_with(
        Bucket=s3_service.client_config.bucket_name,
        Prefix='test_file.md'
    )


def test_delete_object_version_success(s3_service, mocker):
    mock_delete = mocker.patch.object(s3_service.s3_client, 'delete_object')
    filename = 'test_file.md'
    version_id = 'v1'

    s3_service.delete_object_version(filename, version_id)

    mock_delete.assert_called_once_with(
        Bucket=s3_service.client_config.bucket_name,
        Key=filename,
        VersionId=version_id
    )


def test_delete_object_version_not_found(s3_service, mocker):
    mocker.patch.object(
        s3_service.s3_client,
        'delete_object',
        side_effect=ClientError(
            error_response={"Error": {"Code": "NoSuchKey", "Message": "Not Found"}},
            operation_name='DeleteObject'
        )
    )

    with pytest.raises(FileNotFoundError):
        s3_service.delete_object_version('missing_file.md', 'v1')


def test_delete_object_version_unexpected_error(s3_service, mocker):
    mocker.patch.object(
        s3_service.s3_client,
        'delete_object',
        side_effect=RuntimeError("Unexpected failure")
    )

    with pytest.raises(RuntimeError) as exc_info:
        s3_service.delete_object_version('test_file.md', 'v1')

    assert "unexpected failure" in str(exc_info.value).lower()


@patch('src.services.s3_service.S3Service.get_s3_client')
def test_status_reporter_success(mock_client, mocker):
    # Success is counter-intuitive due to the way the check is implemented:
    # If a 404 or 403 exception is raised, that's shown the service is alive.
    mock_client.side_effect = ClientError(
        error_response={"Error": {"Code": "404", "Message": "Not Found"}},
        operation_name='HeadBucket'
    )

    so = S3ServiceStatusReporter.get_status()

    mock_client.assert_called()
    assert so.has_failures() is False


@patch('src.services.s3_service.S3Service.get_s3_client')
def test_status_reporter_failure(mock_client, mocker):
    # Success is counter-intuitive due to the way the check is implemented:
    # If a 404 or 403 exception is raised, that's shown the service is alive.
    mock_client.side_effect = ClientError(
        error_response={"Error": {"Code": "400", "Message": "Unable to connect"}},
        operation_name='HeadBucket'
    )

    so = S3ServiceStatusReporter.get_status()

    mock_client.assert_called()
    assert so.has_failures()
