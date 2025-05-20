from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, Depends, Request
from fastapi.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.validation import clam_av_validator

router = APIRouter()
logger = structlog.get_logger()


@router.put("/virus_check_file")
async def virus_check_file(
            request: Request,
            file: Optional[UploadFile] = UploadFile(None),
            client_config: ClientConfig = Depends(client_config_middleware),
        ):
    """
    Scans the provided file for known viruses using a regularly updated internal ClamAV service, responding with:
    * 200 If no known viruses were detected
    * 400 If known viruses were detected
    """
    validation_result = await clam_av_validator.scan_request(request.headers, file)
    if validation_result.status_code != 200:
        raise HTTPException(
            status_code=validation_result.status_code,
            detail=validation_result.message
        )

    logger.info(f"File {file.filename} has negative AV scan result")
    return JSONResponse(
        status_code=200, content={
            "success": "No virus found"
        }
    )
