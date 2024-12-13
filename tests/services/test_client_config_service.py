import os
import uuid
from unittest.mock import patch

import src.services.client_config_service
from src.models.execeptions.config_for_user_not_found import ConfigForUserNotFoundError


def test_unauthenticated_user_raises_exception():
    try:
        config = src.services.client_config_service.get_config_for_client('anonymous')
        assert False, "Should have raised an exception"
    except ConfigForUserNotFoundError as nfe:
        assert True


def test_bucket_found_in_env():
    # This test will only be valid until configs are loaded from the database
    src.services.client_config_service.ClientConfigService.clear_cache()
    assert len(src.services.client_config_service.ClientConfigService._configs) == 0
    test_bucket_name = uuid.uuid4().hex
    os.environ['BUCKET_NAME'] = test_bucket_name
    config = src.services.client_config_service.get_config_for_client('test_user')
    assert config.bucket_name == test_bucket_name


def test_configs_are_cached():
    src.services.client_config_service.ClientConfigService.clear_cache()
    src.services.client_config_service.get_config_for_client('test_user')
    with patch.object(src.services.client_config_service.ClientConfigService, 'load') as mock_load:
        src.services.client_config_service.get_config_for_client('test_user')
        mock_load.assert_not_called()
        src.services.client_config_service.ClientConfigService.clear_cache()
        src.services.client_config_service.get_config_for_client('test_user')
        mock_load.assert_called_once()
