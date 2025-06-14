import os
import io
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Union

from google.cloud import storage
from google.cloud.exceptions import NotFound, Forbidden, GoogleCloudError

# Example import from your supabase notifier module:
from app.notifications.supabase_notifier import notify_supabase_final_report

# Upload to Supabase utility:
from app.storage.supabase_uploader import upload_pdf_to_supabase

logger = logging.getLogger(__name__)

def upload_pdf(report_id: Union[str, uuid.UUID], pdf_data: bytes) -> str:
    """
    Upload the generated PDF to Google Cloud Storage (GCS) in-memory
    (no temp file) and return the blob name.
    """
    bucket_name = os.getenv("REPORTS_BUCKET_NAME")
    if not bucket_name:
        logger.error("REPORTS_BUCKET_NAME environment variable is not set.")
        raise ValueError("REPORTS_BUCKET_NAME environment variable is not set.")

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        if not bucket.exists():
            logger.error("Bucket %s does not exist; cannot upload PDF.", bucket_name)
            raise NotFound(f"Bucket '{bucket_name}' not found.")

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        blob_name = f"reports/report_{report_id}_{timestamp}.pdf"
        blob = bucket.blob(blob_name)

        # Upload from an in-memory BytesIO buffer
        with io.BytesIO(pdf_data) as f:
            blob.upload_from_file(f, content_type="application/pdf")

        logger.info("Successfully uploaded PDF to GCS with blob name: %s", blob_name)
        return blob_name

    except (NotFound, Forbidden, GoogleCloudError) as gcs_err:
        logger.error("Error while uploading PDF to GCS: %s", str(gcs_err), exc_info=True)
        raise
    except Exception as e:
        logger.error("Unexpected error while uploading PDF: %s", str(e), exc_info=True)
        raise

def generate_signed_url(blob_name: str, expiration_seconds: int = 86400) -> str:
    """
    Generate a version 4 signed URL for a PDF in GCS,
    valid for `expiration_seconds` (default 1 day).
    """
    bucket_name = os.getenv("REPORTS_BUCKET_NAME")
    if not bucket_name:
        logger.error("REPORTS_BUCKET_NAME environment variable is not set.")
        raise ValueError("REPORTS_BUCKET_NAME environment variable is not set.")

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            logger.error("Bucket %s does not exist; cannot generate signed URL.", bucket_name)
            raise NotFound(f"Bucket '{bucket_name}' not found.")

        blob = bucket.blob(blob_name)

        signed_url = blob.generate_signed_url(
            expiration=timedelta(seconds=expiration_seconds),
            version="v4",
            method="GET",
        )

        logger.info("Signed URL generated successfully for blob: %s", blob_name)
        return signed_url

    except (NotFound, Forbidden, GoogleCloudError) as gcs_err:
        logger.error("Error while generating signed URL: %s", str(gcs_err), exc_info=True)
        raise
    except Exception as e:
        logger.error("Unexpected error while generating signed URL: %s", str(e), exc_info=True)
        raise

def finalize_report_with_pdf(
    report_id: Union[str, uuid.UUID],
    user_id: int,
    final_report_sections: list,
    pdf_data: bytes,
    expiration_seconds: int = 3600,
    upload_to_supabase: bool = True,
    create_signed_url: bool = False,
    user_email: Optional[str] = None,
    requestor_name: str = "there"
) -> dict:
    """
    1) Uploads a PDF to GCS (in-memory),
    2) Optionally generates a signed URL from GCS,
    3) Uploads the same PDF to Supabase (using a local temp file),
    4) Notifies Supabase that the final report is ready.

    If `user_email` is provided, it can be used to send an email with the PDF link.
    """
    try:
        # 1) Upload PDF to GCS
        blob_name = upload_pdf(report_id, pdf_data)

        # 2) (Optional) Generate a signed URL for the GCS file
        if create_signed_url:
            signed_url = generate_signed_url(blob_name, expiration_seconds=expiration_seconds)
        else:
            signed_url = "N/A"

        # 3) Prepare final report data payload (for notifications or future use)
        final_report_data = {
            "report_id": report_id,
            "status": "completed",
            "signed_pdf_download_url": signed_url,
            "sections": final_report_sections
        }

        # 4) Upload PDF to Supabase storage (if enabled)
        supabase_info = {}
        if upload_to_supabase:
            logger.info("Uploading PDF to Supabase for user_id=%s report_id=%s", user_id, report_id)
            temp_pdf_path = os.path.join(os.path.dirname(__file__), "temp_supabase_report.pdf")
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            with open(temp_pdf_path, "wb") as tmp_file:
                tmp_file.write(pdf_data)
            try:
                supabase_info = upload_pdf_to_supabase(
                    user_id=user_id,
                    report_id=report_id,
                    name=requestor_name,
                    pdf_file_path=temp_pdf_path,
                    user_email=user_email
                )
            finally:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
            final_report_data["supabase_storage_path"] = supabase_info.get("storage_path")
            final_report_data["supabase_public_url"] = supabase_info.get("public_url")

        # 5) Trigger Supabase notification (no-op for DB, but could email user)
        notify_supabase_final_report(report_id, final_report_data, user_id)
        logger.info("PDF upload complete and Supabase notification triggered for report %s", report_id)

        return supabase_info  # NEW: Return storage info (especially public_url) to caller

    except Exception as e:
        logger.error("Failed to finalize report %s with PDF: %s", report_id, str(e), exc_info=True)
        raise
