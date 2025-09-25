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
    * 204 if all versions of file found and deleted
    * 404 if file not found
    * 500 if an internal error occurred
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
            # List all versions of the object
            versions = s3_service.list_file_versions(client_config, file_key)

            if len(versions) < 1:
                logger.warning(f"No versions found for {file_key}")
                outcomes[file_key] = 404
                continue

            # Delete each version
            for version in versions:
                version_id = version.get("VersionId")

                if not version_id:
                    logger.error(f"Missing VersionId for file {file_key}")
                    raise RuntimeError(f"Missing VersionId for file {file_key}")

                try:
                    logger.info(f"Attempting to delete version with versionId {version_id}")
                    s3_service.delete_file_version(client_config, file_key, version_id)
                    audit_service.put_item(
                        client_config.azure_display_name, file_key, OperationType.DELETE
                    )
                    logger.info(f"Deleted version {version_id} of file {file_key}")

                except Exception as e:
                    logger.error(f"Failed to delete version {version_id} of {file_key}: {e}")
                    raise e  # Bubble up to outer exception handler

            outcomes[file_key] = 204  # NO CONTENT, all versions deleted successfully

        except FileNotFoundError:
            logger.error(f"File to be deleted {file_key} not found for client {client_config.azure_client_id}")
            outcomes[file_key] = 404  # NOT FOUND
        except Exception as e:
            msg = f"Unexpected error deleting {file_key}: {e.__class__.__name__} - {str(e)}"
            logger.exception(msg)
            outcomes[file_key] = 500  # SERVER ERROR

    return JSONResponse(outcomes, status_code=202)  # ACCEPTED
