# app/storage/supabase_uploader.py
import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase URL or Service Role Key is not set. Supabase uploads will fail.")

# Initialize Supabase client if credentials exist
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_pdf_to_supabase(
    user_id: int,
    report_id: int,
    pdf_file_path: str,
    table_name: str = "report_requests"
) -> dict:
    """
    Uploads a local PDF file to the 'report_pdfs' bucket in Supabase Storage
    under '{user_id}/{report_id}.pdf'.
    
    Then updates the 'report_requests' table with 'storage_path' and
    a public URL. Returns a dict with:
      {
        "storage_path": <str>,
        "public_url": <str>
      }
    """
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check environment variables.")

    storage_path = f"{user_id}/{report_id}.pdf"
    try:
        # Upload using the file path (storage3 will open it in "rb" mode internally)
        result = supabase.storage.from_("report_pdfs").upload(
            path=storage_path,
            file=pdf_file_path,  # pass the path (str, Path)
            file_options={"content-type": "application/pdf"}
        )

        # Check for upload errors
        if result.get("error"):
            err_msg = result["error"].get("message", "Unknown error")
            raise ValueError(f"Error uploading PDF to Supabase: {err_msg}")

        # Get public URL
        public_url_data = supabase.storage.from_("report_pdfs").get_public_url(storage_path)
        public_url = public_url_data.get("publicURL") or ""

        # Update the record in the specified Supabase table
        update_resp = supabase.table(table_name).update({
            "storage_path": storage_path,
            "report_url": public_url,
            "status": "ready_for_review"  # or "approved", "completed", etc. as needed
        }).eq("id", report_id).execute()

        if update_resp.get("status_code") not in [200, 204]:
            logger.warning("Supabase table update may have failed: %s", update_resp)

        logger.info("Successfully uploaded PDF to Supabase bucket 'report_pdfs' at %s", storage_path)
        return {
            "storage_path": storage_path,
            "public_url": public_url
        }

    except Exception as e:
        logger.error("Failed to upload/update Supabase for report_id=%s: %s", report_id, str(e), exc_info=True)
        raise
