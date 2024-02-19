import inspect
import io

from fastapi import Header, UploadFile
from models.validation_response import ValidationResponse
from services.av_check_service import virus_check


async def validate_request(headers: Header, file: UploadFile):
    messages = []
    status_code = None
    validator_sequence = [content_length_is_present,
                          content_expected_fail_for_no_file_received,
                          content_length_is_more_than_file_size,
                          file_size_is_below_maximum]
                          check_antivirus]

    for validator in validator_sequence:
        if inspect.iscoroutinefunction(validator):
            code, message =  await validator(headers, file)
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


def content_length_is_more_than_file_size(headers: Header, file: UploadFile):
    content_length = headers.get('content-length')
    if content_length is not None and file is not None and int(content_length) > file.size:
        return 200, ""
    else:
        return 400, "Content length does not exceed file size or required parameters are missing"


def file_size_is_below_maximum(headers: Header, file: UploadFile):
    if file is not None and file.size <= 2000000:
        return 200, ""
    else:
        return 413, "File size suspiciously large (over 2000000 bytes)"


def content_expected_fail_for_no_file_received(headers: Header, file: UploadFile):
    if file is None:
        return 400, "No file received"
    else:
        return 200, ""

def file_has_right_extension(headers: Header, file: UploadFile):
    fileTypes = ['.pdf', '.doc', '.docx', '.pdf']
    for fileType in fileTypes:
        if file.filename.endswith(fileType):
            return 200
    return 415, "File extension is not PDF, DOC or TXT"

def file_has_right_content_type(headers: Header, file: UploadFile):
    if file.content_type == "application/pdf":
        return 200, ""
    return 415, "File is of wrong content type"

async def check_antivirus(headers: Header, file: UploadFile):
    file_content = await file.read()
    response, status = await virus_check(io.BytesIO(file_content))
    if status == 200:
        return 200, ""
    else:
        return 400, "Virus Found"
