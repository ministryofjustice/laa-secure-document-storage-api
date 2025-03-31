import mimetypes
import uuid
from typing import Dict, List
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

from src.models.client_config import ClientConfig, FileValidatorSpec
from src.validation.client_configured_validator import get_validator, validate
from src.validation.file_validator import InvalidValidatorArgumentsError


def make_uploadfile(content: bytes | None = None, name: str = 'test.txt') -> UploadFile:
    """
    Helper to create an UploadFile object optionally specifying content and filename.

    :param content:
    :param name:
    :return:
    """
    if content is None:
        content = uuid.uuid4().bytes

    file = AsyncMock(spec=UploadFile)
    file.read.return_value = content
    file.size = len(content)
    file.filename = name
    file.content_type = mimetypes.guess_type(name)[0]
    return file


def make_validatorspec(validator_name: str, **kwargs) -> FileValidatorSpec:
    return FileValidatorSpec(name=validator_name, validator_kwargs=kwargs)


def make_config(validator_specs: List[FileValidatorSpec]) -> ClientConfig:
    return ClientConfig(
        azure_client_id="test_user",
        bucket_name="test_bucket",
        azure_display_name="test",
        file_validators=validator_specs
    )


@pytest.mark.parametrize("validator, validator_kwargs, file_object, expected_status, expected_detail, assert_msg", [
    (
        "MaxFileSize", {"size": 5}, make_uploadfile(b"12345"),
        200, "", "File should be just right"
    ),
    (
        "MaxFileSize", {"size": 5}, make_uploadfile(b"123456"),
        413, "File size is too large", "File size exceeds maximum of 5 bytes"
    ),
    (
        "MinFileSize", {"size": 5}, make_uploadfile(b"12345"),
        200, "", "File size exact"
    ),
    (
        "MinFileSize", {"size": 5}, make_uploadfile(b"1234"),
        400, "File size is too small", "File size is less than minimum of 5 bytes"
    ),
    (
        "AllowedFileExtensions", {"extensions": ["txt"]}, make_uploadfile(name="test.txt"),
        200, "", "Filename has allowed extension"
    ),
    (
        "AllowedFileExtensions", {"extensions": ["txt", ]}, make_uploadfile(name="test.TXT"),
        200, "", "Capitalization should not matter in file name"
    ),
    (
        "AllowedFileExtensions", {"extensions": ["txt", ]}, make_uploadfile(name="test.jpg"),
        415, "File extension not allowed", "File with extension not in allowed_extension list"
    ),
    (
        "AllowedMimetypes", {"content_types": ["application/pdf", ]}, make_uploadfile(name="test.exe"),
        415, "File mimetype not allowed", "File with extension not in mimetypes list"
    ),
    (
        "AllowedFileExtensions", {"extensions": ["txt", ]}, make_uploadfile(name="test..txt"),
        200, "", "File with double period extension should be allowed"
    ),
    (
        "AllowedFileExtensions", {"extensions": ["txt", ]}, make_uploadfile(name="test.jpg.txt"),
        200, "", "File with double extension should be allowed if final extension is valid"
    ),
    (
        "AllowedFileExtensions", {"extensions": ["jpg", "txt",]}, make_uploadfile(name="test.txt"),
        200, "", "File has one of the multiple allowed extensions"
    ),
    (
        "AllowedFileExtensions", {"extensions": ["jpg", "txt",]}, make_uploadfile(name="test.txt.jpg"),
        200, "", "File has all of the multiple allowed extensions"
    ),
    (
        "AllowedFileExtensions", {"extensions": ["txt", ""]}, make_uploadfile(name="test"),
        200, "", "File with no extension is allowed"
    ),
])
def test_file_validator(
            validator: str, validator_kwargs: Dict, file_object: UploadFile,
            expected_status: int, expected_detail: str | None,
            assert_msg: str
        ):
    validator = get_validator(validator)
    status, detail = validator.validate(file_object, **validator_kwargs)
    assert status == expected_status, assert_msg
    assert detail == expected_detail, assert_msg


