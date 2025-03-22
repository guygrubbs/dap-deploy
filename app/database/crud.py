from sqlalchemy.orm import Session
from datetime import datetime
import json
from typing import Dict, Any

# 1) Updated import to use ReportRequest instead of Report/ReportSection
from app.database.models import ReportRequest

def create_report_request(
    db: Session,
    title: str,
    user_id: str,
    startup_id: str,
    report_type: str,
    parameters: dict
) -> ReportRequest:
    """
    Creates a new record in the 'report_requests' table (status='pending' by default)
    with any initial parameters you supply.

    Args:
        db: SQLAlchemy Session
        title: Title of the report
        user_id: The user who requested the report
        startup_id: The startup ID associated with this report
        report_type: e.g., 'investment_readiness'
        parameters: Additional JSON parameters (pitch_deck_url, etc.)

    Returns:
        The newly created ReportRequest object (already committed to DB).
    """
    new_request = ReportRequest(
        title=title,
        status="pending",  # if you'd rather let DB defaults handle this, remove this line
        user_id=user_id,
        startup_id=startup_id,
        report_type=report_type,
        parameters=parameters
    )
    db.add(new_request)
    try:
        db.commit()
        db.refresh(new_request)
        return new_request
    except:
        db.rollback()
        raise

def get_report_request_by_id(db: Session, request_id: str) -> ReportRequest:
    """
    Retrieve a single record from 'report_requests' by its primary key (UUID string).
    """
    return db.query(ReportRequest).filter(ReportRequest.id == request_id).first()

def update_report_request_status(db: Session, request_id: str, new_status: str) -> ReportRequest:
    """
    Update the status of a report request in 'report_requests' (e.g., 'processing', 'ready_for_review').
    Remove references to 'completed' if not using that exact status.
    """
    report_request = db.query(ReportRequest).filter(ReportRequest.id == request_id).first()
    if not report_request:
        raise ValueError("Report request not found")

    report_request.status = new_status
    try:
        db.commit()
        db.refresh(report_request)
        return report_request
    except Exception as e:
        db.rollback()
        raise e

def update_report_sections(db: Session, request_id: str, sections_dict: Dict[str, Any]):
    """
    Stores the entire sections data in the JSONB 'sections' column of 'report_requests'.
    If your sections are a dict like:
      {
        "executive_summary_investment_rationale": "...",
        "market_opportunity_competitive_landscape": "...",
        ...
      }
    or a list of section objects, you can assign it directly to 'sections'.
    """
    request_obj = db.query(ReportRequest).filter(ReportRequest.id == request_id).first()
    if not request_obj:
        raise ValueError("Report request not found")

    request_obj.sections = sections_dict  # Overwrite the existing JSON data
    try:
        db.commit()
        db.refresh(request_obj)
        return request_obj
    except Exception as e:
        db.rollback()
        raise e

def update_report_request_pdf(db: Session, request_id: str, pdf_url: str) -> ReportRequest:
    """
    If you need to update a 'signed_pdf_download_url' or 'report_url' after generation,
    call this function. Adjust the field if you store the PDF differently.
    """
    report_request = db.query(ReportRequest).filter(ReportRequest.id == request_id).first()
    if not report_request:
        raise ValueError("Report request not found")

    # e.g., if you're storing the final PDF URL in 'signed_pdf_download_url':
    report_request.signed_pdf_download_url = pdf_url
    report_request.storage_path = pdf_url

    try:
        db.commit()
        db.refresh(report_request)
        return report_request
    except Exception as e:
        db.rollback()
        raise e
