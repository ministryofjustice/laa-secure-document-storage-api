from fastapi import APIRouter
from pydantic import BaseModel
from src.utils.operation_types import OperationType
from src.services.Audit_Service import get_all_items, put_item
router = APIRouter()


class AuditItem(BaseModel):
    service_id: str
    file_id: str
    operation: OperationType


@router.post("/audit/")
async def update_audit_item(item: AuditItem):
    put_item(item.service_id, item.file_id, item.operation)
    return {"message": "Item updated successfully"}


@router.get("/audit/")
async def read_audit_items():
    items = get_all_items()
    return {"items": items}
