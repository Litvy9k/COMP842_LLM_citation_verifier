from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    metadata: Dict[str, Any]  # requires: doi, title, authors(list), year(int)
    full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)

class ValidateResponse(BaseModel):
    ok: bool
    message: str = ""
    doc_id: Optional[int] = None
    hashed_doi: Optional[str] = None
    hashed_tah: Optional[str] = None
    metadata_root: Optional[str] = None
    fulltext_root: Optional[str] = None
    onchain_metadata_root: Optional[str] = None
    onchain_fulltext_root: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class CompleteValidateRequest(BaseModel):
    metadata: Dict[str, Any]
    full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)

class PartialValidateRequest(BaseModel):
    metadata: Dict[str, Any]
    fields_to_check: List[str] = []
