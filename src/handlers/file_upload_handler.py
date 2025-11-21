import os
import structlog
from typing import Optional, Tuple, Dict
from fastapi import HTTPException, UploadFile, Request

from src.models.client_config import ClientConfig
from src.models.file_upload import FileUpload
from src.models.audit_record import AuditRecord
from src.services import audit_service, s3_service
from src.services.checksum_service import get_file_checksum
from src.utils.operation_types import OperationType
from src.utils.request_types import RequestType
from src.validation import clam_av_validator, client_configured_validator, mandatory_file_validator


logger = structlog.get_logger()


async def handle_file_upload_logic(
    request: Request,
    file: Optional[UploadFile],
    body: FileUpload,
    client_config: ClientConfig,
    request_type: RequestType,
    filename_position: int = 0
) -> Tuple[Dict, bool]:

    # Bucket check
    metadata = body.model_dump() or {}
    bucket_name = metadata.pop("bucketName", None)
    if bucket_name != client_config.bucket_name:
        # For compatibility we allow the bucket name to be specified in the request,
        # but log a warning to help prevent confusion
        logger.warning(
            f"{client_config.azure_client_id} specified {bucket_name}, "
            f"not configured name {client_config.bucket_name}"
        )

    # Initial file checks - virus scan, mandatory validators, client config validators ...
    checksum, error_status = await run_initial_file_checks(request, file, client_config)

    folder_prefix = metadata.pop("folder", "")
    full_filename = os.path.join(folder_prefix, file.filename) if folder_prefix else file.filename
    file_existed = False

    # Check file not already in S3 when POST request
    if not error_status:
        file_existed = s3_service.file_exists(client_config, full_filename)
        if file_existed and request_type == RequestType.POST:
            error_status = (409, f"File {full_filename} already exists and cannot be overwritten "
                            "via the /save_file endpoint. Use PUT endpoint /save_or_update_file to overwrite.")

    # Save file to bucket
    if not error_status:
        try:
            success = s3_service.save(client_config, file.file, full_filename, checksum, metadata)
            if not success:
                # This is retained for consistency but might never happen, with Exception handling
                # below actually reporting the error when save fails
                error_status = (500, f"File {full_filename} failed to save for an unknown reason.")
        except Exception as e:
            logger.error(f"An {e.__class__.__name__} occurred while saving the file: {e}")
            error_status = (500, f"The file {full_filename} could not be saved")

    # Update audit table
    audit_record = AuditRecord(request_id=request.headers["x-request-id"],
                               filename_position=filename_position,
                               service_id=client_config.azure_display_name,
                               file_id=str(full_filename),  # str() because can be None when error
                               operation_type=OperationType.UPDATE if file_existed
                               else OperationType.CREATE,
                               # str(error_status[1]) because clam_av errors are list, not str
                               error_details=str(error_status[1]) if error_status else "")
    try:
        audit_service.put_item(audit_record)
    except Exception as e:
        logger.error(f"Error writing to audit table {str(e)}")
        # Potential issue - if there was an Exception on writing to S3, followed by an exception
        # here, then the original error_status is lost. Concatenate error messages?
        error_status = (500, "An error occurred while retrieving the file")

    if error_status:
        raise HTTPException(status_code=error_status[0], detail=error_status[1])

    actioned = "updated" if file_existed else "saved"
    return {
        "success": f"File {actioned} successfully in {client_config.bucket_name} with key {full_filename}",
        "checksum": checksum
    }, file_existed


async def run_initial_file_checks(request: Request,
                                  file: UploadFile,
                                  client_config: ClientConfig) -> tuple[str, tuple]:
    error_status = ()
    # Antivirus scan - note unlike the other checks, validation_result.message is a list, not str
    validation_result = await clam_av_validator.scan_request(request.headers, file)
    if validation_result.status_code != 200:
        error_status = (validation_result.status_code, validation_result.message)

    # Mandatory validation - must run before client-specific validation
    if not error_status:
        status_code, detail = mandatory_file_validator.run_mandatory_validators(file)
        if status_code != 200:
            error_status = (status_code, detail)

    # Client-specific validation
    if not error_status:
        try:
            await client_configured_validator.validate_or_error(file, client_config.file_validators)
        except HTTPException as e:
            error_status = (e.status_code, e.detail)

    # Get checksum from file
    checksum = ""
    if not error_status:
        checksum, error_message = get_file_checksum(file)
        if error_message:
            error_status = (500, error_message)
    return checksum, error_status
