import abc
import os
from typing import Tuple, List

from fastapi import UploadFile
import structlog

logger = structlog.get_logger()


class ValidatorNotFoundError(Exception):
    pass


class InvalidValidatorArgumentsError(Exception):
    pass


class FileValidator(abc.ABC):
    def validate(self, file_object: UploadFile, **kwargs) -> Tuple[int, str]:
        """
        Runs the validator on the file object and returns a status code and a message.

        :param file_object:
        :param kwargs:
        :return: status_code: int, detail: str
        """
        # This method should be overridden by subclasses, so raise an error if this is called
        raise NotImplementedError()


class MaxFileSize(FileValidator):
    def validate(self, file_object, size: int = 1, **kwargs) -> Tuple[int, str]:
        """
        Validates that the file is at most a certain size.

        :param file_object: Must have a size attribute.
        :param size: Size in bytes
        :param kwargs:
        :return: status_code: int, detail: str
        """
        if size <= 0:
            logger.error("MaxFileSize validator requires a positive size")
            raise InvalidValidatorArgumentsError("MaxFileSize validator requires a positive size")
        if file_object.size is None:
            logger.error(f"File object did not have a size attribute {file_object}")
            return 400, 'File is required'
        if file_object.size > size:
            return 413, 'File size is too large'
        return 200, ""


class MinFileSize(FileValidator):
    def validate(self, file_object, size: int = 1, **kwargs) -> Tuple[int, str]:
        """
        Validates that the file is at least a certain size.

        :param file_object: Must have a size attribute.
        :param size: Size in bytes
        :param kwargs:
        :return: status_code: int, detail: str
        """
        if size <= 0:
            logger.error("MinFileSize validator requires a positive size")
            raise InvalidValidatorArgumentsError("MinFileSize validator requires a positive size")
        if file_object.size is None:
            logger.error(f"File object did not have a size attribute {file_object}")
            return 400, 'File is required'
        if file_object.size < size:
            return 400, 'File size is too small'
        return 200, ""


class AllowedFileExtensions(FileValidator):
    def validate(self, file_object, extensions: List[str] = list, **kwargs) -> Tuple[int, str]:
        """
        Validates that the file extension is in the list of allowed extensions.

        :param file_object:  Must have filename property.
        :param extensions: List of file extensions to allow, lowercase without dot, an empty string for no extension.
        :param kwargs:
        :return: status_code: int, detail: str
        """
        if extensions is list:
            extensions = []
        if len(extensions) == 0:
            logger.error("AllowedFileExtensions validator requires a list of extensions")
            raise InvalidValidatorArgumentsError("AllowedFileExtensions validator requires a list of extensions")
        file_ext = os.path.splitext(file_object.filename)[1].strip('.').lower()
        if file_ext not in extensions:
            logger.error(f"File extension {file_object.filename} not in allowed extensions {extensions}")
            return 415, "File extension not allowed"
        return 200, ""


class DisallowedFileExtensions(FileValidator):
    def validate(self, file_object, extensions: List[str] = list, **kwargs) -> Tuple[int, str]:
        """
        Validates that the file extension is not in the list of disallowed extensions.

        :param file_object:  Must have filename property.
        :param extensions: List of file extensions to allow, lowercase without dot, an empty string for no extension.
        :param kwargs:
        :return: status_code: int, detail: str
        """
        if extensions is list:
            extensions = []
        file_ext = os.path.splitext(file_object.filename)[1].strip('.').lower()
        if file_ext in extensions:
            logger.error(f"File extension {file_object.filename} in disallowed extensions {extensions}")
            return 415, "File extension not allowed"
        return 200, ""


