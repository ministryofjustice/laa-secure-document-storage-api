import structlog
from fastapi import APIRouter, HTTPException, Depends
from fastapi.params import Query

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.models.execeptions.file_not_found import FileNotFoundException
from src.services import audit_service, s3_service
from src.utils.operation_types import OperationType

router = APIRouter()
logger = structlog.get_logger()


@router.get('/get_file')
@router.get('/retrieve_file', deprecated=True)
async def retrieve_file(
            file_key: str = Query(None, min_length=1),
            client_config: ClientConfig = Depends(client_config_middleware),
        ):
    """
    Gets a short-lifetime link to download the file specified in the body of the request.

    Returns 200 OK with JSON {'fileURL': '--link to resource--'}
    """
    if not file_key:
        raise HTTPException(status_code=400, detail="File key is missing")

    try:
        audit_service.put_item(client_config.azure_display_name, file_key, OperationType.READ)

        logger.info("calling retrieve file operation")
        response = s3_service.retrieve_file_url(client_config, file_key)
        if response is None:
            logger.error("Error whilst retrieving file from S3, got None response")
            raise FileNotFoundException(
                f"File not found for client {client_config.azure_client_id}", file_key
            )

        logger.info(f"file retrieved successfully: {response}")
        return {'fileURL': response}
    except FileNotFoundException as e:
        logger.error(f"File {file_key} not found for client {client_config.azure_client_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving file: {e.__class__.__name__} {str(e)}")
        raise HTTPException(status_code=500, detail='An error occurred while retrieving the file')
