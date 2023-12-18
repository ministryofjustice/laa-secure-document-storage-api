from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from services.s3_service import save as saveToS3

router = APIRouter()

@router.post("/uploadFile")
async def uploadFile(file: UploadFile) -> JSONResponse:
    success = saveToS3(file.file, file.filename)
    if success:
        return JSONResponse(status_code = 200, content = {"success": True})
    else:
        raise HTTPException(status_code=400, detail='Something went wrong')
