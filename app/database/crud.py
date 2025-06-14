from datetime import datetime
from typing import Any, Dict, Optional, Union

from pydantic import UUID4
from sqlalchemy.orm import Session

from app.database.models import AnalysisRequest

# NOTE: The create_analysis_request_entry function has been removed, since new 
# analysis requests are inserted on the front-end via Supabase (status 'pending').

# READ
def get_analysis_request_by_id(
    db: Session, request_id: Union[str, UUID4]
) -> Optional[AnalysisRequest]:
    """Return the analysis-request row or None."""
    return db.query(AnalysisRequest).filter(AnalysisRequest.id == request_id).first()

# UPDATE – status
def update_analysis_request_status(
    db: Session, request_id: Union[str, UUID4], new_status: str
) -> None:
    """
    Change `status` ('pending' → 'processing' → 'completed'/'failed') 
    and update the timestamp.
    """
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        return
    req.status = new_status
    req.updated_at = datetime.utcnow()
    db.commit()

# UPDATE – generated sections
def save_generated_sections(
    db: Session, request_id: Union[str, UUID4], sections: Dict[str, str]
) -> None:
    """Persist AI-generated sections into `parameters.generated_sections`."""
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        return
    if req.parameters is None:
        req.parameters = {}
    req.parameters["generated_sections"] = sections
    req.updated_at = datetime.utcnow()
    db.commit()

# READ – generated sections
def get_generated_sections(
    db: Session, request_id: Union[str, UUID4]
) -> Dict[str, Any]:
    """Retrieve whatever was saved by `save_generated_sections`."""
    req = get_analysis_request_by_id(db, request_id)
    if not req or not req.parameters:
        return {}
    return req.parameters.get("generated_sections", {})
