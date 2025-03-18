from pydantic import Field, AliasChoices, BaseModel
from .file_validator_spec import FileValidatorSpec


class ClientConfig(BaseModel):
    """
    Represents the client-specific API configuration, including any optional file processors.
    """
    azure_client_id: str = Field(
        validation_alias=AliasChoices('azure_client_id', 'username')
    )
    azure_display_name: str = Field(
        validation_alias=AliasChoices('azure_display_name', 'requesting_service_id')
    )
    bucket_name: str = Field(
        validation_alias=AliasChoices('bucket_name', 'storage_id')
    )
    file_validators: list[FileValidatorSpec] = Field(
        default_factory=list, validation_alias=AliasChoices('file_validators', 'validators')
    )
