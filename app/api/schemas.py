from pydantic import BaseModel, Field
from typing import Optional, Dict

class ReportCreateRequest(BaseModel):
    user_id: int = Field(..., description="ID of the user requesting the report")
    report_type: str = Field(..., description="Type of report to generate")
    parameters: Optional[Dict[str, str]] = Field(
        default=None, description="Additional parameters for report generation"
    )

class ReportResponse(BaseModel):
    report_id: int = Field(..., description="Unique identifier for the report")
    status: str = Field(..., description="Current status of the report generation")
    download_url: Optional[str] = Field(
        default=None, description="Signed URL for downloading the report if available"
    )
    message: Optional[str] = Field(
        default=None, description="Additional message or error details"
    )

class ReportStatusResponse(BaseModel):
    report_id: int = Field(..., description="Unique identifier for the report")
    status: str = Field(..., description="Current status of the report generation")
    progress: Optional[int] = Field(
        default=None, description="Percentage completion of the report generation"
    )
