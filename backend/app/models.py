from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class AuthPayload(BaseModel):
    message: str
    signature: str
    sig_type: Literal["eip191"] = "eip191"

class RegisterRequest(BaseModel):
    auth: AuthPayload
    metadata: Dict[str, Any]
    full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)

class ValidateResponse(BaseModel):
    ok: bool
    message: str = ""
    doc_id: Optional[int] = None
    hashed_doi: Optional[str] = None
    hashed_tad: Optional[str] = None
    metadata_root: Optional[str] = None
    fulltext_root: Optional[str] = None
    onchain_metadata_root: Optional[str] = None
    onchain_fulltext_root: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class CompleteValidateRequest(BaseModel):
    auth: Optional[AuthPayload] = None
    metadata: Dict[str, Any]
    full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)
