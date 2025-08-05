import os
import pathlib
import datetime
from typing import Dict

from fastapi import HTTPException

from src.models.client_config import ClientConfig
import structlog

from src.models.status_report import ServiceObservations, Category
from src.utils.status_reporter import StatusReporter

logger = structlog.get_logger()


class ClientConfigService:
    """
    Service for loading and caching ClientConfigs keyed on username (subject in authentication token).

    To get a ClientConfig, use `ClientConfigService.get_instance(username).config`.
    """
    _configs: Dict = {}
    _config_ttls: Dict = {}
    _config_default_ttl = int(os.getenv('CONFIG_TTL', '300'))
    _config_sources = None

    @staticmethod
    def get_instance(username: str) -> 'ClientConfigService':
        if not isinstance(username, str):
            raise ValueError(f"Invalid type for username: {type(username)}")

        access_time = datetime.datetime.now()
        if username in ClientConfigService._config_ttls and access_time > ClientConfigService._config_ttls[username]:
            if ClientConfigService._config_ttls[username] is not None:
                # Only log the cache clear if there is a value that is being cleared
                logger.info(f"ClientConfig for '{username}' TTL expired, clearing cached config")
            # Clear cache, including any cached 'None' values from a failed auth attempt
            del ClientConfigService._configs[username]
            del ClientConfigService._config_ttls[username]

        if username not in ClientConfigService._configs:
            ClientConfigService._configs[username] = ClientConfigService(username)
            ClientConfigService._config_ttls[username] = datetime.datetime.now() + datetime.timedelta(
                seconds=ClientConfigService._config_default_ttl
            )

        return ClientConfigService._configs[username]

    @staticmethod
    def clear_cache():
        logger.info(f'Clearing {len(ClientConfigService._configs)} cached ClientConfigs')
        ClientConfigService._configs.clear()
        ClientConfigService._config_ttls.clear()

    def __init__(self, username: str):
        self.username = username
        self._config = None

    @property
    def config(self) -> ClientConfig | None:
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> ClientConfig | None:
        # No support for unauthenticated access
        if self.username is None or self.username == 'anonymous':
            return None

        # Effectively cache source list on first use, works more reliably than on startup
        if ClientConfigService._config_sources is None:
            logger.info("Setting config sources from environment variable")
            ClientConfigService._config_sources = os.getenv('CONFIG_SOURCES', 'file').lower().split(',')

        loaded_config = None

        if 'file' in ClientConfigService._config_sources \
                and loaded_config is None:
            logger.info(f"Looking for ClientConfig for '{self.username}' from file")
            loaded_config = self.load_from_file()

        # Only load from environment if other sources are also specified, bit of safety to avoid only trusting the env
        if 'env' in ClientConfigService._config_sources \
                and len(ClientConfigService._config_sources) > 1 \
                and loaded_config is None:
            logger.warning(f"Looking for ClientConfig for '{self.username}' from environment variables")
            loaded_config = self.load_from_env()

        if loaded_config is None:
            logger.error(f"ClientConfig for '{self.username}' not found in {ClientConfigService._config_sources}")

        return loaded_config

    def load_from_env(self) -> ClientConfig | None:
        """
        Attempts to load a ClientConfig from the environment variables, returning None if the variables are not set.

        :return: ClientConfig instance if found and loaded, else None
        """
        loaded_config = None

        env_username = os.getenv('LOCAL_CONFIG_AZURE_CLIENT_ID')
        if env_username != self.username:
            logger.error(
                f"'{self.username}' does not match LOCAL_CONFIG_AZURE_CLIENT_ID user '{env_username}'"
            )
        else:
            logger.info(f"Found LOCAL_CONFIG_AZURE_CLIENT_ID for '{self.username}'")
            try:
                loaded_config = ClientConfig.model_validate({
                    'azure_client_id': env_username,
                    'bucket_name': os.getenv('LOCAL_CONFIG_BUCKET_NAME'),
                    'azure_display_name': os.getenv('LOCAL_CONFIG_AZURE_DISPLAY_NAME', 'local-service-id')
                })
                logger.info(f"Loaded ClientConfig for '{self.username}' from environment variables")
            except Exception as e:
                logger.error(f"Error {e.__class__.__name__} during load of config for '{self.username}': {e}")
                loaded_config = None

        return loaded_config

    def load_from_file(self) -> ClientConfig | None:
        """
        Attempts to find then load a file named {username}.json from the CONFIG_DIR directory, returning None if the
        file does not exist.

        :return: ClientConfig instance if found and loaded, else None
        """
        loaded_config = None
        config_dir = os.getenv('CONFIG_DIR', '/app/clientconfigs')
        try:
            # Config files are JSON files named after the requesting application (client) id.
            # Use a regular expression glob to find all files in any subdirectory of config_dir which are named
            # {username}.json
            candidates = [p for p in pathlib.Path(config_dir).rglob(f"{self.username}.json")]
            # There should be exactly 1 file match: Too many means possibly conflicting configs, none means not found
            if len(candidates) == 1:
                config_path = candidates[0]
                logger.info(f"Loading ClientConfig for '{self.username}' from {config_path}")
                cfg_json = pathlib.Path(config_path).read_text()
                loaded_config = ClientConfig.model_validate_json(cfg_json)
            else:
                logger.error(f"Found {len(candidates)} configs for {self.username} in {os.path.abspath(config_dir)}")
        except Exception as e:
            logger.error(f"Error {e.__class__.__name__} during load of config for '{self.username}': {e}")
            loaded_config = None

        return loaded_config


def get_config_for_client(username: str) -> ClientConfig | None:
    """
    Convenience method to get a ClientConfig instance for a given username.

    :param username:
    :return: ClientConfig
    """
    return ClientConfigService.get_instance(username).config


def get_config_for_client_or_error(username: str) -> ClientConfig:
    """
    Convenience method to get a ClientConfig instance for a given username, raising an exception if the config is not
    found.

    :param username:
    :return: ClientConfig
    """
    config = get_config_for_client(username)
    if config is None:
        logger.error(f"ClientConfig for '{username}' not found")
        raise HTTPException(status_code=403, detail='Forbidden')
    return config


class ClientConfigServiceStatusReporter(StatusReporter):

    @classmethod
    def get_status(cls) -> ServiceObservations:
        """
        Present if configured directory exists.
        Populated if configured directory has contents.
        """
        checks = ServiceObservations(label='configuration')
        present, populated = checks.add_checks('present', 'populated')
        try:
            config_dir = os.getenv('CONFIG_DIR', '/app/clientconfigs')
            if os.path.isdir(config_dir):
                present.category = Category.success
                # Check we actually have some json files
                candidates = [p for p in pathlib.Path(config_dir).rglob("*.json")]
                if len(candidates) > 0:
                    populated.category = Category.success
        except Exception as e:
            logger.error(f'Status check {cls.label} failed: {e.__class__.__name__} {e}')
        return checks
