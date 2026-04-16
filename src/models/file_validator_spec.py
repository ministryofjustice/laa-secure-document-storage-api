from pydantic import Field, AliasChoices, BaseModel


class ValidatorSpec(BaseModel):
    """
    Originally FileValidatorSpec was defined exactly as here.
    Following introduction FileCollectionValidator, now spit into two subclasses.
    """
    name: str = Field(validation_alias=AliasChoices('name', 'type'))
    description: str | None = None
    validator_kwargs: dict = Field(validation_alias=AliasChoices('validator_kwargs', 'kwargs'))


class FileValidatorSpec(ValidatorSpec):
    """
    Requires the named file validator with the specified keyword arguments to pass.
    The description attribute defaults to None and does not require explicit assignment.
    """
    pass


class FileCollectionValidatorSpec(ValidatorSpec):
    """
    New spec for FileCollection validator.
    Happens to be same as FileValidatorSpec currently but defined as separate class
    to enable independent changes if needed, plus enables clearer type-hinting.
    """
    pass
