from pydantic import Field, AliasChoices, BaseModel


class ClientConfig(BaseModel):
    """
    Represents the client-specific API configuration, primarily the storage options.
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
    file_validators: list[str] = Field(
        default_factory=list, validation_alias=AliasChoices('file_validators', 'validators')
    )
