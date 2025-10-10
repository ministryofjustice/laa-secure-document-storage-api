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

    checksum - checksum from latest succesful load of the file within the bulk load
    outcomes - list of outcomes for each load of the file within the bulk load
    postitions - location(s) of file in the upload list (starting from 0)
    """
    filename: str
    positions: list[int]
    checksum: Optional[str] = None
    outcomes: list
