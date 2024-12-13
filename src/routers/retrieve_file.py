from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Depends
from fastapi.params import Query

from src.dependencies import client_config_dependency
from src.models.client_config import ClientConfig
from src.models.execeptions.file_not_found import FileNotFoundException
from src.services.authz_service import AuthzService
from src.services.s3_service import retrieve_file_url
from src.services.Audit_Service import put_item
from src.utils.operation_types import OperationType

router = APIRouter()
logger = structlog.get_logger()


@router.get('/retrieve_file')
async def retrieve_file(
        file_key: str = Query(None, min_length=1),
        client_config: ClientConfig = Depends(client_config_dependency),
    ):
    if not file_key:
        raise HTTPException(status_code=400, detail="File key is missing")

    AuthzService().enforce_or_error(
        client_config.client, client_config.bucket_name, OperationType.READ.value
    )

    try:
        put_item(client_config.service_id, file_key, OperationType.READ)

        logger.info("calling retrieve file operation")
        response = retrieve_file_url(client_config, file_key)

        logger.info(f"file retrieved successfully: {response}")
        return {'fileURL': response}
    except FileNotFoundException as e:
        logger.error(f"File {file_key} not found for client {client_config.client}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving file: {e.__class__.__name__} {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
