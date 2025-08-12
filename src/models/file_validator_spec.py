from pydantic import Field, AliasChoices, BaseModel


class FileValidatorSpec(BaseModel):
    """
    Requires the named file validator with the specified keyword arguments to pass.
    The description attribute defaults to None and does not require explicit assignment.
    """
    name: str = Field(validation_alias=AliasChoices('name', 'type'))
    description: str | None = None
    validator_kwargs: dict = Field(validation_alias=AliasChoices('validator_kwargs', 'kwargs'))
