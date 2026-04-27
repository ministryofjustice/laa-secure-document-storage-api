import structlog
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.params import Query

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig

from src.services.s3_service import list_file_versions


router = APIRouter()
logger = structlog.get_logger()


@router.get('/get_file_details')
async def get_file_details(
    request: Request,
    file_key: str = Query(None, min_length=1),
    client_config: ClientConfig = Depends(client_config_middleware),
):
    """
    Get version history for the specified `file_key`.

    Returns the following for each version: `Key`, `VersionId`, `IsLatest`, `Size`, `LastModified`, e.g.
    ```
    {"version_history":[{"Key":"README.md","VersionId":"AZ2.eOOs_UrTIR36qVsTPRm7lJupRZTI","IsLatest":true,"Size":320,"LastModified":"2026-04-24T13:39:38+00:00"},{"Key":"README.md","VersionId":"AZ2.eOOinemjh3PiPMRoTQzUpoxcqMKo","IsLatest":false,"Size":260,"LastModified":"2026-04-23T07:51:26+00:00"}]}
    ```
    """
    error_status = ()
    if not file_key:
        error_status = (400, "File key is missing")

    if not error_status:
        file_versions = list_file_versions(client_config, file_key)
        if file_versions == []:
            error_status = (410, f"No details found for file: {file_key}")

    if error_status:
        raise HTTPException(status_code=error_status[0], detail=error_status[1])

    # Do we want an audit record for this?

    # Extract subset of details for client
    details_for_client = [{key: version.get(key) for key in ("Key", "VersionId", "IsLatest", "Size", "LastModified")}
                          for version in file_versions]

    return {"version_history": details_for_client}
