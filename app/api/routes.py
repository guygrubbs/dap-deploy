import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.database.crud import (
    create_report_entry,
    get_report_by_id,
    get_report_content
)
from app.database.database import SessionLocal

logger = logging.getLogger(__name__)

# Create a router with NO prefix
# (We previously might have used APIRouter(prefix="/api"), but it's removed now)
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


@router.post("/reports", status_code=status.HTTP_201_CREATED)
def create_report(
    db: Session = Depends(get_db),
    user_id: str = Body(...),
    startup_id: Optional[str] = Body(None),
    report_type: Optional[str] = Body(None),
    title: str = Body(...),
    parameters: Dict[str, Any] = Body(...)
):
    """
    Creates a new report generation request using provided report parameters and user info.
    Required fields: user_id, title, parameters
    Optional fields: startup_id, report_type
    """
    try:
        # Create the report in DB.
        # This example expects a function: create_report_entry(db, title, user_id, startup_id, report_type)
        # If your existing function differs, adjust accordingly.
        new_report = create_report_entry(
            db=db,
            title=title,
            user_id=user_id,
            startup_id=startup_id,
            report_type=report_type,
            parameters=parameters
        )

        # Build the response including the fields the front-end wants:
        response_data = {
            "id": new_report.id,
            "title": new_report.title,
            "status": new_report.status,
            "created_at": new_report.created_at,
            "updated_at": new_report.completed_at,  # or last update time if you track it
            "progress": 0,  # or retrieve from new_report if you track progress
            "startup_id": startup_id,
            "user_id": user_id,
            "report_type": report_type,
            "parameters": parameters,
            "sections": []  # empty for now; sections typically get populated later
        }
        return response_data

    except Exception as e:
        logger.error("Error creating report: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to create report")


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    """
    Retrieves report details by report ID, including:
    - generation status
    - Tier 2 sections: each with sub_sections array
    - the signed PDF download URL if completed
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("Report with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # Convert DB model to dictionary-like object
    # Make sure your crud.get_report_by_id() or your model includes the necessary fields.
    # e.g. report_model.title, report_model.status, ...
    # We'll pretend 'report_model.sections' is a list of DB objects with .section_name, .content, etc.
    # You can build the sub_sections however you prefer. This is a simple demonstration.

    # Example: We'll generate a stable "id" from the section_name, plus an empty sub_sections or a placeholder.
    # If you do parse sub-sections from AI or store them separately, adapt here accordingly.
    sections_list = []
    for i, sec in enumerate(report_model.sections, start=1):
        section_id = f"section_{i}"
        sections_list.append({
            "id": section_id,
            "title": sec.section_name,
            "content": sec.content or "",
            "sub_sections": [
                # If your AI agent or DB actually stores sub-sections, map them here:
                # e.g. {"id": "overview", "title": "Overview", "content": "..."}
                # For demonstration, we just show an empty array or a minimal example.
            ]
        })

    # If the report is completed, get the signed PDF URL from somewhere (if stored in the DB).
    signed_pdf_download_url = None  # e.g. report_model.pdf_url if you store it
    if report_model.status.lower() == "completed":
        # Suppose we stored it in a column named pdf_url or so:
        signed_pdf_download_url = getattr(report_model, "pdf_url", None)

    response_data = {
        "id": report_model.id,
        "title": report_model.title,
        "status": report_model.status,
        "created_at": report_model.created_at,
        "updated_at": report_model.completed_at,
        "startup_id": getattr(report_model, "startup_id", None),
        "user_id": getattr(report_model, "user_id", None),
        "report_type": getattr(report_model, "report_type", None),
        "sections": sections_list
    }

    if signed_pdf_download_url:
        response_data["signed_pdf_download_url"] = signed_pdf_download_url

    return response_data


@router.get("/reports/{report_id}/content")
def get_report_content_endpoint(report_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the content details for a completed report,
    including Tier 2 sections (with sub_sections if present)
    and the signed PDF download URL if available.
    """
    # We re-use the same logic or you can store a final compiled structure in DB.
    # For demonstration, let's just call get_report(...) logic.
    # If you do something else, adapt accordingly:
    try:
        # Reuse the existing get_report function
        report_data = get_report(report_id, db)
        return {
            "url": report_data.get("signed_pdf_download_url") or "",
            "sections": report_data["sections"],
            "status": report_data["status"],
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.warning("Error retrieving content for report %s: %s", report_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve report content")


@router.get("/reports/{report_id}/status")
def report_status(report_id: int, db: Session = Depends(get_db)):
    """
    Returns the current status and progress of a report generation.
    Allows clients to poll for generation progress.
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("Report with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # If you store progress in the DB, fetch it here; else default to 100 if completed.
    # For demonstration:
    progress = 100 if report_model.status.lower() == "completed" else 50  # Just an example

    return {
        "status": report_model.status,
        "progress": progress
    }
