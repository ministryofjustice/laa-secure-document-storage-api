from fastapi.requests import Request
from src.models.client_config import ClientConfig
from src.services import client_config_service
import structlog
logger = structlog.get_logger()


async def client_config_middleware(request: Request) -> ClientConfig:
    """
    Create a new ClientConfig instance with the service_id and client taken from the environment variables,
    raising a 403 error if the user is not authenticated or a config for the user is not found.

    :param request:
    :return: ClientConfig
    :raises HTTPException: 403 if the user is not authenticated or a config for the user is not found
    """
    return client_config_service.get_config_for_client_or_error(request.user.username)
