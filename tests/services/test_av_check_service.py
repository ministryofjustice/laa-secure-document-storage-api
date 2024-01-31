from io import BytesIO
from services.av_check_service import AvCheckService

import pytest


@pytest.mark.asyncio
def test_check_file_has_no_virus():
    file = BytesIO(b'some file byte data')
    av_check_service = AvCheckService.get_instance()
    response, status = av_check_service.check(file)
    assert response['message'] == 'file has no virus'
    assert status == 200


@pytest.mark.asyncio
def test_check_file_has_virus():
    file = BytesIO(b'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
    av_check_service = AvCheckService.get_instance()
    response, status = av_check_service.check(file)
    assert response['message'] == 'file has virus'
    assert status == 200
