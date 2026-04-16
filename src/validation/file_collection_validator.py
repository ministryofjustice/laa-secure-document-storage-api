import abc
from typing import Iterable
from fastapi import UploadFile

"""
These validators concern collections of files, not individual files.
Created for use with bulk_upload endpoint.
"""


class FileCollectionValidator(abc.ABC):
    # Boolean below used to specify expected run behaviour when validator has "fail" result,
    # i.e. if there is a sequence of validators, whether to proceed to the next validator
    # or to end the sequence.
    continue_to_next_validator_on_fail = False

    def validate(self, files: Iterable[UploadFile], **kwargs) -> tuple[int, str]:
        # Could change files parameter to also accept Iterable[str] to enable support
        # for delete files endpoint which takes list of filenames.
        """
        Runs the validator on collection of file objects and returns a status code and a message.

        :param file_object:
        :param kwargs:
        :return: status_code: int, detail: str
        """
        # This method should be overridden by subclasses, so raise an error if this is called
        raise NotImplementedError()


class MaxFileCount(FileCollectionValidator):
    def validate(self, files: Iterable[UploadFile], max_count: int, **kwargs) -> tuple[int, str]:
        """
        Validates that the number of files submitted does not exceed the specified max_count
        value. On success returns status code 200 and empty message. On failure returns
        status code 422 and message with details.

        Parameters:
            files (Iterable[UploadFile]): collection of files
            max_count (int): maximum number of files allowed

        Returns:
            status code (int), message (str)
        """
        # Convert to list because some iterables don't have length (e.g. generators)
        count = len(list(files))
        if count > max_count:
            return 422, f"Too many files. {count} submitted but maximum is {max_count}."
        return 200, ""


class MinFileCount(FileCollectionValidator):
    def validate(self, files: Iterable[UploadFile], min_count: int, **kwargs) -> tuple[int, str]:
        """
        Validates that the number of files submitted is at least the specified min_count
        value. On success returns status code 200 and empty message. On failure returns
        status code 422 and message with details.

        Parameters:
            files (Iterable[UploadFile]): collection of files
            min_count (int): maximum number of files allowed

        Returns:
            status code (int), message (str)
        """
        # Convert to list because some iterables don't have length (e.g. generators)
        count = len(list(files))
        if count < min_count:
            return 422, f"Too few files. {count} submitted but minimum is {min_count}."
        return 200, ""


class MaxCombinedFileSize(FileCollectionValidator):
    def validate(self, files: Iterable[UploadFile], max_combined_size: int, **kwargs) -> tuple[int, str]:
        """
        Validates that the total combined file size does not exceed the specified max_combined_size value
        (bytes). On success returns status code 200 and empty message. On failure returns
        status code 422 and message with details.

        Parameters:
            files (Iterable[UploadFile]): collection of files
            max_combined_size (int): maximum combined file size in bytes

        Returns:
            status code (int), message (str)
        """
        total_size = sum(f.size for f in files)
        if total_size > max_combined_size:
            return 422, f"Combined file size {total_size} B exceeds limit of {max_combined_size} B."
        return 200, ""
