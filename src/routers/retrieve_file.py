import structlog
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.params import Query

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.models.execeptions.file_not_found import FileNotFoundException
from src.models.audit_record import AuditRecord
from src.services import audit_service, s3_service
from src.utils.operation_types import OperationType

router = APIRouter()
logger = structlog.get_logger()


@router.get('/get_file')
@router.get('/retrieve_file', deprecated=True)
async def retrieve_file(
            request: Request,
            file_key: str = Query(None, min_length=1),
            client_config: ClientConfig = Depends(client_config_middleware),
        ):
    """
    Gets a short-lifetime link to download the file specified in the body of the request.

    Returns 200 OK with JSON {'fileURL': '--link to resource--'}
    """
    error_status = ()
    if not file_key:
        error_status = (400, "File key is missing")

    if not error_status:
        try:
            logger.info("calling retrieve file operation")
            response = s3_service.retrieve_file_url(client_config, file_key)
            if response is None:
                logger.error("Error whilst retrieving file from S3, got None response")
                raise FileNotFoundException(
                    f"File not found for client {client_config.azure_client_id}", file_key
                )
            logger.info(f"file retrieved successfully: {response}")
        except FileNotFoundException as e:
            logger.error(f"File {file_key} not found for client {client_config.azure_client_id}")
            error_status = (404, str(e))
        except Exception as e:
            logger.error(f"Error retrieving file: {e.__class__.__name__} {str(e)}")
            # Generic message to avoid exposing technical details externally
            error_status = (500, "An error occurred while retrieving the file")

    audit_record = AuditRecord(request_id=request.headers["x-request-id"],
                               filename_position=0,
                               service_id=client_config.azure_display_name,
                               file_id=str(file_key),  # str() as file_key can be None if missing
                               operation_type=OperationType.READ,
                               error_details=error_status[1] if error_status else "")

    try:
        audit_service.put_item(audit_record)
    except Exception as e:
        logger.error(f"Error writing to audit table {str(e)}")
        # Potential issue - if there was a FileNotFoundException followed by an exception
        # here, then the "file not found" response is lost. Concatenate error messages?
        error_status = (500, "An error occurred while retrieving the file")

    if error_status:
        raise HTTPException(status_code=error_status[0], detail=error_status[1])

    return {'fileURL': response}
