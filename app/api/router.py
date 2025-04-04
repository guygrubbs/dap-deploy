# app/api/router.py

import logging
import requests
import uuid
from pydantic import UUID4
from fastapi import APIRouter, Depends, HTTPException, Path, status
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

# Schemas & DB logic
from app.api.schemas import (
    CreateReportRequest,
    ReportResponse,
    ReportStatusResponse,
    ReportContentResponse,
    ReportSection
)
from app.database.crud import (
    create_report_entry,
    get_report_by_id,
    get_report_content,
    update_report_sections,
    update_report_status
)
from app.database.database import SessionLocal

# AI orchestrator for generating multi-section text
from app.api.ai.orchestrator import generate_report

# PDF generation & storage finalization
from app.storage.pdfgenerator import generate_pdf
from app.storage.gcs import finalize_report_with_pdf

# Optional PDF -> JSONL -> OpenAI flow
from app.matching_engine.pdf_to_openai_jsonl import (
    download_pdf_from_supabase,
    extract_text_with_ocr,
    create_jsonl_file,
    upload_jsonl_to_openai
)

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    """
    Dependency to provide a SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------------------
# REPORT CREATION
# -------------------------------------------------------------------------

@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new report request"
)
def create_report(
    request: CreateReportRequest,
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Creates a new report generation request using the provided fields.
    """

    try:
        new_report = create_report_entry(
            db=db,
            title=request.title,
            user_id=request.user_id,
            startup_id=request.startup_id,
            report_type=request.report_type,
            founder_name=request.founder_name,
            founder_company=request.founder_company,
            company_name=request.company_name,
            company_type=request.company_type,
            industry=request.industry,
            funding_stage=request.funding_stage,
            pitch_deck_url=request.pitch_deck_url,
            parameters=request.parameters
        )

        progress = 0 if new_report.status.lower() != "completed" else 100

        return ReportResponse(
            # If `Report.id` is truly a UUID, 
            # schemas.py must have `id: UUID4` (or str).
            id=new_report.id,
            title=new_report.title,
            status=new_report.status,
            created_at=str(new_report.created_at) if new_report.created_at else None,
            updated_at=str(new_report.completed_at) if new_report.completed_at else None,
            progress=progress,
            startup_id=new_report.startup_id,
            user_id=new_report.user_id,
            report_type=new_report.report_type,
            parameters=new_report.parameters,
            sections=[],
            signed_pdf_download_url=None
        )
    except Exception as e:
        logger.error("Error creating report: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create report"
        )

# -------------------------------------------------------------------------
# REPORT GENERATION
# -------------------------------------------------------------------------

