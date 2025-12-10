import structlog
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, Request
from fastapi.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.validation import csv_validator

router = APIRouter()
logger = structlog.get_logger()


@router.put("/scan_for_suspicious_content")
async def scan_for_suspicious_content(
            request: Request,
            file: UploadFile = File(...),
            delimiter: str = ",",
            client_config: ClientConfig = Depends(client_config_middleware),
        ):
    """
    Scans the provided CSV file for some types of potentially malicious content (HTML tags, JavaScript, SQL formulae).
    * 200 - No suspected malicious content was detected
    * 400 - Suspected malicious content was detected
    """

    validator = csv_validator.ScanCSV()
    status_code, message = validator.validate(file, delimiter)
    if status_code != 200:
        logger.info(f"Scan completed for {file.filename}: Possible malicious content detected")
        raise HTTPException(
            status_code=status_code,
            detail=message
        )

    logger.info(f"Scan completed for {file.filename}: No malicious content detected")
    return JSONResponse(
        status_code=200, content={
            "success": "No malicious content detected"
        }
    )
