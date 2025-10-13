import abc
from fastapi import UploadFile
import re
import structlog
from typing import Tuple

logger = structlog.get_logger()
    

class MandatoryFileValidator(abc.ABC):
    """Base class for validators that always run and are not client-configurable."""
    def validate(self, file_object: UploadFile) -> Tuple[int, str]:
        """
        Runs the validator on the file object and returns a status code and a message.

        :param file_object:
        :return: status_code: int, detail: str
        """
        # This method should be overridden by subclasses, so raise an error if this is called
        raise NotImplementedError()
    

class NoUrlInFilename(MandatoryFileValidator):
    def validate(self, file_object, **kwargs) -> Tuple[int, str]:
        """
        Validates that the filename does not contain any URLs.

        Rejects filenames that include common URL patterns such as http://, https://, or www.
        """
        filename = file_object.filename.lower()

        # Match common URL patterns
        url_patterns = [
            r"http://",
            r"https://",
            r"www."
        ]

        if any(re.search(pattern, filename) for pattern in url_patterns):
            return 400, "Filename must not contain URLs or web addresses"
        return 200, ""


class NoDirectoryPathInFilename(MandatoryFileValidator):
    def validate(self, file_object, **kwargs) -> Tuple[int, str]:
        """
        Validates that the filename does not contain directory path separators.

        Rejects filenames with backslashes (\\) or forward slashes (/), which may indicate directory paths.
        """
        filename = file_object.filename

        if "\\" in filename:
            return 400, "Filename must not contain Windows-style directory path separators"
        return 200, ""


class NoWindowsVolumeInFilename(MandatoryFileValidator):
    def validate(self, file_object, **kwargs) -> Tuple[int, str]:
        """
        Validates that the filename does not contain Windows volume information (e.g., C:\\ or D:/).

        Rejects any substring matching a drive letter followed by a colon and slash or backslash.
        """
        filename = file_object.filename

        # Regex matches patterns like C:\ or D:/ anywhere in the filename
        if re.search(r"[A-Za-z]:[\\/]", filename):
            return 400, "Filename must not contain Windows volume information (e.g., C:\\ or D:/)"
        return 200, ""


class NoUnacceptableCharactersInFilename(MandatoryFileValidator):
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


def run_mandatory_validators(file_object):
    for validator_class in MandatoryFileValidator.__subclasses__():
        validator = validator_class()
        status, detail = validator.validate(file_object)
        if status != 200:
            return status, detail
    return 200, ""