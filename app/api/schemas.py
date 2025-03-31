from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class CreateReportRequest(BaseModel):
    """
    Request model for creating a new report, placing certain fields at top level.
    """
    user_id: int
    startup_id: Optional[int] = None

    # New top-level fields
    founder_name: Optional[str] = None
    founder_company: Optional[str] = None
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    industry: Optional[str] = None
    funding_stage: Optional[str] = None
    pitch_deck_url: Optional[str] = None

    report_type: Optional[str] = None
    title: str

    # For any other user-defined data
    parameters: Optional[Dict[str, Any]] = None


class ReportSection(BaseModel):
    """
    Represents a single section within a report.
    """
    id: str
    title: str
    content: str
    sub_sections: List["ReportSection"] = []


class ReportResponse(BaseModel):
    """
    Response model for returning full report details.
    """
    id: int
    title: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    progress: int
    startup_id: Optional[int] = None
    user_id: Optional[int] = None
    report_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    sections: List[ReportSection]
    signed_pdf_download_url: Optional[str] = None


class ReportContentResponse(BaseModel):
    """
    Response model for returning report content details.
    """
    url: Optional[str] = None
    status: str
    sections: List[ReportSection]


class ReportStatusResponse(BaseModel):
    """
    Response model for returning report status and progress.
    """
    status: str
    progress: int
    report_id: int
