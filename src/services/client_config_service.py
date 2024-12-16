import os
from typing import Dict

import boto3

from src.models.client_config import ClientConfig
from src.models.execeptions.config_for_user_not_found import ConfigForUserNotFoundError
import structlog
logger = structlog.get_logger()


class ClientConfigService:
    """
    Service for loading and caching ClientConfigs keyed on username (subject in authentication token).

    To get a ClientConfig, use `ClientConfigService.get_instance(username).config`.
    """
    _configs: Dict = {}

    @staticmethod
    def get_instance(username: str) -> 'ClientConfigService':
        if not isinstance(username, str):
            raise ValueError(f"Invalid type for username: {type(username)}")

        if username not in ClientConfigService._configs:
            ClientConfigService._configs[username] = ClientConfigService(username)

        return ClientConfigService._configs[username]

    @staticmethod
    def clear_cache():
        logger.info(f'Clearing {len(ClientConfigService._configs)} cached ClientConfigs')
        ClientConfigService._configs.clear()

    def __init__(self, username: str):
        self.username = username
        self._config = None

    @property
    def config(self) -> ClientConfig:
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> ClientConfig:
        # No support for unauthenticated access
        if self.username is None or self.username == 'anonymous':
            raise ConfigForUserNotFoundError()

        loaded_config = None
        try:
            dynamodb = self.get_dynamodb()
            table = dynamodb.Table(os.getenv('CONFIG_TABLE'))
            response = table.get_item(Key={'client': self.username})
            if 'Item' in response:
                logger.info(f"Retrieved ClientConfig for '{self.username}'")
                loaded_config = ClientConfig.model_validate(response['Item'])
            else:
                logger.error(f"ClientConfig for '{self.username}' not found")
        except Exception as e:
            logger.error(f"Error {e.__class__.__name__} during load of config for '{self.username}': {e}")
            loaded_config = None

        if loaded_config is None:
            # FIXME: During development, we return a valid config even if the user's config is not found
            logger.warning(f"Using default ClientConfig from environment variables for '{self.username}'")
            loaded_config = ClientConfig(
                client=self.username,
                service_id=os.getenv('SERVICE_ID', 'equiniti-service-id'),
                bucket_name=os.getenv('BUCKET_NAME', 'sds-deadletter')
            )
        return loaded_config

    def get_dynamodb(self) -> boto3.resource:
        if os.getenv('ENV') == 'local':
            logger.info("Using local DynamoDB client to load ClientConfig")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=os.getenv('AWS_REGION'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                endpoint_url=os.getenv('DYNAMODB_ENDPOINT_URL')
            )
        else:
            logger.info("Using production DynamoDB client to load ClientConfig")
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=os.getenv('AWS_REGION')
            )

        return dynamodb


def get_config_for_client(username: str) -> ClientConfig:
    """
    Convenience method to get a ClientConfig instance for a given username.

    :param username:
    :return: ClientConfig
    """
    return ClientConfigService.get_instance(username).config
