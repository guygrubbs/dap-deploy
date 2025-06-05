# app/api/router.py
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

import requests
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

# ─────────── app imports ──────────────────────────────────────────────────────
from app.schemas.analysis_request import (        # NEW schemas
    AnalysisRequestIn,
    AnalysisRequestOut,
    ReportContentResponse,
    ReportSection,
    ReportStatusResponse,
)
from app.database.crud import (                   # NEW CRUD helpers
    create_analysis_request_entry,
    get_analysis_request_by_id,
    update_analysis_request_status,
    save_generated_sections,
    get_generated_sections,
)
from app.database.database import db_session      # ctx-manager version

from app.api.ai.orchestrator import generate_report           # unchanged
from app.storage.pdfgenerator import generate_pdf              # unchanged
from app.storage.gcs import finalize_report_with_pdf           # unchanged
from app.matching_engine.pdf_to_openai_jsonl import (          # unchanged
    extract_text_with_ocr,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# FastAPI dependency – yields a SQLAlchemy Session
def get_db():
    with db_session() as db:
        yield db


# ──────────────────────────────────────────────────────────────────────────────
#  1)  CREATE  (status = 'pending')
# ──────────────────────────────────────────────────────────────────────────────
@router.post(
    "/reports",
    response_model=AnalysisRequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new analysis request",
)
def create_report(
    payload: AnalysisRequestIn,
    db: Session = Depends(get_db),
) -> AnalysisRequestOut:
    """
    Insert a row into `analysis_requests`.  `company_name` is always
    “Right Hand Operation”; `additional_info` is formatted by the CRUD helper.
    """
    try:
        req = create_analysis_request_entry(db, **payload.dict())

        return AnalysisRequestOut(
            **req.__dict__,
            # Pydantic will serialise UUID & datetime to ISO strings automatically
        )
    except Exception as exc:
        logger.error("Error creating analysis request: %s", exc, exc_info=True)
        raise HTTPException(500, "Failed to create analysis request")


# ──────────────────────────────────────────────────────────────────────────────
#  2)  GENERATE FULL REPORT  (status -> completed)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/reports/{request_id}/generate", response_model=AnalysisRequestOut)
def generate_full_report(
    request_id: UUID4 = Path(..., description="UUID of the analysis request"),
    db: Session = Depends(get_db),
) -> AnalysisRequestOut:
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        raise HTTPException(404, "Analysis request not found")

    # --- 1. Update status -> processing -------------------------------------
    update_analysis_request_status(db, request_id, "processing")

    # --- 2. Gather/augment parameters ---------------------------------------
    params: Dict[str, Any] = (req.parameters or {}).copy()
    params.update(  # enrich with top-level columns
        dict(
            title="Founder Due Diligence Report",
            requestor_name=req.requestor_name,
            company=req.company_name,
            founder_company=req.additional_info.split("\n")[0].replace(
                "Founder Company: ", ""
            ),
            founder_name=req.founder_name or "",
            industry=req.industry or "",
            funding_stage=req.funding_stage or "",
            company_type=req.company_type or "",
            pitch_deck_url=req.pitch_deck_url or "",
            email=req.email,
        )
    )

    # If a pitch-deck URL exists, OCR it and add text
    if params["pitch_deck_url"]:
        try:
            pdf_bytes = requests.get(params["pitch_deck_url"], timeout=30).content
            params["pitch_deck_text"] = extract_text_with_ocr(pdf_bytes)
        except Exception as e:
            logger.warning("Could not fetch/parse pitch deck: %s", e)

    # --- 3. Call the AI orchestrator ----------------------------------------
    ai_sections: Dict[str, str] = generate_report(params)

    # --- 4. Persist generated sections --------------------------------------
    save_generated_sections(db, request_id, ai_sections)

    # --- 5. Mark completed ---------------------------------------------------
    update_analysis_request_status(db, request_id, "completed")

    # --- 6. Build PDF --------------------------------------------------------
    section_map = {
        "executive_summary_investment_rationale": "Section 1: Executive Summary",
        "market_opportunity_competitive_landscape": "Section 2: Market Opportunity",
        "financial_performance_investment_readiness": "Section 3: Financials",
        "go_to_market_strategy_customer_traction": "Section 4: GTM & Traction",
        "leadership_team": "Section 5: Leadership & Team",
        "investor_fit_exit_strategy_funding": "Section 6: Investor Fit & Exit",
        "final_recommendations_next_steps": "Section 7: Recommendations",
    }
    sections_for_pdf = [
        {"id": f"sec_{i}", "title": section_map.get(k, k), "content": v}
        for i, (k, v) in enumerate(ai_sections.items(), start=1)
    ]

    pdf_bytes = generate_pdf(
        report_id=req.id,
        report_title="Founder Due Diligence Report",
        tier2_sections=sections_for_pdf,
        founder_name=req.founder_name or "",
        founder_company=params["founder_company"],
        founder_type=req.company_type or "",
        output_path=None,
    )

    # --- 7. Upload PDF to storage & email user ------------------------------
    try:
        finalize_report_with_pdf(
            report_id=req.id,
            user_id=req.user_id,
            final_report_sections=sections_for_pdf,
            pdf_data=pdf_bytes,
            expiration_seconds=86_400,
            upload_to_supabase=True,
            user_email=req.email,
            requestor_name=req.requestor_name,
        )
    except Exception as e:
        logger.error("PDF upload/email failed: %s", e)

    # --- 8. Return updated row ----------------------------------------------
    updated = get_analysis_request_by_id(db, request_id)
    return AnalysisRequestOut(**updated.__dict__)


# ──────────────────────────────────────────────────────────────────────────────
#  3)  GET FULL ROW + SECTIONS
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/reports/{request_id}", response_model=AnalysisRequestOut)
def get_report(request_id: UUID4, db: Session = Depends(get_db)) -> AnalysisRequestOut:
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        raise HTTPException(404, "Analysis request not found")
    return AnalysisRequestOut(**req.__dict__)


# ──────────────────────────────────────────────────────────────────────────────
#  4)  GET JUST THE CONTENT SECTIONS
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/reports/{request_id}/content", response_model=ReportContentResponse)
def get_report_content_endpoint(
    request_id: UUID4, db: Session = Depends(get_db)
) -> ReportContentResponse:
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        raise HTTPException(404, "Analysis request not found")

    secs_raw = get_generated_sections(db, request_id)
    sections: List[ReportSection] = [
        ReportSection(id=f"sec_{i}", title=title, content=body, sub_sections=[])
        for i, (title, body) in enumerate(secs_raw.items(), start=1)
    ]

    return ReportContentResponse(
        url=req.parameters.get("pdf_url") if req.parameters else None,
        status=req.status,
        sections=sections,
    )


# ──────────────────────────────────────────────────────────────────────────────
#  5)  LIGHT-WEIGHT STATUS POLLING
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/reports/{request_id}/status", response_model=ReportStatusResponse)
def report_status(
    request_id: UUID4, db: Session = Depends(get_db)
) -> ReportStatusResponse:
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        raise HTTPException(404, "Analysis request not found")

    # crude progress heuristic
    progress = 100 if req.status == "completed" else 50
    return ReportStatusResponse(report_id=req.id, status=req.status, progress=progress)
