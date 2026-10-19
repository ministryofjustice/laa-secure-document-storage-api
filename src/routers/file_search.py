import structlog
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.params import Query

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig

from src.services.s3_service import find_files
from src.services import audit_service
from src.utils.operation_types import OperationType
from typing import Optional


router = APIRouter()
logger = structlog.get_logger()


@router.get('/file_search')
async def file_search(
    request: Request,
    folder: Optional[str] = Query(None),
    max_items: int = 1000,
    continuation_token: str = '',
    client_config: ClientConfig = Depends(client_config_middleware),
):
    """
    Search for files.

    A folder may optionally be provided. The folder can be formatted myfolder or myfolder/ but not /myfolder/
    The search is recursive, so if folder is specified any sub-folders will be automatically in scope.
    There is no check that the specified folder exists. If non-existent folder supplied then result is
    just an empty list.

    The maxium number of files returned is 1000 at most but a smaller number can be specified by setting
    an optional max_items value.

    A list of files is returned. If there are more files than the maximum number specified then a continuation
    token will also be returned

    """

    error_status = ()

    if max_items > 1000:
        error_status = (400, "Maximum files to be retrieved must not be greater than 1000")

    if not error_status:
        try:
            file_list = find_files(client_config, folder, max_items, continuation_token)

        except Exception as e:
            error_message = f"Unexpected error during file search: {e.__class__.__name__} - {e}"
            logger.info(error_message)
            error_status = (500, "Unexpected error during file search")

    audit_service.add_record(request=request,
                             filename_position=0,
                             service_id=client_config.azure_display_name,
                             file_id='',
                             search_terms=f"Folder: {folder} Maximum items: {max_items}",
                             operation_type=OperationType.SEARCH,
                             error_status=error_status)

    if error_status:
        raise HTTPException(status_code=error_status[0], detail=error_status[1])

    return file_list
