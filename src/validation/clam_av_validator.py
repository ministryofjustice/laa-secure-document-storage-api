import time
import inspect
import io
import structlog


from fastapi import Header, UploadFile
from src.models.validation_response import ValidationResponse
from src.services.clam_av_service import virus_check

logger = structlog.get_logger()


async def scan_request(headers: Header, file: UploadFile):
    messages = []
    status_code = None
    validator_sequence = [content_length_is_present,
                          check_file_exists,
                          check_antivirus]

    for validator in validator_sequence:
        if inspect.iscoroutinefunction(validator):
            code, message = await validator(headers, file)
        else:
            code, message = validator(headers, file)

        if code != 200:
            messages.append(message)
            if not status_code:
                status_code = code
            break
    if not status_code:
        status_code = 200
    return ValidationResponse(status_code=status_code, message=messages)


def content_length_is_present(headers: Header, file: UploadFile):
    if headers.get('content-length') is not None:
        return 200, ""
    else:
        return 411, "content-length header not found"


def check_file_exists(headers: Header, file: UploadFile):
    if file is None or not file.filename:
        return 400, "File is required"
    else:
        return 200, ""


async def check_antivirus(headers: Header, file: UploadFile):
    start_time = time.time()
    file_content = await file.read()
    read_duration = time.time() - start_time
    response, status = await virus_check(io.BytesIO(file_content))
    # Return file reference point to start to make subsequent read possible
    await file.seek(0)
    full_duration = time.time() - start_time
    logger.info(f"check_antivirus took - file read: {read_duration:10.4f}s, overall {full_duration:10.4f}s")
    if status == 200:
        return 200, ""
    else:
        return 400, "Virus Found"
