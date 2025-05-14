from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query
from starlette.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.services import audit_service, authz_service, s3_service
from src.utils.operation_types import OperationType

router = APIRouter()
logger = structlog.get_logger()


@router.delete('/delete_files')
async def delete_files(
            file_keys: List[str] = Query(default_factory=list),
            client_config: ClientConfig = Depends(client_config_middleware),
        ):
    """
    Always return a 202 ACCEPTED response, with the body containing each of the specified files and the status code
    for the deletion of that file:
    * 204 if found and deleted
    * 404 if not found
    * 500 if an internal error occurred

    :param file_keys:
    :param client_config:
    :return: 202 ACCEPTED response, with body listing each file name and status code
    """
    if len(file_keys) == 0:
        raise HTTPException(status_code=400, detail="File key is missing")

    # Check we have permission to delete items from the bucket
    authz_service.enforce_or_error(client_config.azure_client_id, client_config.bucket_name, 'DELETE')

    # Log total number of deletes requested to help trace large requests
    logger.info(f'Deleting {len(file_keys)} file(s)')

    outcomes = {}
    for file_key in file_keys:
        # Set default outcome
        outcomes[file_key] = 500  # SERVER ERROR, should always process all files
        try:
            audit_service.put_item(client_config.azure_display_name, file_key, OperationType.DELETE)
            logger.info(f"Calling delete file operation to delete file {file_key}")

            # s3 service will raise exceptions if errors are encountered...
            s3_service.delete_file(client_config, file_key)
            # ...therefore this was a success
            outcomes[file_key] = 204  # NO CONTENT, delete was successful

        except FileNotFoundError:
            logger.error(f"File to be deleted {file_key} not found for client {client_config.azure_client_id}")
            outcomes[file_key] = 404  # NOT FOUND
        except Exception as e:
            logger.error(f"Error deleting file: {e.__class__.__name__} {str(e)}")
            outcomes[file_key] = 500  # SERVER ERROR

    return JSONResponse(outcomes, status_code=202)  # ACCEPTED
