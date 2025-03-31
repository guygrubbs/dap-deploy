import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from app.database.database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    startup_id = Column(Integer, nullable=True)
    report_type = Column(String, nullable=True)
    title = Column(String, nullable=False)

    # New top-level fields
    founder_name = Column(String, nullable=True)
    founder_company = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    company_type = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    funding_stage = Column(String, nullable=True)
    pitch_deck_url = Column(String, nullable=True)

    # JSON field for extra data or sections
    parameters = Column(JSONB, nullable=True)

    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    pdf_url = Column(String, nullable=True)
