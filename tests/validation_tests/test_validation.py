import pytest

from unittest.mock import patch
from src.validation.validator import validate_request


@pytest.mark.asyncio
async def test_expected_fail_for_no_content_length_header(get_default_mock_file):
    test_header = {}

    result = await validate_request(test_header, get_default_mock_file)
    assert result.status_code == 411 and result.message == ["content-length header not found"]


@pytest.mark.asyncio
async def test_expected_fail_for_no_file_received():
    test_file = None

    test_header = {'content-length': 1}

    result = await validate_request(test_header, test_file)
    assert result.status_code == 400 and result.message == ["File is required"]


@pytest.mark.asyncio
@patch("src.validation.validator.virus_check")
@pytest.mark.parametrize("filesize,content_length", [(0, 1), (2, 3)])
async def test_expected_success_for_content_length_bigger_than_file_size(virus_check, filesize, content_length,
                                                                         get_default_mock_file):
    get_default_mock_file.size = filesize

    virus_check.return_value = ["OK"], 200

    test_header = {'content-length': content_length}

    result = await validate_request(test_header, get_default_mock_file)

    assert result.status_code == 200 and result.message == []


@pytest.mark.asyncio
@patch("src.validation.validator.virus_check")
@pytest.mark.parametrize("av_msg,status_code,expected_msg", [(["Found"], 400, ["Virus Found"]), (["Ok"], 200, [])])
async def test_expected_failure_for_virus_found(virus_check, av_msg, status_code, expected_msg, get_default_mock_file):
    virus_check.return_value = av_msg, status_code

    test_header = {'content-length': 1235}

    result = await validate_request(test_header, get_default_mock_file)
    assert result.status_code == status_code and result.message == expected_msg
