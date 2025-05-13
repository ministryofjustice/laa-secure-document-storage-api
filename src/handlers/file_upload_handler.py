import os
import structlog
from typing import Optional, Tuple, Dict
from fastapi import HTTPException, UploadFile, Request

from src.models.client_config import ClientConfig
from src.models.file_upload import FileUpload
from src.services import audit_service, s3_service
from src.utils.operation_types import OperationType
from src.utils.request_types import RequestType
from src.validation import clam_av_validator, client_configured_validator

logger = structlog.get_logger()


async def handle_file_upload_logic(
    request: Request,
    file: Optional[UploadFile],
    body: FileUpload,
    client_config: ClientConfig,
    request_type: RequestType,
) -> Tuple[Dict, bool]:
    
    # Read contents of file. Only works once - get nothing if try a second time.  
    file_contents = await file.read()
    
    # Antivirus scan
    validation_result = await clam_av_validator.scan_request(request.headers, file, file_contents)
    if validation_result.status_code != 200:
        raise HTTPException(
            status_code=validation_result.status_code,
            detail=validation_result.message
        )

    # Client-specific validation
    await client_configured_validator.validate_or_error(file, client_config.file_validators)

    metadata = body.model_dump() or {}
    bucket_name = metadata.pop("bucketName", None)
    if bucket_name != client_config.bucket_name:
        # For compatibility we allow the bucket name to be specified in the request,
        # but log a warning to help prevent confusion
        logger.warning(
            f"{client_config.azure_client_id} specified {bucket_name}, "
            f"not configured name {client_config.bucket_name}"
        )

    folder_prefix = metadata.pop("folder", "")
    full_filename = os.path.join(folder_prefix, file.filename) if folder_prefix else file.filename

    file_existed = False

    try:
        file_existed = s3_service.file_exists(client_config, full_filename)
        if request_type == RequestType.POST:
            if file_existed:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"File {full_filename} already exists and cannot be overwritten "
                        "via the /save_file endpoint. Use PUT endpoint /save_or_update_file to overwrite."
                    )
                )

        audit_service.put_item(
            client_config.azure_display_name,
            full_filename,
            OperationType.CREATE
        )

        success = s3_service.save(client_config, file_contents, full_filename, metadata)
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"File {full_filename} failed to save for an unknown reason."
            )
        actioned = "updated" if file_existed else "saved"
        return {
            "success": f"File {actioned} successfully in {client_config.bucket_name} with key {full_filename}"
        }, file_existed

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"An {e.__class__.__name__} occurred while saving the file: {e}")
        raise HTTPException(status_code=500, detail=f"The file {full_filename} could not be saved")
