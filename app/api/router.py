from __future__ import annotations

import logging
import uuid
import time                            # NEW: for deal_id timestamp
from datetime import datetime
from typing import Dict, Any, List

import requests
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

# ─────────── app imports ──────────────────────────────────────────────────────
# REMOVED: AnalysisRequestIn import (no longer used, as front-end inserts directly)
from schemas import (
    AnalysisRequestOut,
    ReportContentResponse,
    ReportSection,
    ReportStatusResponse,
)
from app.database.crud import (
    get_analysis_request_by_id,
    update_analysis_request_status,
    save_generated_sections,    
    get_generated_sections,
)
from app.database.database import db_session
from app.api.ai.orchestrator import generate_report
from app.storage.pdfgenerator import generate_pdf
from app.storage.gcs import finalize_report_with_pdf
from app.notifications.supabase_notifier import supabase    # NEW: Supabase client for DB inserts
from app.matching_engine.pdf_to_openai_jsonl import (          # unchanged
    extract_text_with_ocr,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency – yields a SQLAlchemy Session
def get_db():
    with db_session() as db:
        yield db

# ──────────────────────────────────────────────────────────────────────────────
#  1)  [REMOVED] CREATE (initial insert now handled by front-end via Supabase)
# ──────────────────────────────────────────────────────────────────────────────
# The POST /api/reports endpoint has been removed, since the front-end directly
# inserts a 'pending' analysis_request row into the database (Supabase):contentReference[oaicite:0]{index=0}.

# ──────────────────────────────────────────────────────────────────────────────
#  2)  GENERATE FULL REPORT  (status: pending -> processing -> completed/failed)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/reports/{request_id}/generate", response_model=AnalysisRequestOut)
def generate_full_report(
    request_id: UUID4 = Path(..., description="UUID of the analysis request to process"),
    db: Session = Depends(get_db),
) -> AnalysisRequestOut:
    # Lookup the existing analysis request (which should have status 'pending')
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Analysis request not found")

    try:
        # 1. Update status to 'processing'
        update_analysis_request_status(db, request_id, "processing")  # triggers real-time update

        # 2. Prepare parameters for AI generation (merge form inputs and defaults)
        params: Dict[str, Any] = (req.parameters or {}).copy()
        # Extract founder company from additional_info (prefix "Founder Company: ")
        founder_co = ""
        if req.additional_info:
            founder_co = req.additional_info.split("\n")[0].replace("Founder Company:", "").strip()
        founder_co = founder_co or "Unknown Company"

        # Build the report title dynamically to include founder name & company:contentReference[oaicite:1]{index=1}
        title_str = f"Founder Due Diligence Report for "
        title_str += f"{req.founder_name + ' - ' if req.founder_name else ''}{founder_co or 'Startup'}"
        params.update({
            "title": title_str,
            "requestor_name": req.requestor_name,
            "company": req.company_name,
            "founder_company": founder_co,
            "founder_name": req.founder_name or "",
            "industry": req.industry or "",
            "funding_stage": req.funding_stage or "",
            "company_type": req.company_type or "",
            "pitch_deck_url": req.pitch_deck_url or "",
            "email": req.email,
        })

        # If a pitch deck URL is provided, fetch and OCR its text to include in prompts
        if params["pitch_deck_url"]:
            try:
                pdf_data = requests.get(params["pitch_deck_url"], timeout=30).content
                params["pitch_deck_text"] = extract_text_with_ocr(pdf_data)
            except Exception as e:
                logger.warning("Could not fetch/parse pitch deck PDF: %s", e)

        # 3. Generate report sections using AI orchestrator
        ai_sections: Dict[str, str] = generate_report(params)

        # 4. Save generated sections into the request record (parameters.generated_sections)
        save_generated_sections(db, request_id, ai_sections)

        # 5. Build PDF from the generated sections
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
            {"id": f"sec_{i}", "title": section_map.get(key, key), "content": body}
            for i, (key, body) in enumerate(ai_sections.items(), start=1)
        ]
        pdf_bytes = generate_pdf(
            report_id=req.id,
            report_title=title_str,
            tier2_sections=sections_for_pdf,
            founder_name=req.founder_name or "",
            founder_company=founder_co,
            founder_type=req.company_type or "",
            output_path=None,
        )

        # 6. Upload PDF to storage and send notification email (returns public URL info)
        supabase_info = finalize_report_with_pdf(
            report_id=req.id,
            user_id=req.user_id,
            final_report_sections=sections_for_pdf,
            pdf_data=pdf_bytes,
            expiration_seconds=86_400,
            upload_to_supabase=True,
            user_email=req.email,
            requestor_name=req.requestor_name,
        )
        # finalize_report_with_pdf is now modified to return a dict with storage info (public_url, etc.)

        # 7. Mark request as completed and record external ID & PDF link in the database
        updated_req = get_analysis_request_by_id(db, request_id)
        if not updated_req:
            # In theory, updated_req should exist; this check is just a safety.
            raise Exception("Request record vanished before completion update")
        updated_req.status = "completed"
        updated_req.external_request_id = str(req.id)  # use the same ID as external reference:contentReference[oaicite:2]{index=2}
        if updated_req.parameters is None:
            updated_req.parameters = {}
        updated_req.parameters["pdf_url"] = supabase_info.get("public_url") or ""
        updated_req.updated_at = datetime.utcnow()
        db.commit()  # commit all the above changes

        # 8. Create a new internal deal entry and a summary placeholder
        deal_id = f"deal_{int(time.time())}_{uuid.uuid4().hex[:8]}"  # unique deal identifier
        try:
            # Insert into deal_reports (PDF link initially included, since we have it now)
            supabase.table("deal_reports").insert({
                "deal_id": deal_id,
                "company_name": founder_co or "Unknown Company",
                "pdf_url": supabase_info.get("public_url") or None,
                "pdf_file_path": supabase_info.get("storage_path") or None
            }).execute()
        except Exception as e:
            logger.error("Error saving deal report record: %s", e, exc_info=True)
        try:
            # Insert into deal_report_summaries with placeholder content:contentReference[oaicite:3]{index=3}:contentReference[oaicite:4]{index=4}
            supabase.table("deal_report_summaries").insert({
                "deal_id": deal_id,
                "company_name": founder_co or "Unknown Company",
                "executive_summary": f"Analysis report submitted to external API with ID: {req.id}. Report generation is in progress.",
                "strategic_recommendations": "Report generation in progress via external API",
                "market_analysis": "Analysis pending via external API service",
                "financial_overview": "Financial analysis pending",
                "competitive_landscape": "Competitive analysis pending",
                "action_plan": "Action plan to be generated",
                "investment_readiness": "pending",
                "key_metrics": {"external_report_id": str(req.id), "api_status": "submitted"},
                "financial_projections": {"status": "pending", "external_report_id": str(req.id)}
            }).execute()
        except Exception as e:
            logger.error("Error saving report summary placeholder: %s", e, exc_info=True)

        # At this point, the analysis request is completed and the PDF URL is stored:contentReference[oaicite:5]{index=5}.
        # The front-end can retrieve the PDF via GET /api/reports/{id}/content or directly from deal_reports.

        return AnalysisRequestOut(**updated_req.__dict__)

    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        # Mark the request as failed in the database:contentReference[oaicite:6]{index=6}
        update_analysis_request_status(db, request_id, "failed")
        raise HTTPException(status_code=500, detail="Report generation failed")

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
#  4)  GET JUST THE CONTENT SECTIONS (and PDF URL)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/reports/{request_id}/content", response_model=ReportContentResponse)
def get_report_content_endpoint(request_id: UUID4, db: Session = Depends(get_db)) -> ReportContentResponse:
    req = get_analysis_request_by_id(db, request_id)
    if not req:
        raise HTTPException(404, "Analysis request not found")

    secs_raw = get_generated_sections(db, request_id)
    sections: List[ReportSection] = [
        ReportSection(id=f"sec_{i}", title=title, content=body, sub_sections=[])
        for i, (title, body) in enumerate(secs_raw.items(), start=1)
    ]

    return ReportContentResponse(
        status=req.status,
        url=req.parameters.get("pdf_url") if req.parameters else None,   # returns the public PDF link:contentReference[oaicite:7]{index=7}
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
