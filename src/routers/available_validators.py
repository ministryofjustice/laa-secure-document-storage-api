from fastapi import APIRouter

from src.validation.client_configured_validator import generate_all_filevalidatorspecs

router = APIRouter()


@router.get("/available_validators")
async def available_validators():
    """
    Returns details of all available validators that can be applied to an uploaded file.

    * Purpose is to provide details useful when creating SDS client config
    * Includes validator name, its kwargs and their default values
    * Just lists the validators that SDS makes available to all, not client-specific status
    * Virus check is not listed as it's not a configurable validator and is automatically applied to any file upload
    """
    validators = generate_all_filevalidatorspecs()
    return sorted(validators, key=lambda v: v.name)
