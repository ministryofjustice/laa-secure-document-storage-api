from unittest.mock import patch

import pytest
from models.config.file_types_config import AcceptedFileTypes
from validation.validator import validate_request


@pytest.mark.asyncio
@patch("validation.validator.get_accepted_file_type_config")
async def test_expected_fail_for_no_content_length_header(get_accepted_file_type_config,get_default_mock_file):
    test_header = {}
    get_accepted_file_type_config.return_value = AcceptedFileTypes(acceptedExtensions=["png", "txt"],
                                                                   acceptedContentTypes=["image/png", "text/plain"])
    result = await validate_request(test_header, get_default_mock_file)
    assert result.status_code == 411 and result.message == ["content-length header not found"]

@pytest.mark.asyncio
@patch("validation.validator.get_accepted_file_type_config")
async def test_expected_fail_for_no_file_received(get_accepted_file_type_config):
    test_file = None

    test_header = {'content-length': 1}
    get_accepted_file_type_config.return_value = AcceptedFileTypes(acceptedExtensions=["png", "txt"],
                                                                   acceptedContentTypes=["image/png", "text/plain"])

    result = await validate_request(test_header, test_file)
    assert result.status_code == 400 and result.message == ["No file received"]

@pytest.mark.asyncio
@patch("validation.validator.get_accepted_file_type_config")
@patch("validation.validator.virus_check")
@pytest.mark.parametrize("filesize,content_length", [(0, 1), (2, 3)])
async def test_expected_success_for_content_length_bigger_than_file_size(virus_check, get_accepted_file_type_config,filesize, content_length, get_default_mock_file):
    get_default_mock_file.size = filesize

    virus_check.return_value = ["OK"], 200

    test_header = {'content-length': content_length}

    get_accepted_file_type_config.return_value = AcceptedFileTypes(acceptedExtensions=["png", "txt"],
                                                                   acceptedContentTypes=["image/png", "text/plain"])

    result = await validate_request(test_header, get_default_mock_file)

    assert result.status_code == 200 and result.message == []

@pytest.mark.asyncio
@patch("validation.validator.get_accepted_file_type_config")
async def test_expected_fail_for_file_too_long(get_accepted_file_type_config,get_default_mock_file):
    get_default_mock_file.size = 2000001

    test_header = {'content-length': 2000002}
    get_accepted_file_type_config.return_value = AcceptedFileTypes(acceptedExtensions=["png", "txt"],
                                                                   acceptedContentTypes=["image/png", "text/plain"])

    result = await validate_request(test_header, get_default_mock_file)
    assert result.status_code == 413 and result.message == ["File size suspiciously large (over 2000000 bytes)"]

@pytest.mark.asyncio
@patch("validation.validator.get_accepted_file_type_config")
@patch("validation.validator.virus_check")
@pytest.mark.parametrize("av_msg,status_code,expected_msg", [(["Found"], 400, ["Virus Found"]), (["Ok"], 200, [])])
async def test_expected_failure_for_virus_found(virus_check,get_accepted_file_type_config, av_msg, status_code, expected_msg, get_default_mock_file):
    virus_check.return_value = av_msg,status_code

    test_header = {'content-length': 1235}
    get_accepted_file_type_config.return_value = AcceptedFileTypes(acceptedExtensions=["png", "txt"],
                                                                   acceptedContentTypes=["image/png", "text/plain"])
    result = await validate_request(test_header, get_default_mock_file)
    assert result.status_code == status_code and result.message == expected_msg

@pytest.mark.asyncio
@patch("validation.validator.get_accepted_file_type_config")
async def test_expected_fail_for_incorrect_extension(get_accepted_file_type_config,get_default_mock_file):
    get_default_mock_file.filename = 'test.invalid'

    test_header = {'content-length': 1235}
    get_accepted_file_type_config.return_value = AcceptedFileTypes(acceptedExtensions=["png", "txt"],
                                                                   acceptedContentTypes=["image/png", "text/plain"])

    result = await validate_request(test_header, get_default_mock_file)

    assert result.status_code == 415 and result.message == ["File extension is not PDF, DOC or TXT"]

@pytest.mark.asyncio
@patch("validation.validator.get_accepted_file_type_config")
async def test_expected_fail_for_incorrect_content_type(get_accepted_file_type_config,get_default_mock_file):
    get_default_mock_file.content_type = 'invalid/type'

    test_header = {'content-length': 1235}
    get_accepted_file_type_config.return_value = AcceptedFileTypes(acceptedExtensions=["png", "txt"],
                                      acceptedContentTypes=["image/png", "text/plain"])

    result = await validate_request(test_header, get_default_mock_file)

    assert result.status_code == 415 and result.message == ["File is of wrong content type"]
