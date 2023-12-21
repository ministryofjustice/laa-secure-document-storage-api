from fastapi.testclient import TestClient
from services.s3_service import save
from unittest.mock import patch, Mock
from botocore.exceptions import ClientError

@patch("services.s3_service.boto3")
def test_save_success_responds_with_true(boto3Mock, get_file):
    #assign
    s3_client_mock = Mock()
    s3_client_mock.upload_fileobj.return_value = True

    boto3Mock.client.return_value = s3_client_mock
    #action
    response = save(get_file, 'ss-poc-test.txt')
    #assert
    assert response == True

@patch("services.s3_service.boto3")
def test_save_failure_responds_with_false(boto3Mock, get_file):
    #assign
    s3_client_mock = Mock()
    s3_client_mock.upload_fileobj.side_effect = ClientError(
        error_response={"Error": {"Code": "SomeErrorCode", "Message": "Error message"}},
        operation_name="put_object"
    )
    boto3Mock.client.return_value = s3_client_mock
    #action
    response = save(get_file, 'ss-poc-test.txt')
    #assert
    assert response == False