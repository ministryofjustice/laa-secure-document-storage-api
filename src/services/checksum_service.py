import hashlib
import structlog
import base64
from fastapi import UploadFile

logger = structlog.get_logger()


def get_file_checksum(file_object: UploadFile, algorithm: str = "sha256") -> tuple[str, str]:
    result = ""
    error_message = ""
    # Ensure stream position is at start before we process the data
    file_object.file.seek(0)
    try:
        digest_object = hashlib.file_digest(file_object.file, algorithm)
    except Exception as error:
        error_message = f"Unexpected error getting {algorithm} checksum from file '{file_object.filename}': {error}"
        logger.error(error_message)
    else:
        result = digest_object.hexdigest()
    # Return stream position to start, so contents remain available
    file_object.file.seek(0)
    return result, error_message


def hex_string_to_base64_encoded_bytes(hexstring: str) -> str:
    """
    Convert string of hexadecimal digits to string of base 64 encoded bytes.
    Note input string must have even number of characters.

    e.g. converts "123abc" to "Ejq8"

    Created because boto3's S3 client's put_object method only accepts checksums in this format.
    """
    as_bytes = bytes.fromhex(hexstring)
    as_64bit = base64.b64encode(as_bytes).decode()
    return as_64bit
