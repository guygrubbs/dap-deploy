# schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ReportSection(BaseModel):
    id: str
    title: str
    content: Optional[str]
    sub_sections: Optional[List[Dict[str, Any]]] = None

class CreateReportRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user requesting the report")
    startup_id: Optional[str] = None
    report_type: Optional[str] = None
    title: str = Field(..., description="Title of the report")
    parameters: Dict[str, Any] = Field(..., description="Parameters for report generation")

class ReportResponse(BaseModel):
    id: int
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
    status: str
    progress: Optional[int]
    # optionally include `report_id` if you want to
    report_id: Optional[int] = None

class ReportContentResponse(BaseModel):
    url: Optional[str]
    status: Optional[str]
    sections: Optional[List[ReportSection]]
