"""
CRUD helpers for the analysis-request pipeline.

All writes now target `analysis_requests`—the table that exists in
Supabase—so we never touch the old `reports` table (and thus avoid the
foreign-key constraint that caused 500 errors).
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

from pydantic import UUID4
from sqlalchemy.orm import Session

from app.database.models import AnalysisRequest


# ────────────────────────────────────────────────────────────────────────────────
# CREATE
# ────────────────────────────────────────────────────────────────────────────────
def create_analysis_request_entry(
    db: Session,
    *,
    user_id: UUID4,
    requestor_name: str,
    email: str,
    founder_company: str,
    founder_name: Optional[str] = None,
    industry: Optional[str] = None,
    funding_stage: Optional[str] = None,
    company_type: Optional[str] = None,
    pitch_deck_url: Optional[str] = None,
    additional_info: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> AnalysisRequest:
    """
    Insert a new row into `analysis_requests`.

    `company_name` is hard-coded to "Right Hand Operation".
    `additional_info` is stored as:

        "Founder Company: <founder_company>\\n<additional_info>"
    """
    full_additional = f"Founder Company: {founder_company}\n{additional_info or ''}"

    req = AnalysisRequest(
        user_id=user_id,
        company_name="Right Hand Operation",
        requestor_name=requestor_name,
        email=email,
        founder_name=founder_name,
        industry=industry,
        funding_stage=funding_stage,
        company_type=company_type,
        pitch_deck_url=pitch_deck_url,
        additional_info=full_additional,
        status="pending",
        parameters=parameters or {},
    )

    db.add(req)
    db.commit()
    db.refresh(req)
    return req


# ────────────────────────────────────────────────────────────────────────────────
# READ
# ────────────────────────────────────────────────────────────────────────────────
def get_analysis_request_by_id(
    db: Session, request_id: Union[str, uuid.UUID]
) -> Optional[AnalysisRequest]:
    """Return the analysis-request row or None."""
    return db.query(AnalysisRequest).filter(AnalysisRequest.id == request_id).first()


# ────────────────────────────────────────────────────────────────────────────────
# UPDATE – status
# ────────────────────────────────────────────────────────────────────────────────
def update_analysis_request_status(
    db: Session, request_id: Union[str, uuid.UUID], new_status: str
) -> None:
    """
    Change `status` ('pending' → 'processing' → 'completed'/'failed') and
    update the timestamp.  If status == 'completed', also set `updated_at`.
    """
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        return

    req.status = new_status
    req.updated_at = datetime.utcnow()

    db.commit()


# ────────────────────────────────────────────────────────────────────────────────
# UPDATE – generated sections (optional helper)
# ────────────────────────────────────────────────────────────────────────────────
def save_generated_sections(
    db: Session, request_id: Union[str, uuid.UUID], sections: Dict[str, str]
) -> None:
    """
    Persist AI-generated sections into `parameters.generated_sections`.
    """
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        return

    if req.parameters is None:
        req.parameters = {}

    req.parameters["generated_sections"] = sections
    req.updated_at = datetime.utcnow()
    db.commit()


# ────────────────────────────────────────────────────────────────────────────────
# READ – generated sections (optional helper)
# ────────────────────────────────────────────────────────────────────────────────
def get_generated_sections(
    db: Session, request_id: Union[str, uuid.UUID]
) -> Dict[str, Any]:
    """
    Convenience getter for whatever was previously saved by
    `save_generated_sections`.
    """
    req = get_analysis_request_by_id(db, request_id)
    if not req or not req.parameters:
        return {}

    return req.parameters.get("generated_sections", {})
