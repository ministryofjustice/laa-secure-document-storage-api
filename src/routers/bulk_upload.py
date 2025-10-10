import structlog
from fastapi import APIRouter, Depends, UploadFile, Request

from src.middleware.client_config_middleware import client_config_middleware
from src.validation.json_validator import validate_json
from src.models.client_config import ClientConfig
from src.models.file_upload import FileUpload, BulkUploadFileResponse
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
) -> dict[str, BulkUploadFileResponse]:
    """
    Process a list of upload files.
    Always return a 200 success status code, with the body containing result for each filename.

    Response is a dictionary with filenames as keys and second dictionary with details of filename, positions in
    supplied list, checksum and outcomes. This is to enable multiple outcomes when same file included more than once.
    Also includes checksum from the most recent successful save, e.g:

    ```
    {"file1.txt":{"filename":"file1.txt","positions":[0],"checksum":"2248209fd84772fec1e4ddb7dc1c7647751c98abffd85c26c35ca44398dec82f","outcomes":[201]},
     "file2.txt":{"filename":"file2.txt","positions":[1,2],"checksum":"718546961bb3d07169b89bc75c8775b605239bc7189ea0fb92eefc233228804a","outcomes":[201,200]},
     "...":{"filename":"...","positions":[3],"checksum":null,"outcomes":["415: File extension not allowed"]}}
     ```

    This shows:
    - `file1.txt` was included once, so saved with 201 outcome
    - `file2.txt` was included twice, so was saved with 201 and 200 outcomes, and updated with checksum from last save
    - `...` is invalid filename and so receives 415 error response.

    Status code summary for outcomes:
    * 201 if file created
    * 200 if file updated
    * 4xx if various validation fails
    * 500 other unexpected error
    """
    # Not included validation for empty files list because Fast API gives 422 error automatically

    # Create dictionary for storing results for each filename supplied
    results = {f.filename: BulkUploadFileResponse(filename=f.filename, positions=[], outcomes=[], ) for f in files}

    # Log number of files, number of filenames and if duplicate filenames are present
    logger.info(f'Uploading {len(files)} file(s) with {len(results)} unique filenames')
    if len(results) < len(files):
        logger.warning("Duplicate filnames present in the bulk load. Files with same name will be updated.")

    for fi, file in enumerate(files):
        logger.info(f"Attempting to upload file number {fi+1}: {file.filename}")
        results[file.filename].positions.append(fi)

        try:
            # Upload file
            file_result, file_existed = await handle_file_upload_logic(
                request=request,
                file=file,
                body=body,
                client_config=client_config,
                request_type=RequestType.PUT)

            results[file.filename].outcomes.append(200 if file_existed else 201)
            results[file.filename].checksum = file_result.get("checksum")

        except Exception as e:
            msg = f"Error uploading {file.filename}: {e.__class__.__name__} - {str(e)}"
            logger.exception(msg)
            results[file.filename].outcomes.append(str(e))

    return results