class DisallowedMimetypes(FileValidator):
    def validate(self, file_object, content_types: List[str] = list, **kwargs) -> Tuple[int, str]:
        """
        Validates that the file mimetype is not in the list of disallowed mimetypes.

        Returns 415 if the mimetype is not in the list of allowed mimetypes.
        Returns 400 if the file object does not have a content_type attribute.

        :param file_object: Must have content_type attribute.
        :param content_types: List of mimetypes to disallow.
        :param kwargs:
        :return: status_code: int, detail: str
        """
        if content_types is list:
            content_types = []
        if file_object.content_type is None or file_object.content_type == "":
            logger.error(f"File object did not have a content_type attribute {file_object}")
            return 400, 'File mimetype is required'
        if file_object.content_type.lower() in content_types:
            logger.error(f"File mimetype {file_object.content_type.lower()} in disallowed mimetypes {content_types}")
            return 415, "File mimetype not allowed"
        return 200, ""


class AllowedMimetypes(FileValidator):
    def validate(self, file_object, content_types: List[str] = list, **kwargs) -> Tuple[int, str]:
        """
        Validates that the file mimetype is in the list of allowed mimetypes.

        Returns 415 if the mimetype is not in the list of allowed mimetypes.
        Returns 400 if the file object does not have a content_type attribute.

        :param file_object: Must have content_type attribute.
        :param content_types: List of mimetypes to allow.
        :param kwargs:
        :return: status_code: int, detail: str
        """
        if content_types is list or len(content_types) == 0:
            logger.error("AllowedMimetypes validator requires a list of mimetypes")
            raise InvalidValidatorArgumentsError("AllowedMimetypes validator requires a list of content_types")
        if file_object.content_type is None or file_object.content_type == "":
            logger.error(f"File object did not have a content_type attribute {file_object}")
            return 400, 'File mimetype is required'
        if file_object.content_type.lower() not in content_types:
            logger.error(f"File mimetype {file_object.content_type} not in allowed mimetypes {content_types}")
            return 415, "File mimetype not allowed"
        return 200, ""


class NoDirectoryPathInFilename(FileValidator):
    def validate(self, file_object, **kwargs) -> Tuple[int, str]:
        """
        Validates that the filename does not contain directory path separators.

        Rejects filenames with backslashes (\\) or forward slashes (/), which may indicate directory paths.
        """
        filename = file_object.filename

        if "\\" in filename:
            return 400, "Filename must not contain Windows-style directory path separators"
        return 200, ""


class NoWindowsVolumeInFilename(FileValidator):
    def validate(self, file_object, **kwargs) -> Tuple[int, str]:
        """
        Validates that the filename does not contain Windows volume information.

        Rejects filenames that include a drive letter followed by a colon (e.g., C:\ or D:/).
        """
        filename = file_object.filename

        # Check for patterns like "C:\" or "D:/"
        if len(filename) >= 2 and filename[1] == ":" and filename[0].isalpha(): # Extend for volume info anywhere in filename?
            return 400, "Filename must not contain Windows volume information (e.g., C:\\)"
        return 200, ""


class NoUrlInFilename(FileValidator):
    def validate(self, file_object, **kwargs) -> Tuple[int, str]:
        """
        Validates that the filename does not contain any URLs.

        Rejects filenames that include the string `http`.
        """
        filename = file_object.filename

        if "http" in filename:
            return 400, "Filename must not contain any URLs/web addresses (e.g. http://www.examples.com)"
        return 200, ""


class NoUnacceptableCharactersInFilename(FileValidator):
    def validate(self, file_object, **kwargs) -> Tuple[int, str]:
        """
        Validates that the filename does not contain unacceptable characters (based on AWS S3 docs).

        Rejects control characters, non-printable characters, and symbols known to cause issues in S3 or file systems.
        """
        filename = file_object.filename

        # Reject ASCII control characters (0–31) and DEL (127)
        if any(ord(c) < 32 or ord(c) == 127 for c in filename):
            return 400, "Filename contains control characters"

        # Reject extended ASCII (128–255)
        if any(128 <= ord(c) <= 255 for c in filename):
            return 400, "Filename contains non-printable characters"

        # Characters AWS recommends avoiding
        disallowed_chars = set(r'\/{}[]<>:"|^%`#&$@=;+?,*"~')

        if any(c in disallowed_chars for c in filename):
            return 400, "Filename contains characters that are not allowed"

        return 200, ""



    # class NonZeroFileSize(FileValidator):