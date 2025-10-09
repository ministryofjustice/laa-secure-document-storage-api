import structlog
from fastapi import APIRouter, Depends, UploadFile, Request
from starlette.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.validation.json_validator import validate_json
from src.models.client_config import ClientConfig
from src.models.file_upload import FileUpload
from src.utils.request_types import RequestType
from src.handlers.file_upload_handler import handle_file_upload_logic

router = APIRouter()
logger = structlog.get_logger()


@router.put("/bulk_upload")
async def bulk_upload(
    request: Request,
    files: list[UploadFile],
    body: FileUpload = Depends(validate_json(FileUpload)),
    client_config: ClientConfig = Depends(client_config_middleware)
    # Horrible formating below is to keep flake8 happy
) -> dict:
    """
    Process a list of upload files.
    Always return a 202 ACCEPTED response, with the body containing each filename and the individual
    status code for the upload of that file:
    * 200 if file created
    * 201 if file updated
    * 4xx if various validations fail
    * 500 if an internal error occurred
    """
    # Not included validation for empty file list because we get 422 error automatically

    # Log total number of uploads requested to help trace large requests
    logger.info(f'Uploading {len(files)} file(s)')

    outcomes = {}
    for file in files:
        logger.info(f"Attempting to upload file: {file.filename}")
        if file.filename in outcomes:
            logger.warning(f"File {file.filename} already loaded during same run.")
        # Set default outcome
        outcomes[file.filename] = 500  # SERVER ERROR, should always process all files
        try:
            # Upload file
            _, file_existed = await handle_file_upload_logic(
                request=request,
                file=file,
                body=body,
                client_config=client_config,
                request_type=RequestType.PUT)

            outcomes[file.filename] = 200 if file_existed else 201

        except Exception as e:
            msg = f"Unexpected error uploading {file.filename}: {e.__class__.__name__} - {str(e)}"
            logger.exception(msg)
            outcomes[file.filename] = str(e)

    return JSONResponse(outcomes, status_code=202)
