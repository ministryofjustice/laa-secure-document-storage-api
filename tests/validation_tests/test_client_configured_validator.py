import pytest
from unittest.mock import patch
from fastapi import HTTPException
from src.validation.client_configured_validator import generate_all_filevalidatorspecs
from src.validation.client_configured_validator import get_kwargs_for_filevalidator
from src.validation.client_configured_validator import get_validator_validate_docstring
from src.validation.client_configured_validator import get_status_code_for_response
from src.validation.client_configured_validator import validate_or_error
from src.validation.file_validator import MaxFileSize, MinFileSize
from src.validation.file_validator import AllowedFileExtensions, DisallowedFileExtensions
from src.validation.file_validator import AllowedMimetypes, DisallowedMimetypes

"""
Location of test for functions: validate and get_validator

Tests for the two above functions are in test_file_validator.py rather than here.
Likely for convenience of using functions that create test data there.

Potentially could move them to this file but we have plans to change the way validators
work which might require a larger reorganisation, so leaving as-is for now.
"""


def test_generate_all_filevalidatorspecs_returns_expected_validators():
    validators = generate_all_filevalidatorspecs()
    names = sorted([v.name for v in validators])
    assert names == ['AllowedFileExtensions', 'AllowedMimetypes', 'DisallowedFileExtensions',
                     'DisallowedMimetypes', 'MaxFileSize', 'MinFileSize', 'ScanForSuspiciousContent']


def test_generate_all_filevalidatorspecs_returns_kwargs():
    """Just checks we're getting the expected number of results and that each validator_kwarg
    is a dict. Avoided checking expected kwarg values as would be more fiddly and is also covered
    separately below"""
    validators = generate_all_filevalidatorspecs()
    dict_kwargs = [v.validator_kwargs for v in validators if isinstance(v.validator_kwargs, dict)]
    assert len(dict_kwargs) == 7


@pytest.mark.parametrize("validator_name,expected_result", [("AllowedFileExtensions", {'extensions': []}),
                                                            ("AllowedMimetypes", {'content_types': []}),
                                                            ("DisallowedFileExtensions", {'extensions': []}),
                                                            ("DisallowedMimetypes", {'content_types': []}),
                                                            ("MaxFileSize", {'size': 1}),
                                                            ("MinFileSize", {'size': 1})
                                                            ])
def test_get_kwargs_for_filevalidator_works_with_string_param(validator_name, expected_result):
    kwargs = get_kwargs_for_filevalidator(validator_name)
    assert kwargs == expected_result


@pytest.mark.parametrize("validator,expected_result", [(AllowedFileExtensions, {'extensions': []}),
                                                       (AllowedMimetypes, {'content_types': []}),
                                                       (DisallowedFileExtensions, {'extensions': []}),
                                                       (DisallowedMimetypes, {'content_types': []}),
                                                       (MaxFileSize, {'size': 1}),
                                                       (MinFileSize, {'size': 1})
                                                       ])
def test_get_kwargs_for_filevalidator_works_with_validator_param(validator, expected_result):
    kwargs = get_kwargs_for_filevalidator(validator)
    assert kwargs == expected_result


def test_get_kwargs_for_filevalidator_works_when_no_args():

    class NoArgs:
        @staticmethod
        def validate():
            pass

    kwargs = get_kwargs_for_filevalidator(NoArgs)
    assert kwargs == {}


def test_get_kwargs_for_filevalidator_excludes_self_and_file_object_args():
    """By design, self and file_object args are excluded from the evaluation"""

    class SelfAndFileObjectArgs:
        def validate(self, file_object, a=1):
            pass

    kwargs = get_kwargs_for_filevalidator(SelfAndFileObjectArgs)
    assert kwargs == {"a": 1}


def test_get_kwargs_for_filevalidator_works_when_only_non_default_args_present():

    class NonDefaultOnly:
        def validate(self, a, b, c):
            pass

    kwargs = get_kwargs_for_filevalidator(NonDefaultOnly)
    assert kwargs == {"a": None, "b": None, "c": None}


def test_get_kwargs_for_filevalidator_works_when_only_default_args_present():

    class DefaultOnly:
        def validate(self, a=1, b=2, c=3):
            pass

    kwargs = get_kwargs_for_filevalidator(DefaultOnly)
    assert kwargs == {"a": 1, "b": 2, "c": 3}


def test_get_kwargs_for_filevalidator_works_when_non_default_and_default_args_present():

    class NonDefaultAndDefault:
        def validate(self, a, b, c=1, d=2):
            pass

    kwargs = get_kwargs_for_filevalidator(NonDefaultAndDefault)
    assert kwargs == {"a": None, "b": None, "c": 1, "d": 2}


def test_get_kwargs_for_filevalidator_raises_exception_when_validator_method_not_found():

    class BadClass:
        pass

    with pytest.raises(ValueError) as exception_info:
        get_kwargs_for_filevalidator(BadClass)
    assert ".BadClass'> does not have a 'validate' method" in str(exception_info.value)


