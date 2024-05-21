from fastapi import APIRouter, HTTPException
from fastapi.params import Query

from src.services.s3_service import retrieveFileUrl
from src.services.Audit_Service import put_item
from src.utils.operation_types import OperationType

router = APIRouter()


@router.get('/retrieve_file')
async def retrieve_file(file_key: str = Query(None, min_length=1)):
    if not file_key:
        raise HTTPException(status_code=400, detail="File key is missing")

    try:
        put_item("equiniti-service-id", file_key, OperationType.READ)
        response = retrieveFileUrl(file_key)
        return {'fileURL': response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
