from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, Depends, Request
from fastapi.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.validation import csv_validator

router = APIRouter()
logger = structlog.get_logger()


@router.put("/scan_for_suspicious_content")
async def scan_for_suspicious_content(
            request: Request,
            file: Optional[UploadFile] = UploadFile(None),
            client_config: ClientConfig = Depends(client_config_middleware),
        ):
    """
    Scans the provided CSV file for potentially malicious content (HTML tags, JavaScript, formula injection).
    * 200 If no known malicious content was detected
    * 400 If malicious content was detected
    """

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # This check to be expanded in future work to accept XML files also.
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Extra content-type check
    if file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="Invalid content type. Expected text/csv")

    # The delimiter is currently hardcoded as ',' but may become configurable in future work.
    delimiter = ","

    validator = csv_validator.ScanCSV()
    status_code, message = validator.validate(file, delimiter=delimiter)
    if status_code != 200:
        raise HTTPException(
            status_code=status_code,
            detail=message
        )

    logger.info(f"Scan completed for {file.filename}: no malicious content detected")
    return JSONResponse(
        status_code=200, content={
            "success": "No malicious content detected"
        }
    )
