from pydantic import Field, AliasChoices, BaseModel


class FileValidatorSpec(BaseModel):
    """
    Requires the named file validator with the specified keyword arguments to pass.
    Although description attribute defaults to None, so does not require specific assingment.
    """
    name: str = Field(validation_alias=AliasChoices('name', 'type'))
    description: str | None = None
    validator_kwargs: dict = Field(validation_alias=AliasChoices('validator_kwargs', 'kwargs'))