@router.post("/reports/{report_id}/generate", response_model=ReportResponse)
def generate_full_report(
    report_id: UUID4 = Path(..., description="UUID of the report"),
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Generates an AI-driven multi-section report, updates DB,
    creates a PDF, uploads it to storage, and returns the final data.
    """
    # 1) Retrieve existing report
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        raise HTTPException(status_code=404, detail="Report not found")

    # 2) Prepare orchestrator params
    request_params = {
        "report_query": f"Full investment readiness for report_id={report_id}",
        "company": "{}",
        "industry": "{}",
        "founder_name": report_model.founder_name or "",
        "founder_company": report_model.founder_company or "",
        "company_name": report_model.company_name or "",
        "company_type": report_model.company_type or "",
        "industry": report_model.industry or "",
        "funding_stage": report_model.funding_stage or "",
        "pitch_deck_url": report_model.pitch_deck_url or ""
    }

    # Merge leftover parameters (includes 'email' in request_params['email'])
    if report_model.parameters and isinstance(report_model.parameters, dict):
        request_params.update(report_model.parameters)

    # 3) Optional pitch deck processing
    pitch_deck_url = request_params.get("pitch_deck_url")
    if pitch_deck_url:
        try:
            resp = requests.get(pitch_deck_url, timeout=30)
            resp.raise_for_status()
            pdf_bytes = resp.content
            pitch_deck_text = extract_text_with_ocr(pdf_bytes)
            request_params["pitch_deck_text"] = pitch_deck_text
        except Exception as e:
            logger.error("Error reading pitch deck: %s", e)
            raise HTTPException(status_code=400, detail=f"Couldn't fetch pitch deck: {e}")

    # 4) Orchestrate AI generation
    full_result = generate_report(request_params)

    # 5) Update DB with AI-generated sections
    update_report_sections(db, report_id, full_result)

    # 6) Mark report as completed
    update_report_status(db, report_id, "completed")

    # 7) Prepare PDF sections
    section_id_map = {
        "executive_summary_investment_rationale": "Section 1: Executive Summary & Investment Rationale",
        "market_opportunity_competitive_landscape": "Section 2: Market Opportunity & Competitive Landscape",
        "financial_performance_investment_readiness": "Section 3: Financial Performance & Investment Readiness",
        "go_to_market_strategy_customer_traction": "Section 4: Go-To-Market (GTM) Strategy & Customer Traction",
        "leadership_team": "Section 5: Leadership & Team",
        "investor_fit_exit_strategy_funding": "Section 6: Investor Fit, Exit Strategy & Funding Narrative",
        "final_recommendations_next_steps": "Section 7: Final Recommendations & Next Steps"
    }

    sections_list = []
    i = 1
    for key, content in full_result.items():
        sections_list.append({
            "id": f"section_{i}",
            "title": section_id_map.get(key, key),
            "content": content
        })
        i += 1

    # 8) Generate the PDF in memory
    pdf_data = None
    try:
        pdf_data = generate_pdf(
            report_id=report_model.id,
            report_title=report_model.title or "GFV Investment Report",
            tier2_sections=sections_list,
            founder_name=report_model.founder_name or "",
            company_name=report_model.company_name or "",
            company_type=report_model.company_type or "",
            output_path=None
        )
    except Exception as e:
        logger.error("Error generating PDF for report %s: %s", report_id, str(e))

    # 9) Upload PDF & Email
    if pdf_data:
        try:
            # Pass the user's email from parameters (if present)
            user_email = request_params.get("email")  # e.g. request_params["email"]
            finalize_report_with_pdf(
                report_id=report_id,
                user_id=report_model.user_id if report_model.user_id else 0,
                final_report_sections=sections_list,
                pdf_data=pdf_data,
                expiration_seconds=86400,
                upload_to_supabase=True,
                user_email=user_email  # <--- important for email
            )
        except Exception as e:
            logger.error("Error uploading PDF: %s", str(e))

    # 10) Return final report
    updated_report = get_report_by_id(db, report_id)
    progress_value = 100

    final_sections = get_report_content(db, report_id)
    sections_list_api = []
    if isinstance(final_sections, dict):
        i = 1
        for k, v in final_sections.items():
            sections_list_api.append(
                ReportSection(
                    id=f"section_{i}",
                    title=section_id_map.get(k, k),
                    content=v or "",
                    sub_sections=[]
                )
            )
            i += 1

    return ReportResponse(
        id=updated_report.id,
        title=updated_report.title,
        status=updated_report.status,
        created_at=str(updated_report.created_at) if updated_report.created_at else None,
        updated_at=str(updated_report.completed_at) if updated_report.completed_at else None,
        progress=progress_value,
        startup_id=updated_report.startup_id,
        user_id=updated_report.user_id,
        report_type=updated_report.report_type,
        parameters=updated_report.parameters,
        sections=sections_list_api,
        signed_pdf_download_url=getattr(updated_report, "pdf_url", None)
    )

# -------------------------------------------------------------------------
# REPORT RETRIEVAL & STATUS
# -------------------------------------------------------------------------

@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: UUID4,  # Expect a UUID in the path
    db: Session = Depends(get_db)
) -> ReportResponse:
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        raise HTTPException(status_code=404, detail="Report not found")

    final_sections = get_report_content(db, report_id)
    section_id_map = {
        "executive_summary_investment_rationale": "Section 1",
        "market_opportunity_competitive_landscape": "Section 2",
        "financial_performance_investment_readiness": "Section 3",
        "go_to_market_strategy_customer_traction": "Section 4",
        "leadership_team": "Section 5",
        "investor_fit_exit_strategy_funding": "Section 6",
        "final_recommendations_next_steps": "Section 7"
    }

    sections_list = []
    if isinstance(final_sections, dict):
        i = 1
        for k, v in final_sections.items():
            sections_list.append(
                ReportSection(
                    id=f"section_{i}",
                    title=section_id_map.get(k, k),
                    content=v or "",
                    sub_sections=[]
                )
            )
            i += 1

    progress = 100 if report_model.status.lower() == "completed" else 50

    return ReportResponse(
        id=report_model.id,
        title=report_model.title,
        status=report_model.status,
        created_at=str(report_model.created_at) if report_model.created_at else None,
        updated_at=str(report_model.completed_at) if report_model.completed_at else None,
        progress=progress,
        startup_id=report_model.startup_id,
        user_id=report_model.user_id,
        report_type=report_model.report_type,
        parameters=report_model.parameters,
        sections=sections_list,
        signed_pdf_download_url=report_model.pdf_url
    )

@router.get("/reports/{report_id}/content", response_model=ReportContentResponse)
def get_report_content_endpoint(report_id: int, db: Session = Depends(get_db)) -> ReportContentResponse:
    """
    Retrieves the content details for a completed report, including sections & the PDF URL if any.
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        raise HTTPException(status_code=404, detail="Report not found")

    final_sections = get_report_content(db, report_id)
    sections_list = []
    if isinstance(final_sections, dict):
        i = 1
        for k, v in final_sections.items():
            sections_list.append(
                ReportSection(
                    id=f"section_{i}",
                    title=k,
                    content=v or "",
                    sub_sections=[]
                )
            )
            i += 1

    return ReportContentResponse(
        url=report_model.pdf_url,
        status=report_model.status,
        sections=sections_list
    )

@router.get("/reports/{report_id}/status", response_model=ReportStatusResponse)
def report_status(report_id: Union[str, uuid.UUID], db: Session = Depends(get_db)) -> ReportStatusResponse:
    """
    Returns the current status and approximate progress of a report generation.
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        raise HTTPException(status_code=404, detail="Report not found")

    progress_value = 100 if report_model.status.lower() == "completed" else 50

    return ReportStatusResponse(
        status=report_model.status,
        progress=progress_value,
        report_id=report_model.id
    )
