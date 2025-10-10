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
    # Ugly formating of line below is to keep flake8 happy
) -> dict:
    """
    Process a list of upload files.
    Always return a 202 ACCEPTED status code, with the body containing each filename and the per-file
    results.

    Response body is structured as a dictionary with filenames as keys and values that are lists of
    outcomes. This is because the same filename could be included more than once, so we need to cater
    for multiple outcomes per filename, e.g.

    {"file1.txt":[201],"file2.txt":[201,200],"...":["415: File extension not allowed"]}

    This shows successful creation of file1.txt, creation and subsequent update of file2.txt, error
    response from invalid filename "...".

    status code summary:
    * 201 if file created
    * 200 if file updated
    * 4xx if various validation fails
    * 500 other unexpected error
    """
    # Not included validation for empty files list because Fast API gives 422 error automatically

    outcomes = {f.filename: [] for f in files}

    # Log number of files, number of filenames and if duplicates are present
    logger.info(f'Uploading {len(files)} file(s) with {len(outcomes)} unique filenames')
    if len(outcomes) < len(files):
        logger.warning("Duplicate filnames present in the bulk load. Files with same name will be updated.")

    for fi, file in enumerate(files):
        logger.info(f"Attempting to upload file number {fi}: {file.filename}")

        try:
            # Upload file
            _, file_existed = await handle_file_upload_logic(
                request=request,
                file=file,
                body=body,
                client_config=client_config,
                request_type=RequestType.PUT)

            outcomes[file.filename].append(200 if file_existed else 201)

        except Exception as e:
            msg = f"Error uploading {file.filename}: {e.__class__.__name__} - {str(e)}"
            logger.exception(msg)
            outcomes[file.filename].append(str(e))

    return JSONResponse(outcomes, status_code=202)
