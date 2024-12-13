from pydantic import Field, AliasChoices, BaseModel


class ClientConfig(BaseModel):
    """
    Represents the client-specific API configuration, primarily the storage options.
    """
    client: str = Field(validation_alias=AliasChoices('client', 'client_id', 'username', 'subject'))
    service_id: str = Field(validation_alias=AliasChoices('service_id', 'requesting_service'))
    bucket_name: str = Field(validation_alias=AliasChoices('bucket_name', 'storage_id'))
