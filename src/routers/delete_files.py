from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.params import Query
from starlette.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.models.audit_record import AuditRecord
from src.services import audit_service, authz_service, s3_service
from src.utils.operation_types import OperationType

router = APIRouter()
logger = structlog.get_logger()


@router.delete('/delete_files')
async def delete_files(
    request: Request,
    file_keys: List[str] = Query(default_factory=list),
    client_config: ClientConfig = Depends(client_config_middleware)
):
    """
    If we don't have any file_keys, return a 400 response.

    Otherwise always return a 200 OK response, with the body containing each of the specified files
    and the status code for the deletion of that file:
    * 204 if all versions of file found and deleted
    * 404 if file not found
    * 500 if an internal error occurred
    """
    error_status = ()
    # Could move this nearer to the raise HTTPException line
    if len(file_keys) == 0:
        error_status = (400, "File key is missing")

    # Check we have permission to delete items from the bucket
    authz_service.enforce_or_error(client_config.azure_client_id, client_config.bucket_name, 'DELETE')

    # Log total number of deletes requested to help trace large requests
    logger.info(f'Deleting {len(file_keys)} file(s)')

    outcomes = {}
    for fi, file_key in enumerate(file_keys):
        error_status = delete_all_file_versions(client_config, file_key)
        outcomes[file_key] = error_status[0] if error_status else 204

        # Could later extend auditing to record delete of each version
        audit_record = AuditRecord(request_id=request.headers["x-request-id"],
                                   filename_position=fi,
                                   service_id=client_config.azure_display_name,
                                   file_id=file_key,
                                   operation_type=OperationType.DELETE
                                   )
        # Temporary filter for only non-error situations as need to update "error" tests to cope
        if not error_status:
            audit_service.put_item(audit_record)

    # Consistent with previous behaviour
    if error_status == (400, "File key is missing"):
        raise HTTPException(status_code=error_status[0], detail=error_status[1])

    return JSONResponse(outcomes, status_code=200)  # OK


def delete_all_file_versions(client_config:  ClientConfig, file_key: str) -> tuple[int, str]:
    error_status = ()
    # List all versions of the object

    try:
        # List all versions of the object
        versions = s3_service.list_file_versions(client_config, file_key)
    # For consistency kept "as before"
    except FileNotFoundError:
        logger.error(f"File to be deleted {file_key} not found for client {client_config.azure_client_id}")
        error_status = (404, "")  # NOT FOUND
    except Exception as e:
        msg = f"Unexpected error deleting {file_key}: {e.__class__.__name__} - {str(e)}"
        logger.exception(msg)
        error_status = (500, "")  # SERVER ERROR
        versions = []

    # Want to avoid overwriting previous error status
    if len(versions) < 1 and not error_status:
        logger.warning(f"No versions found for {file_key}")
        error_status = (404, f"No versions found for {file_key}")
        return error_status

    # Delete each version
    for version in versions:
        version_id = version.get("VersionId")

        if not version_id:
            logger.error(f"Missing VersionId for file {file_key}")
            error_status = (500, f"Missing VersionId for file {file_key}")
            break
        try:
            logger.info(f"Attempting to delete version with versionId {version_id}")
            s3_service.delete_file_version(client_config, file_key, version_id)
            logger.info(f"Deleted version {version_id} of file {file_key}")
        except Exception as e:
            logger.error(f"Failed to delete version {version_id} of {file_key}: {e}")
            error_status = (500, str(e))
    return error_status
