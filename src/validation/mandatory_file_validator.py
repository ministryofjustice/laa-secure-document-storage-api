import abc
from fastapi import UploadFile
import re
import structlog
from typing import Tuple, Iterable
import io
import inspect
from src.services.clam_av_service import virus_check


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


class HaveFile(MandatoryFileValidator):
    def validate(self, file_object: UploadFile, **kwargs) -> Tuple[int, str]:
        """
        Validate that we have a file object with a filename.
        """
        if file_object is None or not file_object.filename:
            return 400, "File is required"
        else:
            return 200, ""


class NoVirusFoundInFile(MandatoryFileValidator):
    async def validate(self, file_object: UploadFile, **kwargs) -> Tuple[int, str]:
        """
        Runs Clam AV virus scan
        """
        file_content = await file_object.read()
        response, status = await virus_check(io.BytesIO(file_content))
        # Return file reference point to start to make subsequent read possible
        await file_object.seek(0)
        if status == 200:
            return 200, ""
        else:
            return 400, "Virus Found"


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

        Rejects filenames with backslashes (\\), which may indicate directory paths.
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
        disallowed_chars = set(r'\{}[]<>:"|^%`#&$@=;+?,*"~')

        if any(c in disallowed_chars for c in filename):
            return 400, "Filename contains characters that are not allowed"

        return 200, ""


def get_ordered_validators(run_order: Iterable[MandatoryFileValidator] = ()):
    """
    Returns list of all MandatoryFileValidator derived classes with any specified
    in optional run_order parameter at the start of the list. Any unspecified
    validators also included but in default positions (likely same as definition order).
    """
    validators = MandatoryFileValidator.__subclasses__()
    priority_validators = []
    for validator in run_order:
        if validator not in validators:
            raise ValueError(f"Class {validator} must be subclass of MandatoryFileValidator")
        priority_validators.append(validator)
        validators.remove(validator)
    return priority_validators + validators


# Unspecified MandatoryFileValidator validators are also included but in default arbitrary order
validator_classes_in_run_order = get_ordered_validators((HaveFile, NoVirusFoundInFile))


async def run_selected_validators(file_object: UploadFile,
                                  validators: Iterable[MandatoryFileValidator]) -> Tuple[int, str]:
    for validator_class in validators:
        validator = validator_class()
        if inspect.iscoroutinefunction(validator.validate):
            status, detail = await validator.validate(file_object)
        else:
            status, detail = validator.validate(file_object)
        if status != 200:
            return status, detail
    return 200, ""


async def run_mandatory_validators(file_object: UploadFile) -> Tuple[int, str]:
    """
    This runs all mandatory validators, including virus scan. Intended for use
    with file upload to S3.
    """
    result = await run_selected_validators(file_object, validator_classes_in_run_order)
    return result


async def run_virus_check(file_object: UploadFile) -> Tuple[int, str]:
    """
    This only runs the file validators particularly concerned with the virus scan.
    Intended for use with the virus_check_file endpoint.
    """
    result = await run_selected_validators(file_object, [HaveFile, NoVirusFoundInFile])
    return result
