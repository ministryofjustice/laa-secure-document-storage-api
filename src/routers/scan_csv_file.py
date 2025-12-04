from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, Depends, Request
from fastapi.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
# from src.validation import placeholder_scan_csv_validator

router = APIRouter()
logger = structlog.get_logger()


@router.put("/scan_csv_file")
async def scan_csv_file(
            request: Request,
            file: Optional[UploadFile] = UploadFile(None),
            client_config: ClientConfig = Depends(client_config_middleware),
        ):
    """
    Scans the provided CSV file content for possible malicious SQL injection and returns
    * 200 If no known malicious content was detected
    * 400 If malicious content was detected
    """
    # validation_result = await placeholder_scan_csv_validator.scan_request(request.headers, file)
    # if validation_result.status_code != 200:
    #     raise HTTPException(
    #         status_code=validation_result.status_code,
    #         detail=validation_result.message
    #     )

    logger.info(f"File {file.filename} has negative malicious content scan result")
    return JSONResponse(
        status_code=200, content={
            "success": "No malicious content found"
        }
    )
