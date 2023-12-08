from fastapi import APIRouter, Form, UploadFile, File, Depends
from pydantic import BaseModel

router = APIRouter()
class Metadata(BaseModel):
    file: UploadFile
    reference: str
    name: str

async def parse_upload_form(file: UploadFile = File(...), reference: str = Form(...),
                            name: str = Form(...)) -> Metadata:
    upload_form = Metadata(file=file, reference=reference, name=name)
    return upload_form

@router.post("/files", status_code=201)
async def saveFile(uploadForm: Metadata = Depends(parse_upload_form)):

    return {
        "file_name": uploadForm.name,
        "reference": uploadForm.reference

    }