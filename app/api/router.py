import logging
import requests
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from sqlalchemy.orm import Session

# Import your CRUD functions and DB session from the respective modules
# Removed references to get_report_content since we no longer have a separate report_sections table
from app.database.crud import (
    create_report_request,  # renamed from create_report_entry
    get_report_request_by_id,  # renamed from get_report_by_id
    update_report_sections,
)
from app.database.database import SessionLocal

# We still import your schemas for response models
from app.api.schemas import (
    CreateReportRequest,
    ReportResponse,
    ReportStatusResponse,
    ReportContentResponse,
    ReportSection
)

# Orchestrator logic for local dev
from app.api.ai.orchestrator import generate_report

# PDF and GCS utilities
from app.storage.pdfgenerator import generate_pdf
from app.storage.gcs import finalize_report_with_pdf

# Optional: PDF -> JSONL -> OpenAI code
from app.matching_engine.pdf_to_openai_jsonl import (
    download_pdf_from_supabase,
    extract_text_with_ocr,
    create_jsonl_file,
    upload_jsonl_to_openai
)

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    """Dependency that provides a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------------
#  NEW POST ENDPOINT: /pitchdecks/{deck_file}/upload_to_openai
# -------------------------------------------------------------------------
class UploadToOpenAIRequest(BaseModel):
    """Optional body model for additional params (bucket, out_jsonl, etc.)."""
    bucket: Optional[str] = "pitchdecks"
    output_filename: Optional[str] = "pitchdeck_data.jsonl"
    upload_to_openai: Optional[bool] = True


@router.post("/pitchdecks/{deck_file}/upload_to_openai", summary="Convert a pitch deck to .jsonl and upload it to OpenAI.")
def upload_deck_to_openai(
    deck_file: str,
    request_body: UploadToOpenAIRequest = Body(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    1) Downloads a PDF pitch deck from Supabase (using 'deck_file' as the filename).
    2) Extracts text (fallback to OCR if needed).
    3) Creates a .jsonl file in memory or on disk.
    4) Optionally uploads that file to OpenAI with `purpose="fine-tune"`.
    5) Returns the OpenAI file ID if upload is successful, or an error if any step fails.
    """
    try:
        bucket = request_body.bucket or "pitchdecks"
        pdf_bytes = download_pdf_from_supabase(deck_file, bucket=bucket)
        logger.info(f"Downloaded PDF '{deck_file}' from Supabase bucket '{bucket}'")

        extracted_text = extract_text_with_ocr(pdf_bytes)
        if not extracted_text.strip():
            logger.warning("No text extracted from PDF; possibly empty or scanned images only.")

        out_jsonl_path = request_body.output_filename
        create_jsonl_file(extracted_text, out_jsonl_path)
        logger.info(f"Created JSONL file at: {out_jsonl_path}")

        openai_file_id = None
        if request_body.upload_to_openai:
            openai_file_id = upload_jsonl_to_openai(out_jsonl_path, purpose="fine-tune")
            logger.info(f"Uploaded JSONL to OpenAI; file_id={openai_file_id}")

        return {
            "deck_file": deck_file,
            "bucket": bucket,
            "jsonl_path": out_jsonl_path,
            "openai_file_id": openai_file_id
        }
    except Exception as e:
        logger.error("Error in /pitchdecks/{deck_file}/upload_to_openai endpoint: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload pitch deck to OpenAI: {e}")


# -------------------------------------------------------------------------
#  /reports endpoints
# -------------------------------------------------------------------------

