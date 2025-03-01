from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.schemas import ReportCreateRequest, ReportResponse, ReportStatusResponse
from app.database.crud import (
    create_report_entry,
    get_report_by_id,
    get_report_content
)
from app.database.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    """
    Dependency that provides a SQLAlchemy database session.
    Ensures the session is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(report_req: ReportCreateRequest, db: Session = Depends(get_db)):
    """
    Creates a new report generation request using provided report parameters and user info.
    """
    try:
        report = create_report_entry(
            db,
            report_req.user_id,
            report_req.report_type,
            report_req.parameters
        )
        logger.info("Report created successfully with id: %s", report["report_id"])
        return ReportResponse(
            report_id=report["report_id"],
            status=report["status"]
        )
    except Exception as e:
        logger.error("Error creating report: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to create report")


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    """
    Retrieves report details by report ID, including its generation status,
    all Tier 2 sections (id, title, content), and the signed PDF download URL if completed.
    """
    report = get_report_by_id(db, report_id)
    if not report:
        logger.warning("Report with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # Pull sections array from wherever they are stored (example uses 'sections' key).
    sections = report.get("sections", [])
    # If the report is completed, we can return the signed PDF download URL as well
    signed_pdf_download_url = None
    if report["status"] == "completed":
        signed_pdf_download_url = report.get("signed_pdf_download_url")

    # Construct the final JSON response
    response_data = {
        "report_id": report["report_id"],
        "status": report["status"],
        "sections": sections  # each item: {"id": ..., "title": ..., "content": ...}
    }
    # Include signed PDF URL if completed
    if signed_pdf_download_url:
        response_data["signed_pdf_download_url"] = signed_pdf_download_url

    return response_data


@router.get("/reports/{report_id}/content")
def get_report_content_endpoint(report_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the content details for a completed report, including the Tier 2
    sections and the signed PDF download URL if available.
    """
    content = get_report_content(db, report_id)
    if not content:
        logger.warning("Content for report id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report content not found")

    # The content might contain the same structure (sections + possibly a URL).
    sections = content.get("sections", [])
    status = content.get("status", "completed")  # or pull from the main report record
    signed_pdf_download_url = content.get("signed_pdf_download_url")

    response_data = {
        "report_id": report_id,
        "status": status,
        "sections": sections
    }
    if signed_pdf_download_url:
        response_data["signed_pdf_download_url"] = signed_pdf_download_url

    return response_data


@router.get("/reports/{report_id}/status", response_model=ReportStatusResponse)
def report_status(report_id: int, db: Session = Depends(get_db)):
    """
    Returns the current status and progress of a report generation.
    This endpoint allows clients to poll for generation progress.
    """
    report = get_report_by_id(db, report_id)
    if not report:
        logger.warning("Report with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    progress = report.get("progress")
    return ReportStatusResponse(
        report_id=report["report_id"],
        status=report["status"],
        progress=progress
    )
