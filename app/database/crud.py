from sqlalchemy.orm import Session
from datetime import datetime
import json
from typing import Dict

from app.database.models import Report, ReportSection

def create_report_entry(
    db: Session,
    title: str,
    user_id: str,
    startup_id: str,
    report_type: str,
    parameters: dict
) -> Report:
    # parameters_str = json.dumps(parameters) if parameters else None

    new_report = Report(
        title=title,
        status="pending",
        user_id=user_id,
        startup_id=startup_id,
        report_type=report_type,
        parameters=parameters
    )
    db.add(new_report)
    try:
        db.commit()
        db.refresh(new_report)
        return new_report
    except:
        db.rollback()
        raise

def update_report_status(db: Session, report_id: int, new_status: str) -> Report:
    """
    Update the status of a report. If setting status to 'completed', update completed_at timestamp.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise ValueError("Report not found")

    report.status = new_status
    if new_status.lower() == "completed":
        report.completed_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(report)
        return report
    except Exception as e:
        db.rollback()
        raise e

def save_section(db: Session, report_id: int, section_name: str, content: str) -> ReportSection:
    """
    Save or update a specific report section in the database.
    """
    new_section = ReportSection(
        report_id=report_id,
        section_name=section_name,
        content=content
    )
    db.add(new_section)
    try:
        db.commit()
        db.refresh(new_section)
        return new_section
    except Exception as e:
        db.rollback()
        raise e

def get_report_by_id(db: Session, report_id: int) -> Report:
    """
    Retrieve a report from the database by its ID.
    """
    return db.query(Report).filter(Report.id == report_id).first()

def get_report_content(db: Session, report_id: int) -> dict:
    """
    Retrieve and aggregate the content of each section for a given report as {section_name: content}.
    """
    sections = db.query(ReportSection).filter(ReportSection.report_id == report_id).all()
    if not sections:
        return {}
    return {section.section_name: section.content for section in sections}

def update_pdf_url(db: Session, report_id: int, pdf_url: str) -> Report:
    """
    If you need to update pdf_url after report generation, call this.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise ValueError("Report not found")
    report.pdf_url = pdf_url

    try:
        db.commit()
        db.refresh(report)
        return report
    except Exception as e:
        db.rollback()
        raise e

# -------------------------------
# Missing function for storing multi-section results:
# -------------------------------
def update_report_sections(db: Session, report_id: int, sections_dict: Dict[str, str]):
    """
    Takes a dictionary like:
      {
        "executive_summary_investment_rationale": "...section text...",
        "market_opportunity_competitive_landscape": "...section text...",
        ...
      }
    and saves/updates each one into the 'report_sections' table 
    for the given report_id.

    Adjust logic if you want to only create new or always overwrite existing.
    """
    for section_key, content in sections_dict.items():
        # Optional: check if we have an existing section row or not
        existing_section = db.query(ReportSection).filter(
            ReportSection.report_id == report_id,
            ReportSection.section_name == section_key
        ).first()

        if existing_section:
            # Overwrite content if you want to update in place
            existing_section.content = content
        else:
            # Create a new row
            new_section = ReportSection(
                report_id=report_id,
                section_name=section_key,
                content=content
            )
            db.add(new_section)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
