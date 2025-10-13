import structlog
from fastapi import APIRouter, Depends, UploadFile, Request, HTTPException

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
    Process a list of upload files. If the same filename is included more than once, it will be
    updated when second and subsequent instances are reached.

    The response status code just indicates success/failure in the ability to process the supplied
    files, not the sucess of each file operation, and should always be 200 unless there is an
    unexpected error.

    Results for individual files are recorded in the response json which caters for
    multiple files and also having the same filename included more than once in the load.
    This includes the `filename`, the `postitions` of the filename in the supplied file list,
    the `checksum` of the latest successful file operation concerning the filename, `outcomes`
    with `status_code` and `detail` for each file operation, e.g. as below:

    ```
    {'file1.txt': {'filename': 'file1.txt',
    'positions': [0],
    'outcomes': [{'status_code': 201, 'detail': 'saved'}],
    'checksum': '2248209fd84772fec1e4ddb7dc1c7647751c98abffd85c26c35ca44398dec82f'},
    'file2.txt': {'filename': 'file2.txt',
    'positions': [1, 2],
    'outcomes': [{'status_code': 201, 'detail': 'saved'},
    {'status_code': 200, 'detail': 'updated'}],
    'checksum': '2248209fd84772fec1e4ddb7dc1c7647751c98abffd85c26c35ca44398dec82f'},
    '...': {'filename': '...',
    'positions': [3],
    'outcomes': [{'status_code': 415, 'detail': 'File extension not allowed'}],
    'checksum': null}}
    ```

    This shows:
    - `file1.txt` was included once, so saved with a single 201 outcome
    - `file2.txt` was included twice, so was saved with 201 and then updated with a 200 outcomes.
        Checksum is from the second save.
    - `...` is invalid filename and so received 415 error response and null checksum.

    Status code summary for outcomes:
    * 201 file created
    * 200 file updated
    * 4xx various validation failures
    * 500 unexpected error
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

            outcome = {"status_code": 200, "detail": "updated"} if file_existed \
                else {"status_code": 201, "detail": "saved"}

            results[file.filename].checksum = file_result.get("checksum")

        except HTTPException as httpe:
            msg = f"HTTP error uploading {file.filename}: {httpe.__class__.__name__} - {httpe}"
            logger.exception(msg)
            outcome = {"status_code": httpe.status_code, "detail": httpe.detail}

        except Exception as e:
            msg = f"Unexpected error uploading {file.filename}: {e.__class__.__name__} - {e}"
            logger.exception(msg)
            outcome = {"status_code": 500, "detail": str(e)}

        results[file.filename].outcomes.append(outcome)

    return results
