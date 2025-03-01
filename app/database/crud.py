from sqlalchemy.orm import Session
from datetime import datetime
from app.database.models import Report, ReportSection


def create_report_entry(db: Session, title: str) -> Report:
    """
    Create a new report entry in the database with status 'pending' 
    and return the Report instance.
    """
    new_report = Report(title=title, status="pending")
    db.add(new_report)
    try:
        db.commit()
        db.refresh(new_report)
        return new_report
    except Exception as e:
        db.rollback()
        raise e


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
    If the section already exists for this report, you could update 
    instead of creating a new row. For simplicity, we always create new here.
    """
    new_section = ReportSection(report_id=report_id, section_name=section_name, content=content)
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
    Retrieve and aggregate the content of each section for a given report as 
    { section_name: content }.
    """
    sections = db.query(ReportSection).filter(ReportSection.report_id == report_id).all()
    if not sections:
        return {}
    return {section.section_name: section.content for section in sections}
