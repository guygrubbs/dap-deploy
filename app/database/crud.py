import json
import uuid
from datetime import datetime
from typing import Union, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import Report

from app.database.models import Report

def create_report_entry(
    db: Session,
    title: str,
    user_id: int,
    startup_id: Optional[int],
    report_type: Optional[str],
    founder_name: Optional[str],
    founder_company: Optional[str],
    company_name: Optional[str],
    company_type: Optional[str],
    industry: Optional[str],
    funding_stage: Optional[str],
    pitch_deck_url: Optional[str],
    parameters: Optional[Dict[str, Any]]
) -> Report:
    """
    Create a new report record with top-level fields and JSON parameters.
    """
    report = Report(
        title=title,
        user_id=user_id,
        startup_id=startup_id,
        report_type=report_type,
        founder_name=founder_name,
        founder_company=founder_company,
        company_name=company_name,
        company_type=company_type,
        industry=industry,
        funding_stage=funding_stage,
        pitch_deck_url=pitch_deck_url,
        status="pending",
        parameters=parameters or {}
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_by_id(db: Session, report_id: Union[str, uuid.UUID]) -> Optional[Report]:
    return db.query(Report).filter(Report.id == report_id).first()


def update_report_status(db: Session, report_id: Union[str, uuid.UUID], new_status: str) -> None:
    report = get_report_by_id(db, report_id)
    if report:
        report.status = new_status
        if new_status.lower() == "completed":
            report.completed_at = datetime.utcnow()
        db.commit()


def update_report_sections(db: Session, report_id: Union[str, uuid.UUID], sections_dict: Dict[str, str]) -> None:
    """
    Example: store AI-generated sections in the 'parameters' JSON 
    under a 'generated_sections' key.
    """
    report = get_report_by_id(db, report_id)
    if report:
        if not report.parameters:
            report.parameters = {}
        report.parameters["generated_sections"] = sections_dict
        db.commit()


def get_report_content(db: Session, report_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
    """
    Return any structured content from DB (like sections).
    In this example, we look for 'generated_sections' in the parameters.
    """
    report = get_report_by_id(db, report_id)
    if not report:
        return {}
    return report.parameters.get("generated_sections", {})
