from fastapi.requests import Request
from src.models.client_config import ClientConfig
from src.services.client_config_service import get_config_for_client
import structlog
logger = structlog.get_logger()


async def client_config_dependency(request: Request) -> ClientConfig:
    """
    Create a new ClientConfig instance with the service_id and client taken from the environment variables.

    :param request:
    :return: ClientConfig
    """
    return get_config_for_client(request.user.username)
