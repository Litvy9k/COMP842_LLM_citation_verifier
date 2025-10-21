# app/models.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

print("### models.py loaded from:", __file__)

# ---------------------------
#  Auth & Common DTOs
# ---------------------------

class AuthPayload(BaseModel):
    """
    EIP-191 signature payload.
    """
    message: str = Field(..., description="Exact message that was signed")
    signature: str = Field(..., min_length=10, description="0x-prefixed ECDSA signature")
    sig_type: Literal["eip191"] = Field("eip191", description="Signature scheme")


# ---------------------------
#  Register (add) flow
#  （保留原有 add 接口使用的形状）
# ---------------------------

class RegisterRequest(BaseModel):
    auth: AuthPayload
    metadata: Dict[str, Any] = Field(
        ...,
        description='Paper metadata. Must contain: "doi", "title", "authors"[list], "date" (YYYY-MM-DD).'
    )
    full_text: Optional[str] = Field(
        default=None,
        description="Optional full text for chunking/merkle."
    )
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)


class RegisterResponse(BaseModel):
    ok: bool
    message: Optional[str] = None
    doc_id: Optional[int] = None

    # Local computed (hex-strings)
    hashed_doi: Optional[str] = None
    hashed_tad: Optional[str] = None
    metadata_root: Optional[str] = None
    fulltext_root: Optional[str] = None

    # On-chain readback (if any)
    onchain_metadata_root: Optional[str] = None
    onchain_fulltext_root: Optional[str] = None

    details: Optional[Dict[str, Any]] = None
    # For consistency with validate endpoints if present
    is_retracted: Optional[bool] = None


# ---------------------------
#  Retraction (status / set)
# ---------------------------

class RetractionStatusRequest(BaseModel):
    """
    Query retraction by doc_id or metadata (with doi OR title+authors+date).
    """
    doc_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class RetractionSetRequest(BaseModel):
    """
    Set retract/unretract. Requires REGISTRAR_ROLE & server PRIVATE_KEY.
    Identify target by doc_id or metadata.
    """
    auth: AuthPayload
    doc_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    retract: bool


# ---------------------------
#  Edit = retract old + add new
# ---------------------------

class EditRequest(BaseModel):
    """
    Edit a paper: retract the old one, then register a new one.
    old_doc_id or old_metadata is required.
    new_metadata must include doi/title/authors/date.
    """
    auth: AuthPayload

    # Identify the old paper
    old_doc_id: Optional[int] = None
    old_metadata: Optional[Dict[str, Any]] = None

    # New content
    new_metadata: Dict[str, Any]
    new_full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)


class EditResponse(BaseModel):
    ok: bool
    tx_retract: Optional[str] = None
    tx_add: Optional[str] = None
    old_doc_id: Optional[int] = None

    new_hashed_doi: Optional[str] = None
    new_hashed_tad: Optional[str] = None
    new_metadata_root: Optional[str] = None
    new_fulltext_root: Optional[str] = None

    details: Optional[Dict[str, Any]] = None


# ---------------------------
#  (Optional) Validate
#  如果你的后端里有 /validate 相关使用到这个响应结构
# ---------------------------

class ValidateResponse(BaseModel):
    ok: bool
    details: Optional[Dict[str, Any]] = None
    # 新增：用于把撤稿状态串联到验证结果里（如果你的实现会返回它）
    is_retracted: Optional[bool] = None
    
    
    # --- Complete validation input (kept for backward-compat) ---
class CompleteValidateRequest(BaseModel):
    """
    Backward-compatible request model for the /validate (complete) endpoint.
    Identify the paper by doc_id OR metadata (with doi OR title+authors+date).
    Extra fields are optional so older code won't crash.
    """
    # ways to identify the paper
    doc_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None  # expects keys: doi/title/authors/date (YYYY-MM-DD)

    # optional helpers some implementations may read
    hashed_doi: Optional[str] = None
    hashed_tad: Optional[str] = None
    metadata_root: Optional[str] = None
    fulltext_root: Optional[str] = None

    # full text (if your validation recomputes merkle locally)
    full_text: Optional[str] = None
    chunk_size: int = Field(default=4096, ge=1, le=1_000_000)

    # whether to include retraction flag in the validation response
    include_retraction: bool = True

