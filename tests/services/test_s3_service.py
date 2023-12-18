from services.s3_service import save
from unittest.mock import patch, Mock

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


# When mocking and you want to force an exception
# You dont use .return_value, you use .side_effect