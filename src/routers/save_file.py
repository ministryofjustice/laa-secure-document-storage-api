import os
from typing import Type, Optional

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from src.models.file_upload import FileUpload
from src.services.s3_service import save as saveToS3
from src.validation.validator import validate_request

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
        body: FileUpload = Depends(validate_json(FileUpload))):
    validation_result = await validate_request(request.headers, file)
    if validation_result.status_code != 200:
        raise HTTPException(status_code=validation_result.status_code, detail=validation_result.message)
    metadata = body.model_dump()

    bucketName = metadata.pop('bucketName')
    folderPrefix = metadata.pop('folder')
    full_filename = os.path.join(folderPrefix if folderPrefix else '', file.filename)

    try:
        success = saveToS3(file.file, full_filename, bucketName, metadata)

        if success:
            return JSONResponse(status_code=200, content={
                "success": f"Files Saved successfully in {bucketName} with key {full_filename} "})

    except Exception as e:
        logger.error(f"An error occurred while uploading the file: {e}")
        raise HTTPException(status_code=500, detail='Something went wrong uploading file')
