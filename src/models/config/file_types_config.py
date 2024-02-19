from pydantic import BaseModel, Field
from typing import List

class AcceptedFileTypes(BaseModel):
    acceptedExtensions: List[str]
    acceptedContentTypes: List[str]