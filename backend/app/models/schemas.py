from typing import List

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    status: str
    filename: str


class QueryResponse(BaseModel):
    status: str
    results: List[str] = []
