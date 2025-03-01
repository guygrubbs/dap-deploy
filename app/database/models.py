from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database.database import Base  # Assumes Base is defined in database.py

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=True)
    startup_id = Column(String(50), nullable=True)
    report_type = Column(String(50), nullable=True)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # e.g., pending, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship to report sections.
    sections = relationship("ReportSection", back_populates="report", cascade="all, delete-orphan")

class ReportSection(Base):
    __tablename__ = "report_sections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=True)
    startup_id = Column(String(50), nullable=True)
    report_type = Column(String(50), nullable=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    section_name = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship back to the report.
    report = relationship("Report", back_populates="sections")
