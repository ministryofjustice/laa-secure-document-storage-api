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

    filename - the filename
    postitions - location(s) of filename in the upload list (starting from 0)
    outcomes - outcomes for each attempted load of the file within the bulk load
    checksum - checksum from latest succesful load of the file within the bulk load
    """
    filename: str
    positions: list[int]
    outcomes: list[dict]
    checksum: Optional[str] = None
