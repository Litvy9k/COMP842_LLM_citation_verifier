# app/models.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# =============== Auth Envelope ===================
class AuthEnvelope(BaseModel):
    message: str
    signature: str
    sig_type: Optional[str] = "eip191"

# =============== Metadata (六字段-完整) ===========
class Metadata(BaseModel):
    doi: str
    title: str
    author: List[str]          # 数组
    date: str                  # YYYY-MM-DD
    journal: str
    abstract: str

# =============== MetadataPartial (六字段-可选) ====
# 仅用于“定位论文”的请求体：允许只给 doi，或给 title+author+date 三元组
class MetadataPartial(BaseModel):
    doi: Optional[str] = None
    title: Optional[str] = None
    author: Optional[List[str]] = None
    date: Optional[str] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None

# =============== Requests ========================
class RegisterRequest(BaseModel):
    auth: AuthEnvelope
    metadata: Metadata                # 注册需要完整六字段
    full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)

class RetractionStatusRequest(BaseModel):
    doc_id: Optional[int] = None
    metadata: Optional[MetadataPartial] = None   # ✅ 改成 Partial

class RetractionSetRequest(BaseModel):
    auth: AuthEnvelope
    doc_id: Optional[int] = None
    metadata: Optional[MetadataPartial] = None   # ✅ 改成 Partial
    retract: bool

class EditRequest(BaseModel):
    auth: AuthEnvelope
    old_doc_id: Optional[int] = None
    old_metadata: Optional[MetadataPartial] = None   # ✅ 旧文定位用 Partial
    new_metadata: Metadata                            # 新文仍需完整六字段
    new_full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)

class CompleteValidateRequest(BaseModel):
    # 完整验证需要计算根；要么提供 doc_id，要么提供完整 metadata
    doc_id: Optional[int] = None
    metadata: Optional[Metadata] = None              # 保持完整
    full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)
    include_retraction: bool = True

# =============== Responses =======================
class ValidateResponse(BaseModel):
    ok: bool
    doc_id: Optional[int] = None

    hashed_doi: Optional[str] = None
    hashed_tad: Optional[str] = None
    metadata_root: Optional[str] = None
    fulltext_root: Optional[str] = None

    onchain_metadata_root: Optional[str] = None
    onchain_fulltext_root: Optional[str] = None

    matches: Optional[Dict[str, bool]] = None
    details: Optional[Dict[str, Any]] = None
    is_retracted: Optional[bool] = None
