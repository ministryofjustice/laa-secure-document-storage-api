import inspect
import io

from fastapi import Header, UploadFile
from src.models.validation_response import ValidationResponse
from src.services.av_check_service import virus_check


async def validate_request(headers: Header, file: UploadFile):
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
    file_content = await file.read()
    response, status = await virus_check(io.BytesIO(file_content))
    if status == 200:
        return 200, ""
    else:
        return 400, "Virus Found"
