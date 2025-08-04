import os
import uuid
from unittest.mock import patch

from fastapi import HTTPException

import src.services.client_config_service
from src.models.status_report import Outcome
from src.services.client_config_service import ClientConfigServiceStatusReporter


def test_unauthenticated_user_raises_exception():
    try:
        config = src.services.client_config_service.get_config_for_client_or_error('anonymous')
        assert False, f"Should have raised an exception, instead got {config}"
    except HTTPException:
        assert True


def test_unauthenticated_user_has_no_config():
    config = src.services.client_config_service.get_config_for_client('anonymous')
    assert config is None


def test_env_store():
    src.services.client_config_service.ClientConfigService.clear_cache()
    assert len(src.services.client_config_service.ClientConfigService._configs) == 0
    test_bucket_name = uuid.uuid4().hex
    os.environ['LOCAL_CONFIG_CLIENT'] = 'test_user'
    os.environ['LOCAL_CONFIG_BUCKET_NAME'] = test_bucket_name
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


def test_config_ttl():
    src.services.client_config_service.ClientConfigService.clear_cache()
    src.services.client_config_service.ClientConfigService._config_default_ttl = 0
    src.services.client_config_service.get_config_for_client('test_user')
    with patch.object(src.services.client_config_service.ClientConfigService, 'load') as mock_load:
        src.services.client_config_service.get_config_for_client('test_user')
        mock_load.assert_called()


@patch('pathlib.Path.rglob')
@patch('os.path.isdir')
def test_status_reporter_success(mock_isdir, mock_pathlib):
    # Config directory exists...
    mock_isdir.return_value = True
    # ...and it has some suitable files
    mock_pathlib.return_value = ['a.json', 'b.json']

    so = ClientConfigServiceStatusReporter.get_status()

    assert so.has_failures() is False


@patch('pathlib.Path.rglob')
@patch('os.path.isdir')
def test_status_reporter_partial_failure(mock_isdir, mock_pathlib):
    # Config directory exists...
    mock_isdir.return_value = True
    # ...but there are no suitable files
    mock_pathlib.return_value = []

    so = ClientConfigServiceStatusReporter.get_status()

    assert so.has_failures()
    for check in so.checks:
        if check.name == 'present':
            assert check.outcome == Outcome.success
        elif check.name == 'populated':
            assert check.outcome == Outcome.failure
