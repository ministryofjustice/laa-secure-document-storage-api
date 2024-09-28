from typing import Optional

from pydantic import BaseModel


class FileUpload(BaseModel):
    bucketName: str
    folder: Optional[str] = None
