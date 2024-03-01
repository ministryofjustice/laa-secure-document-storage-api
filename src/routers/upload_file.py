from fastapi import APIRouter, UploadFile, Request, HTTPException
from fastapi.responses import JSONResponse

from services.s3_service import save as saveToS3
from validation.validator import validate_request

router = APIRouter()


@router.post("/uploadFile")
async def uploadFile(file: UploadFile, request: Request) -> JSONResponse:
    validation_result = await validate_request(request.headers, file)
    if validation_result.status_code != 200:
        raise HTTPException(status_code=validation_result.status_code, detail=validation_result.message)
    else:
        success = saveToS3(file.file, file.filename)
        if success:
            return JSONResponse(status_code=200, content={"success": True})
        else:
            raise HTTPException(status_code=400, detail='Something went wrong')
