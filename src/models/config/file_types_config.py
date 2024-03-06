from typing import List

from pydantic import BaseModel


class AcceptedFileTypes(BaseModel):
    acceptedExtensions: List[str]
    acceptedContentTypes: List[str]