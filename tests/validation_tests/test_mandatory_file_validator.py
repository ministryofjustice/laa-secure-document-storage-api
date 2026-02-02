import pytest
from unittest.mock import patch
from src.validation.mandatory_file_validator import (
    HaveFile,
    NoVirusFoundInFile,
    NoDirectoryPathInFilename,
    NoWindowsVolumeInFilename,
    NoUrlInFilename,
    NoUnacceptableCharactersInFilename,
    get_ordered_validators,
    run_selected_validators,
    run_mandatory_validators,
    run_virus_check
)
from .test_file_validator import make_uploadfile


filename_validator_test_data = [
    (
        NoDirectoryPathInFilename,
        "normal.txt",
        200,
        "",
        "Should allow plain filename"),
    (
        NoDirectoryPathInFilename,
        "folder\\file.txt",
        400,
        "Filename must not contain Windows-style directory path separators",
        "Should reject backslash",
    ),
    (
        NoDirectoryPathInFilename,
        "folder\\subfolder/file.txt",
        400,
        "Filename must not contain Windows-style directory path separators",
        "Should reject mixed separators",
    ),
    (
        NoWindowsVolumeInFilename,
        "C:\\file.txt",
        400,
        "Filename must not contain Windows volume information (e.g., C:\\ or D:/)",
        "Should reject Windows volume",
    ),
    (
        NoWindowsVolumeInFilename,
        "file_D:/data.txt",
        400,
        "Filename must not contain Windows volume information (e.g., C:\\ or D:/)",
        "Should reject volume info anywhere",
    ),
    (NoUrlInFilename, "report.txt", 200, "", "Should allow non-URL filename"),
    (
        NoUrlInFilename,
        "http://report.txt",
        400,
        "Filename must not contain URLs or web addresses",
        "Should reject http://",
    ),
    (
        NoUrlInFilename,
        "my-https://www.report.txt",
        400,
        "Filename must not contain URLs or web addresses",
        "Should reject a URL anywhere in filename",
    ),
    (NoUrlInFilename, "http.txt", 200, "", "Should allow 'http' without URL format"),
    (
        NoUnacceptableCharactersInFilename,
        "clean.txt",
        200,
        "",
        "Should allow clean filename",
    ),
    (
        NoUnacceptableCharactersInFilename,
        "clean_name.txt",
        200,
        "",
        "Should allow underscore",
    ),
    (
        NoUnacceptableCharactersInFilename,
        "bad|name.txt",
        400,
        "Filename contains characters that are not allowed",
        "Should reject pipe character",
    ),
    (
        NoUnacceptableCharactersInFilename,
        "bad$name.txt",
        400,
        "Filename contains characters that are not allowed",
        "Should reject dollar sign",
    ),
    (
        NoUnacceptableCharactersInFilename,
        "bad#name.txt",
        400,
        "Filename contains characters that are not allowed",
        "Should reject hash",
    ),
    (
        NoUnacceptableCharactersInFilename,
        "bad<name>.txt",
        400,
        "Filename contains characters that are not allowed",
        "Should reject angle brackets",
    ),
    (
        NoUnacceptableCharactersInFilename,
        "résumé.txt",
        400,
        "Filename contains non-printable characters",
        "Should reject extended ASCII",
    ),
    (
        NoUnacceptableCharactersInFilename,
        "file\x01name.txt",
        400,
        "Filename contains control characters",
        "Should reject control character",
    ),
]


@pytest.mark.parametrize("validator_class, filename, expected_status, expected_detail, assert_msg",
                         filename_validator_test_data)
def test_individual_mandatory_filename_validators(validator_class, filename, expected_status,
                                                  expected_detail, assert_msg):
    "Test the validators that validate filenames"
    file = make_uploadfile(name=filename, content=b"dummy")
    validator = validator_class()
    status, detail = validator.validate(file)
    assert status == expected_status, assert_msg
    assert detail == expected_detail, assert_msg


def test_have_file_validator_passes_good_file():
    file = file = make_uploadfile(name="goodfile.txt", content=b"dummy")
    validator = HaveFile()
    result = validator.validate(file_object=file)
    assert result == (200, "")


