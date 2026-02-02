from io import BytesIO
from unittest.mock import patch

import pytest

from src.models.status_report import Category
from src.services.clam_av_service import ClamAVService, ClamAvServiceStatusReporter


@pytest.mark.asyncio
@patch.object(ClamAVService.get_instance(), '_clamd')
@pytest.mark.parametrize("scan_result,expected_status,expected_message",  [
    ({"stream": ["OK"]}, 200, ""),
    ({"stream": ["FOUND"]}, 400, "Virus Found"),
    ({"stream": ["ERROR"]}, 500, "Error occurred while processing")
])
async def test_check_av_service(mock_clamd, scan_result, expected_status, expected_message):
    # Create BytesIO object simulating a file
    file = BytesIO(b'test content')
    av_service = ClamAVService.get_instance()

    mock_clamd.instream.return_value = scan_result

    status, message = await av_service.check(file)

    assert status == expected_status
    assert message == expected_message


@patch.object(ClamAVService.get_instance(), '_clamd')
def test_status_reporter_success(mock_clamd):
    # ClamAV mock returns without raising an exception, so each check passes
    so = ClamAvServiceStatusReporter.get_status()

    assert so.has_failures() is False


@patch.object(ClamAVService.get_instance(), '_clamd')
def test_status_reporter_failure(mock_clamd):
    mock_clamd.version.side_effect = Exception()

    so = ClamAvServiceStatusReporter.get_status()

    assert so.has_failures()


@patch.object(ClamAVService.get_instance(), '_clamd')
def test_status_reporter_partial_failure(mock_clamd):
    mock_clamd.ping.side_effect = Exception()

    so = ClamAvServiceStatusReporter.get_status()

    assert so.has_failures()
    for check in so.observations:
        if check.phenomenon == 'reachable':
            assert check.category == Category.success
        elif check.phenomenon == 'responding':
            assert check.category == Category.failure
