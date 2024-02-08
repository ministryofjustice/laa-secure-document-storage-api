import pytest
from validation.validator import validate_request
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import UploadFile

@pytest.mark.asyncio
async def test_expected_fail_for_no_content_length_header():
    mocked_file = MagicMock()
    mocked_file.read = MagicMock(return_value=b'test_file_content')
    # Create a mock for UploadFile
    mocked_upload_file = MagicMock(spec=UploadFile)
    mocked_upload_file.filename = 'test.xlsx'
    mocked_upload_file.content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    mocked_upload_file.file = mocked_file  # Assign the file mock to 'file' attribute
    mocked_upload_file.size = 1234
    test_header = {}
    result = await validate_request(test_header, mocked_upload_file)
    assert result.status_code == 411 and result.message == ["content-length header not found"]

@pytest.mark.asyncio
async def test_expected_fail_for_no_file_received():
    test_file = None
    test_header = {'content-length': 1}
    result = await validate_request(test_header, test_file)
    assert result.status_code == 400 and result.message == ["No file received"]


@pytest.mark.asyncio
@pytest.mark.parametrize("filesize,contentlength", [(0, 1), (2, 3)])
async def test_expected_success_for_content_length_bigger_than_file_size(filesize, contentlength):
    test_file = AsyncMock(spec=UploadFile)
    test_file.read.return_value = b'test_file_content'
    test_file.size = filesize
    test_header = {'content-length': contentlength}

    result = await validate_request(test_header, test_file)  # should be async now and awaited

    assert result.status_code == 200 and result.message == []

@pytest.mark.asyncio
async def test_expected_fail_for_file_too_long():
    # test_file = MockUploadFile("test.xlsx", 2000001,
    #                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # test_header = {'content-length': 2000002}
    test_file = MagicMock(spec=UploadFile)
    test_file.size = 2000001
    mocked_file = MagicMock()
    mocked_file.read = MagicMock(return_value=b'test_file_content')
    test_file.file = mocked_file
    test_header = {'content-length': 2000002}
    result = await validate_request(test_header, test_file)
    assert result.status_code == 413 and result.message == ["File size suspiciously large (over 2000000 bytes)"]


@pytest.mark.asyncio
@patch("validation.validator.virus_check")
@pytest.mark.parametrize("filesize,contentlength,av_msg,status_code,expected_msg", [(0, 1,["Found"],400,["Virus Found"]), (2, 3,["Ok"],200,[])])
async def test_expected_failure_for_virus_found(virus_check, filesize, contentlength,av_msg,status_code,expected_msg):
    test_file = AsyncMock(spec=UploadFile)
    test_file.read.return_value = b'test_file_content'
    test_file.size = filesize
    virus_check.return_value = av_msg,status_code
    test_header = {'content-length': contentlength}
    result = await validate_request(test_header, test_file)
    assert result.status_code == status_code and result.message == expected_msg