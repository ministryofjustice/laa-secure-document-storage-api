from fastapi import APIRouter, Form, UploadFile, File, Depends
from pydantic import BaseModel, Field
from typing import Optional
import boto3
from src.services.s3_service import S3Service

router = APIRouter()

def get_s3_service():
    service = S3Service.getInstance()
    return service()


BUCKET = 'ss-poc-test'            
class Metadata(BaseModel):
    file: UploadFile = Field(..., description="File is required")
    reference: Optional[str]  = Field(None, alias="reference")
    name: str = Field(..., description="The name field is required")

async def parse_upload_form(file: UploadFile = File(...), reference: Optional[str] = Form(None),
                            name: str = Form(...)) -> Metadata:
    upload_form = Metadata(file=file, reference=reference, name=name)
    return upload_form

@router.post("/files", status_code=201)
async def saveFile(uploadForm: Metadata = Depends(parse_upload_form),
                   s3_client: boto3.client = Depends(get_s3_service)):
    file_content = await uploadForm.file.read()
    response = s3_client.put_object(Bucket='ss-poc-test',Key=uploadForm.name, Body=file_content)
    success =  response['ResponseMetadata']['HTTPStatusCode'] == 200
    return {
        "file_name": uploadForm.name,
        "reference": uploadForm.reference,
        "success": success
    }