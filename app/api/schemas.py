from typing import Optional, Dict, Any, List
from pydantic import BaseModel, UUID4

class CreateReportRequest(BaseModel):
    user_id: str
    startup_id: Optional[str] = None
    founder_name: Optional[str] = None
    founder_company: Optional[str] = None
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    industry: Optional[str] = None
    funding_stage: Optional[str] = None
    pitch_deck_url: Optional[str] = None
    report_type: Optional[str] = None
    title: Optional[str] = 'Due Diligence Report'
    parameters: Optional[Dict[str, Any]] = None

class ReportSection(BaseModel):
    id: str
    title: str
    content: str
    sub_sections: List["ReportSection"] = []

class ReportResponse(BaseModel):
    id: UUID4  # ← Use UUID4 instead of int
    title: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    progress: int
    startup_id: Optional[str] = None
    user_id: Optional[str] = None
    report_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    sections: List[ReportSection]
    signed_pdf_download_url: Optional[str] = None

class ReportContentResponse(BaseModel):
    url: Optional[str] = None
    status: str
    sections: List[ReportSection]

class ReportStatusResponse(BaseModel):
    status: str
    progress: int
    report_id: UUID4  # ← If your route param is also a UUID
