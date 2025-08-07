import pytest
from src.validation.client_configured_validator import generate_all_filevalidatorspecs
from src.validation.client_configured_validator import get_kwargs_for_filevalidator
from src.validation.file_validator import MaxFileSize, MinFileSize
from src.validation.file_validator import AllowedFileExtensions, DisallowedFileExtensions
from src.validation.file_validator import AllowedMimetypes, DisallowedMimetypes


def test_generate_all_filevalidatorspecs_returns_expected_validators():
    validators = generate_all_filevalidatorspecs()
    names = sorted([v.name for v in validators])
    assert names == ['AllowedFileExtensions', 'AllowedMimetypes', 'DisallowedFileExtensions',
                     'DisallowedMimetypes', 'MaxFileSize', 'MinFileSize']


def test_generate_all_filevalidatorspecs_returns_kwargs():
    """Just checks we're getting the expected number of results and that each validator_kwarg
    is a dict. Avoided chekcing expected kwarg values as would be more fidly and is also covered
    separately below"""
    validators = generate_all_filevalidatorspecs()
    dict_kwargs = [v.validator_kwargs for v in validators if isinstance(v.validator_kwargs, dict)]
    assert len(dict_kwargs) == 6


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
        def validate(a, b, c):
            pass

    kwargs = get_kwargs_for_filevalidator(NonDefaultOnly)
    assert kwargs == {"a": None, "b": None, "c": None}


def test_get_kwargs_for_filevalidator_works_when_only_default_args_present():

    class DefaultOnly:
        def validate(a=1, b=2, c=3):
            pass

    kwargs = get_kwargs_for_filevalidator(DefaultOnly)
    assert kwargs == {"a": 1, "b": 2, "c": 3}


def test_get_kwargs_for_filevalidator_works_when_non_default_and_default_args_present():

    class NonDefaultAndDefault:
        def validate(a, b, c=1, d=2):
            pass

    kwargs = get_kwargs_for_filevalidator(NonDefaultAndDefault)
    assert kwargs == {"a": None, "b": None, "c": 1, "d": 2}


def test_get_kwargs_for_filevalidator_raises_exception_when_validator_method_not_found():

    class BadClass:
        pass

    with pytest.raises(ValueError) as exception_info:
        get_kwargs_for_filevalidator(BadClass)
    assert ".BadClass'> does not have a 'validate' method" in str(exception_info.value)
