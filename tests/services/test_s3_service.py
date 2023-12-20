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

    # Not sure if the below is the correct way to go about this, happy to discuss and change. I mostly just Googled the error message below to find a solution and a way around this.
    # When running 'pytest' without the following lines error_response and the operation_name I get an error saying:
    # TypeError: __init__() missing 2 required positional arguments: 'error_response' and 'operation_name'

    # Previous code when running 'pytest' won't pass
    # s3_client_mock.upload_fileobj.side_effect = ClientError

    # Current code when running 'pytest' test will pass
    s3_client_mock.upload_fileobj.side_effect = ClientError(
        error_response={"Error": {"Code": "SomeErrorCode", "Message": "Error message"}},
        operation_name="put_object"
    )
    boto3Mock.client.return_value = s3_client_mock
    #action
    response = save(get_file, 'ss-poc-test.txt')
    #assert
    assert response == False

# When mocking and you want to force an exception
# You dont use .return_value, you use .side_effect