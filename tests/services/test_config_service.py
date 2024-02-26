import os
import pytest
from unittest.mock import MagicMock, patch
from models.config.file_types_config import AcceptedFileTypes
from services.config_service import DynamoDBService, get_accepted_file_type_config


@pytest.mark.asyncio
@patch.object(DynamoDBService.get_instance(), '_config')
@patch.object(DynamoDBService.get_instance(), '_dynamodb')
@pytest.mark.parametrize("db_response,expected_result", [
    (
            {"Item": {"acceptedExtensions": ["png"], "acceptedContentTypes": ["image/png"]}},
            AcceptedFileTypes(acceptedExtensions=["png"], acceptedContentTypes=["image/png"])
    )
])
async def test_read_config_item_exists(mocked_dynamodb, mocked_config, db_response, expected_result):
    os.environ["IS_LOCAL"] = "True"

    mocked_dynamodb.Table.return_value = mocked_config
    mocked_config.get_item.return_value = db_response

    result = await get_accepted_file_type_config('1234')

    assert result.acceptedExtensions == expected_result.acceptedExtensions
    assert result.acceptedContentTypes == expected_result.acceptedContentTypes

    mocked_config.get_item.assert_called_once_with(Key={'service_id': '1234'})
