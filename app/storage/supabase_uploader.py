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

        """
        Typically upload_resp looks like:
        {
          "data": { ...some metadata... } or None,
          "error": { "message": "...some error..." } or None
        }
        """

        # 2. Check for upload errors
        if isinstance(upload_resp, dict):
            error = upload_resp.get("error")
            if error:
                # error might itself be a dict with a "message" key
                err_msg = error.get("message") if isinstance(error, dict) else str(error)
                raise ValueError(f"Error uploading PDF to Supabase: {err_msg}")
        else:
            # If for some reason upload_resp isn't a dict, just log it
            logger.warning(f"Unexpected upload_resp type: {type(upload_resp)} => {upload_resp}")

        # 3. Get the public URL
        public_url_data = supabase.storage.from_("report_pdfs").get_public_url(storage_path)
        # Typically returns {"data": {"publicUrl": "..."}, "error": None} in new versions
        # or { "publicURL": "..." } in older versions.
        # Adjust logic to ensure we retrieve the URL correctly:
        if isinstance(public_url_data, dict):
            public_url = (
                public_url_data.get("publicURL")
                or (public_url_data.get("data") or {}).get("publicUrl")
                or ""
            )
        else:
            public_url = ""

        # 4. Update the record in the specified Supabase table
        # Use external_id instead of id for numeric report IDs
        update_resp = supabase.table(table_name).update({
            "storage_path": storage_path,
            "report_url": public_url,
            "status": "ready_for_review"
        }).eq("external_id", str(report_id)).execute()

        # 5. Check update response
        # In supabase-py 2.x, update_resp might be a `PostgrestResponse`,
        # which has properties like .status_code, .data, .error
        if hasattr(update_resp, "status_code") and update_resp.status_code not in [200, 204]:
            logger.warning(
                "Supabase table update may have failed. Status code: %s; Data: %s; Error: %s",
                update_resp.status_code,
                getattr(update_resp, "data", None),
                getattr(update_resp, "error", None)
            )

        logger.info("Successfully uploaded PDF to Supabase at %s", storage_path)
        return {
            "storage_path": storage_path,
            "public_url": public_url
        }

    except Exception as e:
        logger.error("Failed to upload/update Supabase for report_id=%s: %s", report_id, str(e), exc_info=True)
        raise
