from pydantic import Field, AliasChoices, BaseModel


class FileValidatorSpec(BaseModel):
    """
    Requires the named file validator with the specified keyword arguments to pass.
    """
    name: str = Field(validation_alias=AliasChoices('name', 'type'))
    validator_kwargs: dict = Field(validation_alias=AliasChoices('validator_kwargs', 'kwargs'))