def test_have_file_validator_fails_when_no_file():
    validator = HaveFile()
    result = validator.validate(file_object=None)
    assert result == (400, "File is required")


def test_have_file_validator_fails_when_no_filename():
    file = make_uploadfile(name="", content=b"dummy")
    validator = HaveFile()
    result = validator.validate(file_object=file)
    assert result == (400, "File is required")


@pytest.mark.asyncio
@patch("src.validation.mandatory_file_validator.virus_check", return_value=(200, ""))
async def test_no_virus_found_pass(mock_virus_check):
    file = make_uploadfile(name="goodfile.txt", content=b"dummy")
    validator = NoVirusFoundInFile()
    result = await validator.validate(file_object=file)
    assert result == (200, "")


@pytest.mark.asyncio
@patch("src.validation.mandatory_file_validator.virus_check", return_value=(400, "Virus Found"))
async def test_no_virus_found_fail(mock_virus_check):
    file = make_uploadfile(name="badfile.txt", content=b"dummy")
    validator = NoVirusFoundInFile()
    result = await validator.validate(file_object=file)
    assert result == (400, "Virus Found")


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_return_value", [(418, "Time for tea!"), (500, "SOS"), (500, "Computer says no")])
@patch("src.validation.mandatory_file_validator.virus_check")
async def test_return_value_from_virus_validator_is_same_as_virus_check(mock_virus_check, mock_return_value):
    mock_virus_check.return_value = mock_return_value
    file = make_uploadfile(name="testfile.txt", content=b"dummy")
    validator = NoVirusFoundInFile()
    result = await validator.validate(file_object=file)
    # Result should be same as mock_return_value as validator should forward the response
    assert result == mock_return_value


@pytest.mark.asyncio
@patch("src.validation.mandatory_file_validator.virus_check",
       return_value=(500, 'Virus scan gave non-standard result'))
async def test_no_virus_found_get_processing_error_when_processing_error(mock_virus_check):
    file = make_uploadfile(name="unluckyfile.txt", content=b"dummy")
    validator = NoVirusFoundInFile()
    result = await validator.validate(file_object=file)
    assert result == (500, 'Virus scan gave non-standard result')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename, expected_status, expected_detail, assert_msg",
    [
        (
            "safe_filename.txt",
            200,
            "",
            "Should pass all mandatory validators"
        ),
        (
            "bad|name.txt",
            400,
            "Filename contains characters that are not allowed",
            "Should fail NoUnacceptableCharactersInFilename and stop at first failure"
        ),
        (
            "www.&.com",
            400,
            "Filename must not contain URLs or web addresses",
            "Should fail NoUrlInFilename and stop, despite also containing unacceptable characters"
        ),
    ]
)
@patch("src.validation.mandatory_file_validator.NoVirusFoundInFile.validate", return_value=(200, ""))
async def test_run_mandatory_validators(mock_av_scan, filename, expected_status, expected_detail, assert_msg):
    file = make_uploadfile(name=filename, content=b"dummy")
    status, detail = await run_mandatory_validators(file)
    assert status == expected_status, assert_msg
    assert detail == expected_detail, assert_msg


@pytest.mark.asyncio
@patch("src.validation.mandatory_file_validator.virus_check", return_value=(200, ""))
async def test_run_virus_check_pass(mock_virus_check):
    file = make_uploadfile(name="goodfile.txt", content=b"dummy")
    result = await run_virus_check(file)
    assert result == (200, "")


@pytest.mark.asyncio
@patch("src.validation.mandatory_file_validator.virus_check", return_value=(200, ""))
async def test_run_virus_check_bad_file(mock_virus_check):
    "If no filename or file, virus scan does not take place - get 'File is required' message"
    file = make_uploadfile(name="", content=b"dummy")
    result = await run_virus_check(file)
    assert result == (400, "File is required")


@pytest.mark.asyncio
@patch("src.validation.mandatory_file_validator.virus_check", return_value=(400, "Virus Found"))
async def test_run_virus_check_fail(mock_virus_check):
    file = make_uploadfile(name="badfile.txt", content=b"dummy")
    result = await run_virus_check(file)
    assert result == (400, "Virus Found")


