import logging
from fastapi import Header, UploadFile
from models.validation_response import ValidationResponse

def validate_request(headers: Header, file: UploadFile):
    messages = []
    status_code = None
    validator_sequence = [content_length_is_present,
                          content_length_is_more_than_file_size,
                          file_size_is_below_maximum]
    
    for validator in validator_sequence:
        code, message = validator(headers, file)
        if code != 200:
            messages.append(message)
            if not status_code:
                status_code = code
    if not status_code:
        status_code = 200    
    return ValidationResponse(status_code=status_code,  message=messages)
            
def content_length_is_present(headers: Header, file: UploadFile):
    if headers.get('content-length') is not None:
        return 200, ""
    else:
        return 411, "content-length header not found"
    
def content_length_is_more_than_file_size(headers: Header, file: UploadFile):
    if int(headers.get('content-length')) > file.size:
        return 200, ""
    else:
        return 400, "Content length does not exceed file size"

def file_size_is_below_maximum(headers: Header, file: UploadFile):
    if file.size <= 2000000:
        return 200, ""
    else:
        return 413, "File size suspiciously large (over 2000000 bytes)"