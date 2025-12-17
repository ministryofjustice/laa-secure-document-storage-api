import structlog
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends, Request
from fastapi.responses import JSONResponse

from src.middleware.client_config_middleware import client_config_middleware
from src.models.client_config import ClientConfig
from src.validation import suspicious_content_validator

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
    Scans the provided CSV or XML file for some types of potentially malicious content:
    (HTML tags, JavaScript, SQL injection).

    If file has mimetype "application/xml" or "text/xml"), scan will automatically be in
    XML mode and delimiter ignored. Also, when XML mode used, the response text will start "(XML Scan")

    * 200 - No suspected malicious content was detected
    * 400 - Suspected malicious content was detected
    """
    xml_mode = False
    mode_text = ""
    if file.content_type in ("application/xml", "text/xml"):
        xml_mode = True
        mode_text = "(XML Scan) "

    validator = suspicious_content_validator.ScanForSuspiciousContent()
    status_code, message = validator.validate(file, delimiter, xml_mode=xml_mode)
    if status_code != 200:
        logger.info(f"Scan completed for {file.filename}: Possible malicious content detected")
        raise HTTPException(
            status_code=status_code,
            detail=f"{mode_text}{message}"
        )

    logger.info(f"Scan completed for {file.filename}: No malicious content detected")
    return JSONResponse(
        status_code=200, content={
            "success": f"{mode_text}No malicious content detected"
        }
    )
