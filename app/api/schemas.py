from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ReportSection(BaseModel):
    """
    Represents an individual section in the final API response.
    Even though 'sections' are stored in JSONB in the DB, we can
    still represent them as a list of 'ReportSection' objects in responses.
    """
    id: str
    title: str
    content: Optional[str]
    sub_sections: Optional[List[Dict[str, Any]]] = None

class CreateReportRequest(BaseModel):
    """
    Schema for creating a new 'report_requests' entry.
    """
    user_id: str = Field(..., description="ID of the user requesting the report")
    startup_id: Optional[str] = None
    report_type: Optional[str] = None
    title: str = Field(..., description="Title of the report")
    parameters: Dict[str, Any] = Field(..., description="Parameters for report generation")

class ReportResponse(BaseModel):
    """
    Detailed response for a single report request.
    Note: id is a UUID in the DB, so it's a string type here.
    """
    id: str
    title: str
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]
    progress: Optional[int]
    startup_id: Optional[str]
    user_id: Optional[str]
    report_type: Optional[str]
    parameters: Optional[Dict[str, Any]]
    sections: Optional[List[ReportSection]] = None
    signed_pdf_download_url: Optional[str]

class ReportStatusResponse(BaseModel):
    """
    Response for checking the status and progress of a report request.
    """
    status: str
    progress: Optional[int]
    # If your 'report_requests.id' is a UUID, use str here:
    report_id: Optional[str] = None

class ReportContentResponse(BaseModel):
    """
    Response for retrieving just the content (sections)
    and an optional signed PDF download URL.
    """
    url: Optional[str]
    status: Optional[str]
    sections: Optional[List[ReportSection]]
