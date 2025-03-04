# app/api/router.py

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# For demonstration, import the new schemas from your 'schemas.py'.
from app.api.schemas import (
    CreateReportRequest,
    ReportResponse,
    ReportStatusResponse,
    ReportContentResponse,
    ReportSection
)

# Import your CRUD functions and DB session from the respective modules
from app.database.crud import (
    create_report_entry,
    get_report_by_id,
    get_report_content,
    update_report_sections,
    update_report_status
)
from app.database.database import SessionLocal
from app.main import verify_token  # or wherever verify_token is defined

# Import orchestrator logic for generating the full report
from app.api.ai.orchestrator import generate_report

# Import your PDF and GCS utilities
from app.storage.pdfgenerator import generate_pdf
from app.storage.gcs import finalize_report_with_pdf

logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    """Dependency that provides a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new report request"
)
def create_report(
    request: CreateReportRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
) -> ReportResponse:
    """
    Creates a new report generation request using provided report parameters and user info.

    - **user_id**: ID of the user requesting the report.
    - **startup_id**: (Optional) ID of the startup associated with this report.
    - **report_type**: (Optional) Type of report (e.g., 'investment_readiness').
    - **title**: Title of the report.
    - **parameters**: Additional parameters for generating the report.
    """
    try:
        new_report = create_report_entry(
            db=db,
            title=request.title,
            user_id=request.user_id,
            startup_id=request.startup_id,
            report_type=request.report_type,
            parameters=request.parameters
        )

        # Example progress; adjust to your actual logic
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
            parameters=new_report.parameters,  # or None if your DB defaults differ
            sections=[],  # Newly created report typically has no sections yet
            signed_pdf_download_url=None
        )

    except Exception as e:
        logger.error("Error creating report: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to create report"
        )


@router.post(
    "/reports/{report_id}/generate",
    summary="Generate the full report (Tier-2 sections), create PDF, and upload to GCS",
    response_model=ReportResponse
)
def generate_full_report(
    report_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
) -> ReportResponse:
    """
    Triggers the full orchestrator-based generation for the given report,
    fills in the 7 sections, updates the DB with final content,
    then creates a PDF from those sections and uploads to GCS.
    """
    # 1) Retrieve existing report from DB
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("Report with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # 2) Prepare the request_params dict from the report data
    request_params = {
        "report_query": f"Full investment readiness for report_id={report_id}",
        "company": "{}",   # placeholders or actual data from DB
        "industry": "{}",
    }
    if report_model.parameters:
        # if parameters is JSON/dict, merge them
        request_params.update(report_model.parameters)

    logger.info("Generating full Tier-2 sections for report %s", report_id)
    full_result = generate_report(request_params)

    # 3) Store these sections in DB
    # The 'full_result' is a dict where each key is a section name
    # and each value is the generated text.
    update_report_sections(db, report_id, full_result)

    # 4) Mark the report as completed
    update_report_status(db, report_id, "completed")

    # 5) Build a list of sections for PDF output
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

    # 6) Generate the PDF in-memory
    pdf_data = None
    try:
        logger.info("Generating PDF for report %s", report_id)
        pdf_data = generate_pdf(
            report_id=report_model.id,
            report_title=report_model.title or "GFV Investment Report",
            tier2_sections=sections_list,
            output_path=None  # None -> returns PDF bytes in-memory
        )
        logger.info("PDF generated successfully for report %s", report_id)
    except Exception as e:
        logger.error("Error generating PDF for report %s: %s", report_id, str(e))

    # 7) If PDF generated successfully, upload to GCS and notify Supabase
    if pdf_data:
        try:
            from app.storage.gcs import finalize_report_with_pdf
            logger.info("Uploading PDF and notifying Supabase for report %s", report_id)
            # user_id can be included if your final logic needs it
            # e.g. 'report_model.user_id' or a known user
            finalize_report_with_pdf(
                report_id=report_id,
                user_id=report_model.user_id if report_model.user_id else 0,
                final_report_sections=sections_list,
                pdf_data=pdf_data,
                expiration_seconds=3600  # or your chosen duration
            )
        except Exception as e:
            logger.error("Error in finalize_report_with_pdf for report %s: %s", report_id, str(e))

    # 8) Build final response
    updated_report = get_report_by_id(db, report_id)
    progress_value = 100  # Example logic: we've completed generation

    # Reconstruct the final sections in the response
    # Now that we've stored them, fetch them from the DB to ensure consistency
    final_sections_list = []
    if updated_report.sections:
        for i, sec in enumerate(updated_report.sections, start=1):
            final_sections_list.append(ReportSection(
                id=f"section_{i}",
                title=sec.section_name or f"Section {i}",
                content=sec.content or "",
                sub_sections=[]
            ))

    # If we had a column for 'pdf_url' in the DB, we could fetch it here
    signed_pdf_download_url = getattr(updated_report, "pdf_url", None)

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
        sections=final_sections_list,
        signed_pdf_download_url=signed_pdf_download_url
    )


@router.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    summary="Get report metadata"
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
) -> ReportResponse:
    """
    Retrieves report details by report ID, including:
    - generation status
    - Tier 2 sections
    - signed PDF download URL if completed
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("Report with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # Convert sections (stored in DB) to a list of ReportSection if applicable
    sections_list = []
    if report_model.sections:
        for i, sec in enumerate(report_model.sections, start=1):
            sections_list.append(ReportSection(
                id=f"section_{i}",
                title=sec.section_name or f"Section {i}",
                content=sec.content or "",
                sub_sections=[]
            ))

    signed_pdf_download_url = getattr(report_model, "pdf_url", None)

    # Example progress logic
    progress = 100 if report_model.status.lower() == "completed" else 50

    return ReportResponse(
        id=report_model.id,
        title=report_model.title,
        status=report_model.status,
        created_at=str(report_model.created_at) if report_model.created_at else None,
        updated_at=str(report_model.completed_at) if report_model.completed_at else None,
        progress=progress,
        startup_id=getattr(report_model, "startup_id", None),
        user_id=getattr(report_model, "user_id", None),
        report_type=getattr(report_model, "report_type", None),
        parameters=getattr(report_model, "parameters", None),
        sections=sections_list,
        signed_pdf_download_url=signed_pdf_download_url
    )


@router.get(
    "/reports/{report_id}/content",
    response_model=ReportContentResponse,
    summary="Get report content"
)
def get_report_content_endpoint(
    report_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
) -> ReportContentResponse:
    """
    Retrieves the content details for a completed report,
    including Tier 2 sections and a signed PDF download URL if available.
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        raise HTTPException(status_code=404, detail="Report not found")

    sections_list = []
    if report_model.sections:
        for i, sec in enumerate(report_model.sections, start=1):
            sections_list.append(ReportSection(
                id=f"section_{i}",
                title=sec.section_name or f"Section {i}",
                content=sec.content or "",
                sub_sections=[]
            ))

    signed_pdf_download_url = getattr(report_model, "pdf_url", None)

    return ReportContentResponse(
        url=signed_pdf_download_url,
        status=report_model.status,
        sections=sections_list
    )


@router.get(
    "/reports/{report_id}/status",
    response_model=ReportStatusResponse,
    summary="Get report status and progress"
)
def report_status(
    report_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
) -> ReportStatusResponse:
    """
    Returns the current status and progress of a report generation.
    Allows clients to poll for generation progress.
    """
    report_model = get_report_by_id(db, report_id)
    if not report_model:
        logger.warning("Report with id %s not found", report_id)
        raise HTTPException(status_code=404, detail="Report not found")

    # Example progress logic
    progress_value = 100 if report_model.status.lower() == "completed" else 50

    return ReportStatusResponse(
        status=report_model.status,
        progress=progress_value,
        report_id=report_model.id
    )