@pytest.mark.asyncio
@patch("src.validation.mandatory_file_validator.virus_check",
       return_value=(500, "Virus scan gave non-standard result"))
async def test_run_virus_check_non_standard_result(mock_virus_check):
    file = make_uploadfile(name="unlucky.txt", content=b"dummy")
    result = await run_virus_check(file)
    assert result == (500, "Virus scan gave non-standard result")


# Validator run-order selection tests


def test_get_ordered_validators_works_with_one_specified_validator():
    # A bit ticky to test as expected default ordering cannot be easily established
    default_order = get_ordered_validators()
    virus_check_first = get_ordered_validators([NoVirusFoundInFile])
    assert virus_check_first[0] == NoVirusFoundInFile
    assert len(default_order) == len(virus_check_first)
    assert set(default_order) == set(virus_check_first)
    assert len(default_order) == len(set(default_order))


def test_get_ordered_validators_works_with_three_specified_validators():
    # A bit ticky to test as expected default ordering cannot be easily established
    priority_validators = [NoVirusFoundInFile, NoUrlInFilename, NoWindowsVolumeInFilename]
    default_order = get_ordered_validators()
    part_ordered = get_ordered_validators(priority_validators)
    assert part_ordered[0] == priority_validators[0]
    assert part_ordered[1] == priority_validators[1]
    assert part_ordered[2] == priority_validators[2]
    assert len(default_order) == len(part_ordered)
    assert set(default_order) == set(part_ordered)
    assert len(default_order) == len(set(default_order))


def test_get_ordered_validators_gives_expected_exception_when_invalid_class_provided():
    class NotAValidator():
        pass
    with pytest.raises(ValueError) as exc_info:
        _ = get_ordered_validators([NotAValidator])
    assert "NotAValidator'> must be subclass of MandatoryFileValidator" in str(exc_info.value)


# Validator selection tests


@pytest.mark.asyncio
async def test_run_selected_validator_with_one_validator():
    file = make_uploadfile(name="goodfile.txt", content=b"dummy")
    # Using "fail" so we can see the returned message is from expected validator. Always hard-coded ""
    # when result is a "pass".
    with patch('src.validation.mandatory_file_validator.HaveFile.validate') as mock_validate:
        mock_validate.return_value = (418, "This is from mock HaveFile")
        result = await run_selected_validators(file, [HaveFile])
    assert result == (418, "This is from mock HaveFile")
    mock_validate.assert_called_once()


@pytest.mark.asyncio
async def test_run_selected_validator_with_some_validators():
    file = make_uploadfile(name="goodfile.txt", content=b"dummy")
    # just to keep patch line-lengths shorter
    path = "src.validation.mandatory_file_validator"
    with (patch(f'{path}.HaveFile.validate', return_value=(200, "")) as mock1,
          patch(f'{path}.NoWindowsVolumeInFilename.validate', return_value=(200, "")) as mock2,
          patch(f'{path}.NoUrlInFilename.validate', return_value=(200, "")) as mock3):
        result = await run_selected_validators(file, [HaveFile,
                                                      NoWindowsVolumeInFilename,
                                                      NoUrlInFilename])
    assert result == (200, "")
    mock1.assert_called_once()
    mock2.assert_called_once()
    mock3.assert_called_once()


@pytest.mark.asyncio
async def test_run_selected_validator_passes_bad_character_in_filename_when_related_validator_absent():
    "This file would fail NoUnacceptableCharactersInFilename, so 'pass' result shows it hasn't run"
    file = make_uploadfile(name="bad|name.txt", content=b"dummy")
    result = await run_selected_validators(file, [HaveFile,
                                                  NoDirectoryPathInFilename,
                                                  NoUrlInFilename])
    assert result == (200, "")


@pytest.mark.asyncio
async def test_run_selected_validator_fails_bad_character_in_filename_when_related_validator_present():
    "Has fail result because filename fails NoUnacceptableCharactersInFilename which is included"
    file = make_uploadfile(name="bad|name.txt", content=b"dummy")
    result = await run_selected_validators(file, [HaveFile,
                                                  NoDirectoryPathInFilename,
                                                  NoUrlInFilename,
                                                  NoUnacceptableCharactersInFilename])
    assert result == (400, "Filename contains characters that are not allowed")