def test_get_validator_validate_docstring_multi_line():

    class HasLongDoc:
        def validate(self):
            """This is the first line
            This is the second line
            This is the third line
            """
            pass

    headline, all = get_validator_validate_docstring(HasLongDoc)
    assert headline == "This is the first line"
    assert all == "This is the first line\nThis is the second line\nThis is the third line\n"


def test_get_validator_validate_docstring_multi_line_and_newline_start():

    class HasLongDocNl:
        def validate(self):
            """
            This is the first line
            This is the second line
            This is the third line
            """
            pass

    headline, all = get_validator_validate_docstring(HasLongDocNl)
    assert headline == "This is the first line"
    assert all == "\nThis is the first line\nThis is the second line\nThis is the third line\n"


def test_get_validator_validate_docstring_single_line():

    class HasShortDoc:
        def validate(self):
            "This is the only line"
            pass

    headline, all = get_validator_validate_docstring(HasShortDoc)
    assert headline == all == "This is the only line"


def test_get_validator_validate_docstring_empty_docstring():

    class EmptyDoc:
        def validate(self):
            ""
            pass

    headline, all = get_validator_validate_docstring(EmptyDoc)
    assert headline == all == ""


def test_get_validator_validate_docstring_no_docstring():

    class LacksDoc:
        def validate(self):
            pass

    headline, all = get_validator_validate_docstring(LacksDoc)
    assert headline == all == ""


def test_get_validator_validate_docstring_with_actual_validator():
    """
    Just checking ability to digest a genuine validator.
    Not examining text content to avoid fragility if docstring updated
    (which is not part of code).
    """
    headline, all = get_validator_validate_docstring(MaxFileSize)
    assert len(headline) <= len(all)


@pytest.mark.parametrize("validator_results,expected_result", [
    # Singular pass - same 200 code result
    ([(200, "")], 200),
    # Singular fail - same 415 code result
    ([(415, "Unsupported Media Tripe")], 415),
    # Two fails with different 4xx status codes - 422 result
    ([(415, "Unsupported Media Tripe"), (400, "Bad Repast")], 422),
    # Three fails with one having 500 status code - 500 result
    ([(415, "Unsupported Media Tripe"), (400, "Bad Repast"), (500, "Infernal Server Error")], 500),
    # Three fails, all having 500 status code - 500 result
    ([(500, "Infernal Server Error"), (500, "Infernal Server Error"), (500, "Infernal Server Error")], 500),
    # Three fails, all having 400 status code - 400 result
    ([(400, "Bad Repast"), (400, "Bad Repast"), (400, "Bad Repast")], 400),
    # Three fails, each with different status ocde - 422 result
    ([(400, "Bad Repast"), (417, "Expectation Dashed"), (421, "Misdirected Tourist")], 422)
    ])
def test_get_status_code_from_response(validator_results, expected_result):
    result = get_status_code_for_response(validator_results)
    assert result == expected_result


@pytest.mark.asyncio
async def test_validate_or_error_with_pass():
    # Note these values don't really matter due to patching of validate return value.
    # This test concerns the format of result rather than the validation itself
    file = ""
    validators = []
    with patch("src.validation.client_configured_validator.validate", return_value=[(200, "")]):
        result = await validate_or_error(file, validators)
    assert result == (200, "")


# Note this function raises an HTTPException when there is a "fail" result.
# The expected results here are based on Pytest's ExceptionInfo representation
# of the exception, not HTTPException directly.
@pytest.mark.asyncio
@pytest.mark.parametrize("validate_result,expected_result", [
    # Single failure
    ([(400, 'Size is too small')],
     "400: [(400, 'Size is too small')]"),
    # Two failures with same status codes
    ([(415, 'File mimetype not allowed'), (415, 'File extension not allowed')],
     "415: [(415, 'File mimetype not allowed'), (415, 'File extension not allowed')]"),
    # Two failures with different status codes - gets 422
    ([(400, "Size is too small"), (415, "File extension not allowed")],
     "422: [(400, 'Size is too small'), (415, 'File extension not allowed')]"),
    # 500 error present
    ([(400, "Size is too small"), (500, "Infernal Server Error")],
     "500: [(400, 'Size is too small'), (500, 'Infernal Server Error')]")
    ])
async def test_validate_or_error_with_fail(validate_result, expected_result):
    # Note the fileobject and  validators values  don't really matter due to patching of
    # validate return value. This test concerns the format of result/exception rather
    # than validation itself
    fileobject = ""
    validators = []
    with patch("src.validation.client_configured_validator.validate", return_value=validate_result):
        with pytest.raises(HTTPException) as excinfo:
            _ = await validate_or_error(fileobject, validators)
    assert str(excinfo.value) == expected_result
