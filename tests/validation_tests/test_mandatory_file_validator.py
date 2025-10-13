import pytest
from src.validation.mandatory_file_validator import (
    NoDirectoryPathInFilename,
    NoWindowsVolumeInFilename,
    NoUrlInFilename,
    NoUnacceptableCharactersInFilename,
)
from .test_file_validator import make_uploadfile


@pytest.mark.parametrize("validator_class, filename, expected_status, expected_detail, assert_msg", [
    (NoDirectoryPathInFilename, "normal.txt", 200, "", "Should allow plain filename"),
    (NoDirectoryPathInFilename, "folder\\file.txt", 400, "Filename must not contain Windows-style directory path separators", "Should reject backslash"),
    (NoDirectoryPathInFilename, "folder\\subfolder/file.txt", 400, "Filename must not contain Windows-style directory path separators", "Should reject mixed separators"),
    (NoWindowsVolumeInFilename, "C:\\file.txt", 400, "Filename must not contain Windows volume information (e.g., C:\\ or D:/)", "Should reject Windows volume"),
    (NoWindowsVolumeInFilename, "file_D:/data.txt", 400, "Filename must not contain Windows volume information (e.g., C:\\ or D:/)", "Should reject volume info anywhere"),
    (NoUrlInFilename, "report.txt", 200, "", "Should allow non-URL filename"),
    (NoUrlInFilename, "http://report.txt", 400, "Filename must not contain URLs or web addresses", "Should reject http://"),
    (NoUrlInFilename, "my-https://www.report.txt", 400, "Filename must not contain URLs or web addresses", "Should reject a URL anywhere in filename"),
    (NoUrlInFilename, "http.txt", 200, "", "Should allow 'http' without URL format"),
    (NoUnacceptableCharactersInFilename, "clean.txt", 200, "", "Should allow clean filename"),
    (NoUnacceptableCharactersInFilename, "clean_name.txt", 200, "", "Should allow underscore"),
    (NoUnacceptableCharactersInFilename, "bad|name.txt", 400, "Filename contains characters that are not allowed", "Should reject pipe character"),
    (NoUnacceptableCharactersInFilename, "bad$name.txt", 400, "Filename contains characters that are not allowed", "Should reject dollar sign"),
    (NoUnacceptableCharactersInFilename, "bad#name.txt", 400, "Filename contains characters that are not allowed", "Should reject hash"),
    (NoUnacceptableCharactersInFilename, "bad<name>.txt", 400, "Filename contains characters that are not allowed", "Should reject angle brackets"),
    (NoUnacceptableCharactersInFilename, "résumé.txt", 400, "Filename contains non-printable characters", "Should reject extended ASCII"),
    (NoUnacceptableCharactersInFilename, "file\x01name.txt", 400, "Filename contains control characters", "Should reject control character")

])
def test_mandatory_file_validators(
    validator_class, filename, expected_status, expected_detail, assert_msg, file_size=None
):
    content = b"x" * file_size if file_size is not None else b"dummy"
    file = make_uploadfile(content=content, name=filename)
    validator = validator_class()
    status, detail = validator.validate(file)
    assert status == expected_status, assert_msg
    assert detail == expected_detail, assert_msg