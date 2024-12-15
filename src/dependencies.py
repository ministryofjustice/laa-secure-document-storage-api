from fastapi.requests import Request
from src.models.client_config import ClientConfig
from src.services import client_config_service
import structlog
logger = structlog.get_logger()


async def client_config_dependency(request: Request) -> ClientConfig:
    """
    Create a new ClientConfig instance with the service_id and client taken from the environment variables.

    :param request:
    :return: ClientConfig
    """
    return client_config_service.get_config_for_client(request.user.username)
