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
        # 1. Upload the file to Supabase Storage
        upload_resp = supabase.storage.from_("report_pdfs").upload(
            path=storage_path,
            file=pdf_file_path,
            file_options={"content-type": "application/pdf"}
        )

        # 2. Check for upload errors using attributes, not dict keys
        if upload_resp.error:
            # upload_resp.error might be a dict or a string, depending on the version
            err_msg = upload_resp.error.get("message") if isinstance(upload_resp.error, dict) else upload_resp.error
            raise ValueError(f"Error uploading PDF to Supabase: {err_msg}")

        # 3. Get the public URL
        public_url_data = supabase.storage.from_("report_pdfs").get_public_url(storage_path)
        # In newer versions, this might be public_url_data.public_url or public_url_data.publicURL,
        # depending on how the library structures it. Adjust accordingly.
        public_url = public_url_data.get("publicURL", "")  # or public_url_data.public_url

        # 4. Update the record in the specified Supabase table
        update_resp = supabase.table(table_name).update({
            "storage_path": storage_path,
            "report_url": public_url,
            "status": "ready_for_review"
        }).eq("id", report_id).execute()

        # 5. Check update response attributes, not dict keys
        if update_resp.status_code not in [200, 204]:
            logger.warning(
                "Supabase table update may have failed. Status code: %s; Error: %s",
                update_resp.status_code, update_resp.error
            )

        logger.info("Successfully uploaded PDF to Supabase at %s", storage_path)
        return {
            "storage_path": storage_path,
            "public_url": public_url
        }

    except Exception as e:
        logger.error("Failed to upload/update Supabase for report_id=%s: %s", report_id, str(e), exc_info=True)
        raise
