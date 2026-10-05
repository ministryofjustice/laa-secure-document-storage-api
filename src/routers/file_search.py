import structlog
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.params import Query

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig

from src.services.s3_service import list_file_search, list_file_versions
from src.services import audit_service
from src.utils.operation_types import OperationType


router = APIRouter()
logger = structlog.get_logger()


@router.get('/file_search')
async def file_search(
    request: Request,
    folder: str = Query(None, min_length=1),
    max_keys: int = 1000,
    continuation_token: str = '',
    client_config: ClientConfig = Depends(client_config_middleware),
):

    file_list = list_file_search(client_config, folder, max_keys, continuation_token)
    return file_list

    return f"File search {folder}"
