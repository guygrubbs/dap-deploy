import datetime
from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database.database import Base
class Report(Base):
    __tablename__ = "reports"

    # UUID primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),  # If using pgcrypto or extension
        index=True
    )

    user_id = Column(UUID(as_uuid=True), index=True)  # or Integer if your user_id is an integer
    startup_id = Column(UUID(as_uuid=True), nullable=True)  # or int if you prefer
    report_type = Column(String, nullable=True)
    title = Column(String, nullable=False)
    requestor_name = Column(String, nullable=False)

    founder_name = Column(String, nullable=True)
    founder_company = Column(String, nullable=True)
    founder_type = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    funding_stage = Column(String, nullable=True)
    pitch_deck_url = Column(String, nullable=True)

    parameters = Column(JSONB, nullable=True)

    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    pdf_url = Column(String, nullable=True)