@pytest.mark.asyncio
@pytest.mark.parametrize("validator_config, file_object, expected_status, expected_detail, assert_msg", [
    (
        make_config([make_validatorspec("MaxFileSize", size=5), ]),
        make_uploadfile(b"12345"),
        200, "",
        "File should be just right"
    ),
    (
        make_config([make_validatorspec("MaxFileSize", size=5), ]),
        make_uploadfile(b"123456"),
        413, "File size is too large",
        "File should be too big"
    ),
    (
        make_config([
            make_validatorspec("MaxFileSize", size=5),
            make_validatorspec("MinFileSize", size=1),
            make_validatorspec("AllowedFileExtensions", extensions=["txt", ])
        ]),
        make_uploadfile(content=b"12345", name="test.txt"),
        200, "",
        "Multiple validators, all passing"
    ),
    (
        make_config([
            make_validatorspec("MaxFileSize", size=5),
            make_validatorspec("MinFileSize", size=1),
            make_validatorspec("AllowedFileExtensions", extensions=["txt", ])
        ]),
        make_uploadfile(content=b"123456", name="test.pdf"),
        413, "File size is too large",
        "Failing validator is first in list"
    ),
    (
        make_config([
            make_validatorspec("MaxFileSize", size=50),
            make_validatorspec("MinFileSize", size=1),
            make_validatorspec("AllowedFileExtensions", extensions=["txt", ]),
            make_validatorspec("MinFileSize", size=5),
        ]),
        make_uploadfile(content=b"1234", name="test.txt"),
        400, "File size is too small",
        "Can duplicate validators and use different parameters"
    ),
    (
        make_config([
            make_validatorspec("MaxFileSize", size=5),
            make_validatorspec("AllowedFileExtensions", extensions=["txt", ]),
            make_validatorspec("MinFileSize", size=1),
        ]),
        make_uploadfile(content=b"1234", name="test.pdf"),
        415, "File extension not allowed",
        "Failing validator is in the middle"
    ),
    (
        make_config([
            make_validatorspec("AllowedFileExtensions", extensions=["txt", ]),
            make_validatorspec("DisallowedFileExtensions", extensions=["txt", ]),
        ]),
        make_uploadfile(name="test.txt"),
        415, "File extension not allowed",
        "When allowing and disallowing an extension, the disallow will take priority"
    ),
    (
        make_config([
            make_validatorspec(
                "DisallowedMimetypes",
                content_types=[
                    "application/prs.implied-executable", "application/x-msdownload", "application/x-msdos-program"
                ]
            ),
        ]),
        make_uploadfile(name="test.exe"),
        415, "File mimetype not allowed",
        "Microsoft executable mimetype includes .exe files"
    ),
    (
        make_config([
            make_validatorspec(
                "DisallowedMimetypes",
                content_types=[
                    "application/prs.implied-executable", "application/x-msdownload", "application/x-msdos-program"
                ]
            ),
        ]),
        make_uploadfile(name="test.dll"),
        415, "File mimetype not allowed",
        "Microsoft executable mimetype includes .dll files"
    ),
    (
        make_config([
            make_validatorspec(
                "DisallowedMimetypes",
                content_types=["application/x-sh", "text/x-sh", "application/x-msdownload"]
            ),
        ]),
        make_uploadfile(name="test.sh"),
        415, "File mimetype not allowed",
        "Exclude shell scripts"
    ),
    (
        make_config([
            make_validatorspec(
                "DisallowedMimetypes",
                content_types=[
                    "application/x-sh", "text/x-sh", "application/x-msdownload", "application/x-msdos-program"
                ]
            ),
        ]),
        make_uploadfile(name="test.MISSING"),
        400, "File mimetype is required",
        "Always exclude files with missing mimetype if mimetype is required"
    ),
    (
        make_config([
            make_validatorspec(
                "DisallowedFileExtensions",
                extensions=["", ]
            ),
        ]),
        make_uploadfile(name="no-extension-exe"),
        415, "File extension not allowed",
        "Exclude any files with no extension"
    ),
])
async def test_file_validator_from_config(
            validator_config: ClientConfig, file_object: UploadFile,
            expected_status: int, expected_detail: str | None, assert_msg: str
        ):
    status, detail = await validate(file_object, validator_config.file_validators)
    assert status == expected_status, assert_msg
    assert detail == expected_detail, assert_msg


@pytest.mark.asyncio
@pytest.mark.parametrize("validator, validator_kwargs, file_object, assert_msg", [
    (
        "MinFileSize", {"size": -5}, make_uploadfile(b"12345"),
        "MinFileSize specifying a negative size should raise an error"
    ),
    (
        "MaxFileSize", {"size": -5}, make_uploadfile(b"12345"),
        "MaxFileSize specifying a negative size should raise an error"
    ),
    (
        "AllowedFileExtensions", {}, make_uploadfile(name="test.txt"),
        "AllowedFileExtensions without correctly specifying extensions should raise an error"
    ),
    (
        "AllowedMimetypes", {}, make_uploadfile(name="test.pdf"),
        "AllowedMimetypes without correctly specifying mimetypes should raise an error"
    )
])
async def test_validator_misconfigured(
            validator: str, validator_kwargs: Dict, file_object: UploadFile, assert_msg: str
        ):
    validator = get_validator(validator)
    with pytest.raises(InvalidValidatorArgumentsError):
        validator.validate(file_object, **validator_kwargs)
