# app/api/router.py

import logging
import requests
import json
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel
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

# Tools for pitch deck -> JSONL -> OpenAI (optional usage)
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
#  Example Endpoint: Upload a Pitch Deck PDF, Convert, (Optionally) Upload
# -------------------------------------------------------------------------
class UploadToOpenAIRequest(BaseModel):
    """
    Payload for POST /pitchdecks/{deck_file}/upload_to_openai
    """
    bucket: Optional[str] = "pitchdecks"
    output_filename: Optional[str] = "pitchdeck_data.jsonl"
    upload_to_openai: Optional[bool] = True

@router.post("/pitchdecks/{deck_file}/upload_to_openai")
def upload_deck_to_openai(
    deck_file: str,
    request_body: UploadToOpenAIRequest = Body(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    1) Download a PDF pitch deck from Supabase (using 'deck_file' as filename).
    2) Extract text with OCR fallback.
    3) Create a .jsonl file from that text.
    4) Optionally upload it to OpenAI.
    5) Return relevant info (OpenAI file ID, etc.).
    """
    try:
        # 1) Download from Supabase
        bucket = request_body.bucket or "pitchdecks"
        pdf_bytes = download_pdf_from_supabase(deck_file, bucket=bucket)
        logger.info("Downloaded PDF '%s' from bucket '%s'", deck_file, bucket)

        # 2) Extract text
        extracted_text = extract_text_with_ocr(pdf_bytes)

        # 3) Create JSONL locally
        out_jsonl_path = request_body.output_filename
        create_jsonl_file(extracted_text, out_jsonl_path)
        logger.info("Created JSONL: %s", out_jsonl_path)

        # 4) Optionally upload to OpenAI
        openai_file_id = None
        if request_body.upload_to_openai:
            openai_file_id = upload_jsonl_to_openai(out_jsonl_path, purpose="fine-tune")
            logger.info("Uploaded JSONL to OpenAI: file_id=%s", openai_file_id)

        # 5) Return
        return {
            "deck_file": deck_file,
            "bucket": bucket,
            "jsonl_path": out_jsonl_path,
            "openai_file_id": openai_file_id
        }
    except Exception as e:
        logger.error("Error in upload_deck_to_openai: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload pitch deck: {e}")


# -------------------------------------------------------------------------
#  REPORT ENDPOINTS
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
    This includes top-level data (title, founder_name, etc.) plus 'parameters' dict.
    """
    try:
        new_report = create_report_entry(
            db=db,
            title=request.title,
            user_id=request.user_id,
            startup_id=request.startup_id,
            report_type=request.report_type,

            # Additional fields from the request
            founder_name=request.founder_name,
            founder_company=request.founder_company,
            company_name=request.company_name,
            company_type=request.company_type,
            industry=request.industry,
            funding_stage=request.funding_stage,
            pitch_deck_url=request.pitch_deck_url,

            # JSON/dict of arbitrary extras
            parameters=request.parameters
        )

        # If not completed, progress = 0
        progress = 0 if new_report.status.lower() != "completed" else 100

        return ReportResponse(
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
            sections=[],  # Not generated yet
            signed_pdf_download_url=None
        )
    except Exception as e:
        logger.error("Error creating report: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create report"
        )


@router.post(
    "/reports/{report_id}/generate",
    summary="Generate the full AI-based report, create PDF, and upload",
    response_model=ReportResponse
)
def generate_full_report(
    report_id: int,
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Generates an AI-driven multi-section report, updates DB,
    creates a PDF, uploads it to storage, and returns the final data.
    """
    # 1) Get existing report
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("Report with id %s not found.", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # 2) Prepare orchestrator params
    request_params = {
        "report_query": f"Full investment readiness for report_id={report_id}",
        # minimal placeholders
        "company": "{}",
        "industry": "{}",
    }

    # Integrate new top-level fields
    request_params["founder_name"] = report_model.founder_name or ""
    request_params["founder_company"] = report_model.founder_company or ""
    request_params["company_name"] = report_model.company_name or ""
    request_params["company_type"] = report_model.company_type or ""
    request_params["industry"] = report_model.industry or ""
    request_params["funding_stage"] = report_model.funding_stage or ""
    request_params["pitch_deck_url"] = report_model.pitch_deck_url or ""

    # (New) if you want to pass "company_description" or "prepared_by"
    request_params["company_description"] = report_model.company_description or ""
    request_params["prepared_by"] = getattr(report_model, "prepared_by", "") or "Shweta Mokashi, Right Hand Operation"

    # Merge leftover "parameters"
    if report_model.parameters and isinstance(report_model.parameters, dict):
        request_params.update(report_model.parameters)

    # 3) If pitch_deck_url is present, attempt download + text extraction
    pitch_deck_url = request_params.get("pitch_deck_url")
    if pitch_deck_url:
        try:
            resp = requests.get(pitch_deck_url, timeout=30)
            resp.raise_for_status()
            pdf_bytes = resp.content
            pitch_deck_text = extract_text_with_ocr(pdf_bytes)
            request_params["pitch_deck_text"] = pitch_deck_text
        except Exception as e:
            logger.error("Error fetching pitch deck from %s: %s", pitch_deck_url, str(e), exc_info=True)
            raise HTTPException(status_code=400, detail=f"Couldn't fetch pitch deck: {e}")

    # 4) Orchestrate AI generation
    full_result = generate_report(request_params)  # returns {section_key: "AI text"...}

    # 5) Update DB with generated sections
    update_report_sections(db, report_id, full_result)

    # 6) Mark status completed
    update_report_status(db, report_id, "completed")

    # 7) Build a sections list for PDF
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

    # 8) Generate PDF in-memory
    pdf_data = None
    try:
        pdf_data = generate_pdf(
            report_id=report_model.id,
            report_title=report_model.title or "GFV Investment Report",
            tier2_sections=sections_list,

            founder_name=report_model.founder_name or "",
            company_name=report_model.company_name or "",
            company_type=report_model.company_type or "",
            company_description=request_params.get("company_description", ""),
            prepared_by=request_params.get("prepared_by", "Shweta Mokashi, Right Hand Operation"),
            output_path=None
        )
        logger.info("PDF generated for report_id=%s successfully.", report_id)
    except Exception as e:
        logger.error("Error generating PDF for report_id=%s: %s", report_id, str(e), exc_info=True)

    # 9) Upload PDF if available
    if pdf_data:
        try:
            finalize_report_with_pdf(
                report_id=report_id,
                user_id=report_model.user_id if report_model.user_id else 0,
                final_report_sections=sections_list,
                pdf_data=pdf_data,
                expiration_seconds=86400,
                upload_to_supabase=True
            )
        except Exception as e:
            logger.error("Error uploading PDF for report_id=%s: %s", report_id, str(e), exc_info=True)

    # 10) Return the updated ReportResponse
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


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Retrieves report details by ID, including status, generated sections, and PDF URL if available.
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("No report found with id=%s", report_id)
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
def get_report_content_endpoint(
    report_id: int,
    db: Session = Depends(get_db)
) -> ReportContentResponse:
    """
    Retrieves the content details for a completed report, including sections & the PDF download URL if any.
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("No report found with id=%s", report_id)
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
def report_status(
    report_id: int,
    db: Session = Depends(get_db)
) -> ReportStatusResponse:
    """
    Returns the current status and approximate progress of a report generation.
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("No report found with id=%s", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    progress_value = 100 if report_model.status.lower() == "completed" else 50

    return ReportStatusResponse(
        status=report_model.status,
        progress=progress_value,
        report_id=report_model.id
    )
