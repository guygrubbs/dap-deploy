from sqlalchemy.orm import Session
from datetime import datetime
from app.database.models import Report, ReportSection

def create_report_entry(db: Session, title: str) -> Report:
    """
    Create a new report entry in the database with status 'pending' and return the Report instance.
    
    Args:
        db (Session): Database session.
        title (str): Title or name for the report.
    
    Returns:
        Report: The newly created report instance.
    
    Raises:
        Exception: Propagates any error encountered during the transaction.
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
    Update the status of a report. If setting status to 'complete', update the completed_at timestamp.
    
    Args:
        db (Session): Database session.
        report_id (int): Identifier of the report to update.
        new_status (str): New status to set (e.g., "pending", "complete", "failed").
    
    Returns:
        Report: The updated report instance.
    
    Raises:
        ValueError: If the report with the specified ID is not found.
        Exception: Propagates any error encountered during the transaction.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise ValueError("Report not found")
    
    report.status = new_status
    if new_status.lower() == "complete":
        report.completed_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(report)
        return report
    except Exception as e:
        db.rollback()
        raise e

def save_section(db: Session, report_id: int, section_name: str, content: str):
    """
    Save a report section in the database under the given report ID.
    
    Args:
        db (Session): Database session.
        report_id (int): Identifier of the report to which the section belongs.
        section_name (str): Name of the section (e.g., "Executive Summary").
        content (str): Generated content of the section.
    
    Returns:
        ReportSection: The newly created report section instance.
    
    Raises:
        Exception: Propagates any error encountered during the transaction.
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
    
    Args:
        db (Session): Database session.
        report_id (int): Identifier of the report.
    
    Returns:
        Report: The report instance if found; otherwise, None.
    """
    return db.query(Report).filter(Report.id == report_id).first()

def get_report_content(db: Session, report_id: int) -> dict:
    """
    Retrieve and aggregate the content of each section for a given report.
    
    Args:
        db (Session): Database session.
        report_id (int): Identifier of the report.
    
    Returns:
        dict: A dictionary with section names as keys and their content as values.
    """
    sections = db.query(ReportSection).filter(ReportSection.report_id == report_id).all()
    if not sections:
        return {}
    return {section.section_name: section.content for section in sections}
