from io import BytesIO
from unittest.mock import patch

import pytest
from services.av_check_service import AvCheckService


@pytest.mark.asyncio
@patch.object(AvCheckService.get_instance(), '_clamd')
@pytest.mark.parametrize("scan_result,expected_status,expected_message",  [
    ({"stream": ["OK"]}, 200, "file has no virus"),
    ({"stream": ["FOUND"]}, 400, "file has virus"),
    ({"stream": ["ERROR"]}, 200, "Error occurred while processing")
])
async def test_check_av_service(mock_clamd,scan_result, expected_status, expected_message):
    # Create BytesIO object simulating a file
    file = BytesIO(b'test content')
    av_service = AvCheckService.get_instance()

    mock_clamd.instream.return_value = scan_result

    response, status = await av_service.check(file)

    assert status == expected_status
    assert response.get('message') == expected_message
