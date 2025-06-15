from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, EmailStr, Field, UUID4

# INBOUND schema - restored for API endpoint
class AnalysisRequestIn(BaseModel):
    user_id: UUID4
    startup_id: Optional[str] = None
    report_type: str = "tier-1"
    title: str
    founder_name: str
    company_name: Optional[str] = "Right Hand Operation"
    requestor_name: Optional[str] = ""
    email: Optional[EmailStr] = ""
    industry: Optional[str] = None
    funding_stage: Optional[str] = None
    company_type: Optional[str] = None
    additional_info: Optional[str] = None
    pitch_deck_url: Optional[str] = None

# OUTBOUND schema – reflects a row in analysis_requests table
class AnalysisRequestOut(BaseModel):
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

# Report content section models (unchanged) ...
class ReportSection(BaseModel):
    id: str = Field(..., description="slug or heading anchor")
    title: str
    content: str
    sub_sections: List["ReportSection"] = []

class ReportContentResponse(BaseModel):
    """Returned by GET /api/reports/{id}/content after generation."""
    status: str
    url: Optional[str] = None           # public PDF URL (from deal_reports or parameters):contentReference[oaicite:14]{index=14}
    sections: List[ReportSection]

class ReportStatusResponse(BaseModel):
    """Light-weight status check for a report generation."""
    report_id: UUID4
    status: str
    progress: int = 0
