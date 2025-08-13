import inspect
from typing import Any, Dict, List, Tuple

import structlog
from fastapi import HTTPException

from src.models.file_validator_spec import FileValidatorSpec
from src.validation.file_validator import FileValidator, ValidatorNotFoundError

logger = structlog.get_logger()


def get_validator(validator_name: str) -> FileValidator:
    """
    Returns a validator instance by name, raising a ValidatorNotFoundError if the validator is not found.

    :param validator_name:
    :return: FileValidator
    """
    validators = {}
    for validator in FileValidator.__subclasses__():
        validators[validator.__name__] = validator

    if validator_name not in validators:
        logger.error(f"Validator {validator_name} not found in {validators}")
        raise ValidatorNotFoundError(f"Validator {validator_name} not found")
    return validators[validator_name]()


def get_validator_validate_docstring(validator: FileValidator) -> tuple[str, str]:
    """
    Extract docstring from validate method and return a "headline" and full text.
    The "headline" is the first line non-empty line, or just "" if all are empty.
    """
    full_text = validator.validate.__doc__
    if full_text is None:
        full_text = ""
    headline = ""
    for headline in full_text.splitlines():
        if headline != "":
            break
    return headline, full_text


def generate_all_filevalidatorspecs() -> List[FileValidatorSpec]:
    # The validators are defined src/validation/file_validator.py
    return [FileValidatorSpec(name=v.__name__,
                              description=get_validator_validate_docstring(v)[0],
                              validator_kwargs=get_kwargs_for_filevalidator(v)
                              )
            for v in FileValidator.__subclasses__()]


def get_kwargs_for_filevalidator(validator: str | FileValidator) -> Dict[str, Any]:
    if isinstance(validator, str):
        validator = get_validator(validator)

    if not hasattr(validator, 'validate'):
        raise ValueError(f"Validator {validator} does not have a 'validate' method")
    # Introspect the 'validate' method to get any expected extra arguments which need to appear in the spec
    validator_args = [a for a in inspect.getfullargspec(validator.validate).args if a not in ('self', 'file_object')]
    validator_defaults = inspect.getfullargspec(validator.validate).defaults

    # If there are no defaults we get None rather than usual tuple. Restoring tuple here.
    if validator_defaults is None:
        validator_defaults = tuple()

    # The returned validator_defaults is a tuple that only includes values for args with defaults (which are always
    # the rightmost args). Padding on left with None values for any any non-default args.
    validator_defaults = (None,) * (len(validator_args) - len(validator_defaults)) + validator_defaults

    validator_kwargs = {}
    for key, value in zip(validator_args, validator_defaults):
        if value is list:
            value = []
        validator_kwargs[key] = value

    return validator_kwargs


async def validate(file_object, validator_specs: List[FileValidatorSpec]) -> Tuple[int, str]:
    """
    Validates the file object against a list of validators, returning (200, None) if all validators pass,
    or the first failing validator's status code and message.

    Validators are executed in the provided order, any exception raised during execution of a validator
    will be logged and returned as an internal error (500, "Internal error handling file")

    :param validator_specs:
    :param file_object:
    :return: status_code: int, detail: str
    """
    if file_object is None or not file_object.filename:
        return 400, "File is required"

    for validator_spec in validator_specs:
        validator = get_validator(validator_spec.name)
        validator_kwargs = validator_spec.validator_kwargs
        try:
            if inspect.iscoroutinefunction(validator.validate):
                status, detail = await validator.validate(file_object, **validator_kwargs)
            else:
                status, detail = validator.validate(file_object, **validator_kwargs)
            if status != 200:
                return status, detail
        except Exception as e:
            logger.error(f"Error while running validator {validator.__class__.__name__}: {e}")
            return 500, "Internal error handling file"
    return 200, ""


async def validate_or_error(file_object, validators: List[FileValidatorSpec]) -> Tuple[int, str]:
    """
    Validates the file object against a list of validators, returning (200, None) if all validators pass,
    or the first failing validator's status code and message.

    :param validators:
    :param file_object:
    :return: status_code: int, detail: str
    """
    status_code, detail = await validate(file_object, validators)
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=detail)
    return 200, ""
