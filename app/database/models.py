from sqlalchemy import Column, Text, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ReportRequest(Base):
    """
    SQLAlchemy model for the `report_requests` table
    in Supabase, mirroring its schema.
    """
    __tablename__ = "report_requests"

    # MATCHING THE TABLE SCHEMA EXACTLY:
    # id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    report_url = Column(Text, nullable=True)
    payment_status = Column(Text, nullable=False, server_default="not_required")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    tier = Column(Text, nullable=False, server_default="tier_1")
    status = Column(Text, nullable=False, server_default="pending")
    
    # startup_id is also a UUID
    startup_id = Column(UUID(as_uuid=True), nullable=False)
    
    description = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    report_type = Column(Text, nullable=True)
    
    # JSONB default '[]'
    sections = Column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb")  # or default=list
    )
    
    # progress integer default 0
    progress = Column(Integer, nullable=False, server_default=text("0"))
    
    signed_pdf_download_url = Column(Text, nullable=True)
    
    parameters = Column(JSONB, nullable=True)
    
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    deleted = Column(Boolean, nullable=False, server_default=text("false"))
    
    external_id = Column(Text, nullable=True)
    
    storage_path = Column(Text, nullable=True)
