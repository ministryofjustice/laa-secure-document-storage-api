from unittest.mock import AsyncMock, patch, MagicMock, Mock
from fastapi import UploadFile
import pytest
from src.routers.api_files import saveFile
from src.routers.api_files import Metadata


@pytest.mark.asyncio
@patch('src.routers.api_files.get_s3_service')
async def test_save_file_success(get_s3_service):
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "testfile.txt"
    mock_file.read = AsyncMock(return_value=b'file content')
    mock_s3_client = Mock()
    mock_s3_client.put_object = Mock(return_value={
        'ResponseMetadata': {'HTTPStatusCode': 201}
    })
    get_s3_service.return_value = mock_s3_client()
    response = await saveFile(Metadata(file=mock_file, reference="12345", name="dummy_file"))
    assert response['success'] is True
    assert response['file_name'] == 'dummy_file'