@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new report request"
)
def create_report_request_endpoint(
    request: CreateReportRequest,
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Creates a new record in 'report_requests' (status='pending') with user parameters.
    This is typically the first step before calling the Edge Function 
    (trigger-report-generation) in your production flow.
    """
    try:
        new_req = create_report_request(
            db=db,
            title=request.title,
            user_id=request.user_id,
            startup_id=request.startup_id,
            report_type=request.report_type,
            parameters=request.parameters
        )

        return ReportResponse(
            id=new_req.id,
            title=new_req.title,
            status=new_req.status,  # likely 'pending'
            created_at=str(new_req.created_at) if new_req.created_at else None,
            updated_at=str(new_req.completed_at) if new_req.completed_at else None,
            progress=new_req.progress or 0,  # or None if you want
            startup_id=new_req.startup_id,
            user_id=new_req.user_id,
            report_type=new_req.report_type,
            parameters=new_req.parameters,
            sections=[],  # We can leave this empty, or you can cast new_req.sections if needed
            signed_pdf_download_url=None
        )

    except Exception as e:
        logger.error("Error creating report request: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create report request")


@router.post(
    "/reports/{report_id}/generate",
    summary="Local Dev Only: Generate the full report in one step (ignores payment, multi-step flow)",
    response_model=ReportResponse
)
def generate_local_report(
    report_id: str,  # Use 'str' if your 'report_requests.id' is a UUID
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    ========== WARNING (DEV ONLY) ==========
    This endpoint bypasses the multi-step asynchronous flow. It immediately:
      1) Calls generate_report(...) in Python
      2) Updates DB sections
      3) Generates a PDF locally
      4) Uploads to GCS & Supabase (via finalize_report_with_pdf)

    It does NOT call the Supabase Edge Function or the GCP external service,
    nor does it set 'payment_status' or multi-step statuses. 
    It also does not call 'report-webhook'.

    Use this ONLY for local/demo scenarios or quick testing.
    =======================================
    """
    # 1) Retrieve the record from 'report_requests'
    report_model = get_report_request_by_id(db, report_id)
    if not report_model:
        logger.warning("Report request with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # 2) Build local parameters
    request_params = {"local_generation": True}
    if report_model.parameters and isinstance(report_model.parameters, str):
        # If we previously stored a JSON string instead of JSONB
        try:
            parsed = json.loads(report_model.parameters)
            report_model.parameters = parsed
        except json.JSONDecodeError:
            report_model.parameters = None

    if isinstance(report_model.parameters, dict):
        request_params.update(report_model.parameters)

    # 3) Optionally fetch pitch deck from a URL
    pitch_deck_url = request_params.get("pitch_deck_url")
    if pitch_deck_url:
        logger.info("Downloading pitch deck for local dev from: %s", pitch_deck_url)
        try:
            resp = requests.get(pitch_deck_url, timeout=30)
            resp.raise_for_status()
            pdf_bytes = resp.content

            from app.matching_engine.pdf_to_openai_jsonl import extract_text_with_ocr
            pitch_deck_text = extract_text_with_ocr(pdf_bytes)
            request_params["pitch_deck_text"] = pitch_deck_text

        except Exception as e:
            logger.error("Error fetching pitch deck locally: %s", str(e), exc_info=True)
            raise HTTPException(status_code=400, detail=f"Failed to fetch pitch deck PDF: {str(e)}")

    # 4) Locally generate Tier-2 content
    logger.info("Locally generating Tier-2 content for request %s", report_id)
    full_result = generate_report(request_params)

    # 5) Update DB sections with full_result
    #    'full_result' is presumably a dict of { "section_name": "text", ... }
    update_report_sections(db, report_id, full_result)

    # 6) (DEV) not setting payment status or 'completed' status

    # 7) Prepare sections for PDF
    #    We'll assume full_result is a dict: { "executive_summary": "...", "market_opportunity": "..." }
    #    so we build a list for PDF generator
    sections_list = []
    for i, (key, content) in enumerate(full_result.items(), start=1):
        sections_list.append({
            "id": f"section_{i}",
            "title": key,
            "content": content
        })

    # 8) Generate PDF
    pdf_data = None
    try:
        logger.info("Generating PDF (local) for request %s", report_id)
        pdf_data = generate_pdf(
            report_id=report_model.id,  # If your 'id' is a UUID or string, adapt as needed
            report_title=report_model.title or "Local Dev Report",
            tier2_sections=sections_list,
            founder_name="DevUser",
            company_name=str(report_model.startup_id) or "Dev Startup",
            company_type="",
            company_description="",
            output_path=None
        )
    except Exception as e:
        logger.error("Error generating PDF locally for request %s: %s", report_id, str(e))

    # 9) Upload to GCS / Supabase if PDF is available
    if pdf_data:
        try:
            finalize_report_with_pdf(
                report_id=report_id,
                user_id=str(report_model.user_id) if report_model.user_id else "0",
                final_report_sections=sections_list,
                pdf_data=pdf_data,
                expiration_seconds=86400,
                upload_to_supabase=True
            )
        except Exception as e:
            logger.error("Error in finalize_report_with_pdf (local) for request %s: %s", report_id, str(e))

    # 10) Return final data
    updated = get_report_request_by_id(db, report_id)

    # Build a list of sections to return in the response
    final_sections_list = []
    if isinstance(updated.sections, dict):
        # If sections is a dict
        for i, (key, text) in enumerate(updated.sections.items(), start=1):
            final_sections_list.append(ReportSection(
                id=f"section_{i}",
                title=key,
                content=text,
                sub_sections=[]
            ))
    # If it's a list, you can adapt the iteration to match that structure

    return ReportResponse(
        id=updated.id,
        title=updated.title,
        status=updated.status,
        created_at=str(updated.created_at) if updated.created_at else None,
        updated_at=str(updated.completed_at) if updated.completed_at else None,
        progress=updated.progress or 0,
        startup_id=str(updated.startup_id),
        user_id=str(updated.user_id) if updated.user_id else None,
        report_type=updated.report_type,
        parameters=updated.parameters,
        sections=final_sections_list,
        # If you store a final PDF link in 'signed_pdf_download_url', pass it here
        signed_pdf_download_url=getattr(updated, "signed_pdf_download_url", None)
    )


@router.get("/reports/{report_id}", response_model=ReportResponse, summary="Get report metadata")
def get_report(report_id: str, db: Session = Depends(get_db)) -> ReportResponse:
    """
    Retrieves report details by ID from 'report_requests', including:
      - generation status
      - Tier 2 sections
      - PDF download URL if available

    We do NOT hardcode progress=50/100 anymore.
    If you want progress, read 'report_requests.progress'.
    """
    report_model = get_report_request_by_id(db, report_id)
    if not report_model:
        logger.warning("Report request with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # Build a list of sections from the JSONB if it's a dict
    sections_list = []
    if isinstance(report_model.sections, dict):
        for i, (key, text) in enumerate(report_model.sections.items(), start=1):
            sections_list.append(ReportSection(
                id=f"section_{i}",
                title=key,
                content=text,
                sub_sections=[]
            ))

    return ReportResponse(
        id=report_model.id,
        title=report_model.title,
        status=report_model.status,
        created_at=str(report_model.created_at) if report_model.created_at else None,
        updated_at=str(report_model.completed_at) if report_model.completed_at else None,
        progress=report_model.progress if report_model.progress is not None else 0,
        startup_id=str(report_model.startup_id),
        user_id=str(report_model.user_id) if report_model.user_id else None,
        report_type=report_model.report_type,
        parameters=report_model.parameters,
        sections=sections_list,
        signed_pdf_download_url=getattr(report_model, "signed_pdf_download_url", None)
    )


@router.get("/reports/{report_id}/content", response_model=ReportContentResponse, summary="Get report content")
def get_report_content_endpoint(report_id: str, db: Session = Depends(get_db)) -> ReportContentResponse:
    """
    Retrieves the 'sections' content for a given report from 'report_requests', plus
    a signed PDF URL if available.
    """
    report_model = get_report_request_by_id(db, report_id)
    if not report_model:
        raise HTTPException(status_code=404, detail="Report not found")

    sections_list = []
    if isinstance(report_model.sections, dict):
        for i, (key, text) in enumerate(report_model.sections.items(), start=1):
            sections_list.append(ReportSection(
                id=f"section_{i}",
                title=key,
                content=text,
                sub_sections=[]
            ))

    pdf_url = getattr(report_model, "signed_pdf_download_url", None)

    return ReportContentResponse(
        url=pdf_url,
        status=report_model.status,
        sections=sections_list
    )


@router.get("/reports/{report_id}/status", response_model=ReportStatusResponse, summary="Get report status and progress")
def report_status(report_id: str, db: Session = Depends(get_db)) -> ReportStatusResponse:
    """
    Returns the current status and progress of a report (from 'report_requests').
    For the multi-step approach, you can read 'report_requests.progress'.
    """
    report_model = get_report_request_by_id(db, report_id)
    if not report_model:
        logger.warning("Report request with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportStatusResponse(
        status=report_model.status,
        progress=report_model.progress or 0,
        report_id=report_model.id
    )
