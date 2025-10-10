from typing import Optional

from pydantic import BaseModel


class FileUpload(BaseModel):
    bucketName: str
    folder: Optional[str] = None


class BulkUploadFileResponse(BaseModel):
    """
    Holds results for individual filename in a bulk upload
    Because same filename could occur more than once in the same load, we
    need to be able to store multiple outcomes.
    The checksum value is for the most recent successful load if the same filename
    is loaded more than once.
    """
    filename: str
    checksum: Optional[str] = None
    outcomes: list
