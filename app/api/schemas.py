from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, EmailStr, Field, UUID4   # UUID4 -> validates v4 only :contentReference[oaicite:1]{index=1}


# ──────────────────────────────────────────────────────────────────────────────
#  INBOUND  (create-request payload)
# ──────────────────────────────────────────────────────────────────────────────
class AnalysisRequestIn(BaseModel):
    """
    Payload expected by POST /api/reports.
    Only the fields that map to `analysis_requests` are retained.
    """
    user_id: UUID4
    requestor_name: str
    email: EmailStr
    founder_company: str                     # required so we can prepend in `additional_info`
    founder_name: Optional[str] = None
    industry: Optional[str] = None
    funding_stage: Optional[str] = None
    company_type: Optional[str] = None
    pitch_deck_url: Optional[str] = None
    additional_info: Optional[str] = None   # free-text from the form
    parameters: Optional[Dict[str, Any]] = None  # stays for misc meta (safe in JSONB)


# ──────────────────────────────────────────────────────────────────────────────
#  OUTBOUND  (single row echo-back)
# ──────────────────────────────────────────────────────────────────────────────
class AnalysisRequestOut(BaseModel):
    """
    Row returned after insert (initially status == 'pending').
    Mirrors `analysis_requests` columns + convenience fields.
    """
    id: UUID4
    user_id: UUID4
    company_name: str = "Right Hand Operation"
    requestor_name: str
    email: EmailStr
    founder_name: Optional[str] = None
    industry: Optional[str] = None
    funding_stage: Optional[str] = None
    company_type: Optional[str] = None
    pitch_deck_url: Optional[str] = None
    additional_info: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    external_request_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


# ──────────────────────────────────────────────────────────────────────────────
#  OPTIONAL  – structured report body once the PDF is generated
# ──────────────────────────────────────────────────────────────────────────────
class ReportSection(BaseModel):
    """Recursive tree for section rendering in the UI."""
    id: str = Field(..., description="slug or heading anchor")
    title: str
    content: str
    sub_sections: List["ReportSection"] = []


class ReportContentResponse(BaseModel):
    """
    Returned by GET /api/reports/{id}/content (after generation).
    """
    status: str
    url: Optional[str] = None          # public PDF url (deal_reports.pdf_url)
    sections: List[ReportSection]


class ReportStatusResponse(BaseModel):
    """Light-weight polling endpoint."""
    report_id: UUID4
    status: str
    progress: int = 0                  # optional % filled by edge function
