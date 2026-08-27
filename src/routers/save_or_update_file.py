from typing import Optional

import structlog
from fastapi import APIRouter, UploadFile, Depends, Request
from fastapi.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.validation.json_validator import validate_optional_body_json
from src.models.client_config import ClientConfig
from src.models.file_upload import FileUpload
from src.utils.request_types import RequestType
from src.handlers.file_upload_handler import handle_file_upload_logic


router = APIRouter()
logger = structlog.get_logger()


@router.put("/save_or_update_file")
async def save_or_update_file(
    request: Request,
    file: Optional[UploadFile] = None,
    body: FileUpload = Depends(validate_optional_body_json(FileUpload)),
    client_config: ClientConfig = Depends(client_config_middleware),
):
    """
    Saves the specified file, allowing overwrites of existing files with the same name.
    Files are automatically scanned for viruses, and pre-configured validators are run.

   When file successfully saved, response json includes:

    * `checksum` - sha256 checksum
    * `version_id` - file's version ID if versioning enabled, otherwise get "Versioning not enabled" message
    * `file_already_existed` - Boolean string indicating if this was an existing file.

    See also /save_file for saving a file without allowing overwrites.

    * 200 OK if file replaced an earlier version
    * 201 CREATED if file saved is new

    The following codes may be returned from the automatic virus scan:
    * 411 If file content length is not present
    * 400 If a virus is detected
    * 500 Virus scan gave non-standard result

    Any code other than 200 OK or 201 CREATED means the file has not been saved.
    """
    if file is None:
        file = UploadFile(file=None, filename="")

    response = await handle_file_upload_logic(
        request=request,
        file=file,
        body=body,
        client_config=client_config,
        request_type=RequestType.PUT,
    )
    # Need to use response.model_dump() because JSONResponse is unable to directly serialise the
    # Pydantic model (although would work if we simply returned the model but we'd lose the
    # ability to directly set status code to 200 or 201)
    return JSONResponse(
        status_code=200 if response.file_already_existed else 201,
        content=response.model_dump()
    )
