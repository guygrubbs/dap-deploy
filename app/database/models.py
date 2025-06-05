import datetime
from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database.database import Base


class AnalysisRequest(Base):
    """
    ORM mapping for the Supabase table `analysis_requests`.

    This replaces the old `Report` model so the backend inserts into
    the correct table and avoids the foreign-key error.
    """
    __tablename__ = "analysis_requests"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        index=True,
    )

    # Supabase-auth user that submitted the request
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Always “Right Hand Operation”
    company_name = Column(String, nullable=False, default="Right Hand Operation")

    # Required requester details
    requestor_name = Column(String, nullable=False)
    email = Column(String, nullable=False)

    # Optional founder / company context
    founder_name = Column(String)
    industry = Column(String)
    funding_stage = Column(String)
    company_type = Column(String)

    # Stored in “Founder Company: …\n<extra>” format
    additional_info = Column(String)

    # Pitch-deck link or upload URL
    pitch_deck_url = Column(String)

    # Processing status: pending → processing → completed / failed
    status = Column(String, nullable=False, default="pending")

    # External workflow / API tracking ID
    external_request_id = Column(String)

    # Auto-timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    # Convenience JSON field if you need to stash extra payload
    parameters = Column(JSONB)

    def __repr__(self):
        return f"<AnalysisRequest id={self.id} user_id={self.user_id} status={self.status}>"
