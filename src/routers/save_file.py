import os
from typing import Type, Optional

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.models.file_upload import FileUpload
from src.services import audit_service, s3_service
from src.utils.operation_types import OperationType
from src.validation.av_validator import validate_request

router = APIRouter()
logger = structlog.get_logger()


def validate_json(model: Type[BaseModel]):
    def wrapper(body: str = Form(...)):
        try:
            return model.parse_raw(body)
        except ValidationError as exc:
            error_details = {error['loc'][0]: error['msg'] for error in exc.errors()}
            raise HTTPException(status_code=400, detail=error_details)

    return wrapper


@router.post("/save_file")
async def save_file(
            request: Request,
            file: Optional[UploadFile] = UploadFile(None),
            body: FileUpload = Depends(validate_json(FileUpload)),
            client_config: ClientConfig = Depends(client_config_middleware),
        ):
    validation_result = await validate_request(request.headers, file)
    if validation_result.status_code != 200:
        raise HTTPException(status_code=validation_result.status_code, detail=validation_result.message)

    metadata = body.model_dump()
    if metadata is None:
        metadata = {}

    bucketName = metadata.pop('bucketName')
    if bucketName != client_config.bucket_name:
        # For compatibility we allow the bucket name to be specified in the request,
        # but log a warning to help prevent confusion
        logger.warning(
            f"{client_config.client} specified {bucketName}, not configured name {client_config.bucket_name}"
        )

    folder_prefix = metadata.pop('folder')
    full_filename = os.path.join(folder_prefix if folder_prefix else '', file.filename)

    try:
        audit_service.put_item(client_config.service_id, full_filename, OperationType.CREATE)
        success = s3_service.save(client_config, file.file, full_filename, metadata)

        if success:
            return JSONResponse(
                status_code=200, content={
                    "success": f"Files Saved successfully in {client_config.bucket_name} with key {full_filename} "
                }
            )

    except Exception as e:
        logger.error(f"An {e.__class__.__name__} occurred while uploading the file: {e}")
        raise HTTPException(status_code=500, detail='Something went wrong uploading file')
