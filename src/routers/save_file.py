from typing import Optional

import structlog
from fastapi import APIRouter, UploadFile, Depends, Request
from fastapi.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.models.file_upload import FileUpload
from src.validation.json_validator import validate_json
from src.utils.request_types import RequestType
from src.handlers.file_upload_handler import handle_file_upload_logic


router = APIRouter()
logger = structlog.get_logger()


@router.post("/save_file")
async def save_file(
    request: Request,
    file: Optional[UploadFile] = None,
    body: FileUpload = Depends(validate_json(FileUpload)),
    client_config: ClientConfig = Depends(client_config_middleware),
):
    """
    Saves a new file, ensuring no existing files are overwritten.
    Files are automatically scanned for viruses, and pre-configured validators are run.
    Response json includes sha256 checksum as "checksum" value.
    See also /save_or_update_file for saving a file and allowing overwrites.

    * 201 CREATED on successful save
    * 409 CONFLICT if file already exists

    The following codes may be returned from the automatic virus scan:
    * 411 If file content length is not present
    * 400 If a virus is detected
    * 500 Virus scan gave non-standard result

    Any code other than 201 CREATED means the file has not been saved.
    """
    if file is None:
        file = UploadFile(file=None, filename="")

    response, _ = await handle_file_upload_logic(
        request=request,
        file=file,
        body=body,
        client_config=client_config,
        request_type=RequestType.POST
    )

    return JSONResponse(status_code=201, content=response)
