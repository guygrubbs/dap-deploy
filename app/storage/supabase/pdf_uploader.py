"""
PDF upload functionality for Supabase storage.
"""

import logging
from .client import supabase

logger = logging.getLogger(__name__)

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

        # 2. Check for upload errors
        if isinstance(upload_resp, dict):
            error = upload_resp.get("error")
            if error:
                err_msg = error.get("message") if isinstance(error, dict) else str(error)
                raise ValueError(f"Error uploading PDF to Supabase: {err_msg}")
        else:
            # If for some reason upload_resp isn't a dict, just log it
            logger.warning(f"Unexpected upload_resp type: {type(upload_resp)} => {upload_resp}")

        # 3. Get the public URL
        public_url_data = supabase.storage.from_("report_pdfs").get_public_url(storage_path)
        if isinstance(public_url_data, dict):
            public_url = (
                public_url_data.get("publicURL")
                or (public_url_data.get("data") or {}).get("publicUrl")
                or ""
            )
        else:
            public_url = ""

        # 4. Decide on a new status
        #    If auto-approve is True, set status='approved'; else 'ready_for_review'
        auto_approve = _get_auto_approve_setting()
        status = "approved" if auto_approve else "ready_for_review"
        
        # 5. Update the record in the 'report_requests' table
        report_id_str = str(report_id)

        # First, see if a record has external_id=report_id_str
        check_resp = supabase.table(table_name).select("id").eq("external_id", report_id_str).execute()
        if hasattr(check_resp, "data") and check_resp.data and len(check_resp.data) > 0:
            # Found a matching record
            update_resp = supabase.table(table_name).update({
                "storage_path": storage_path,
                "report_url": public_url,
                "status": status
            }).eq("external_id", report_id_str).execute()
        else:
            # Fallback: find a pending row with no external_id
            pending_resp = supabase.table(table_name).select("id") \
                .is_("external_id", None) \
                .eq("status", "pending") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            
            if (hasattr(pending_resp, "data") and pending_resp.data and 
                    isinstance(pending_resp.data, list) and len(pending_resp.data) > 0):
                report_internal_id = pending_resp.data[0].get("id")
                if report_internal_id:
                    logger.info(f"Found pending report {report_internal_id}, updating with external_id {report_id}")
                    supabase.table(table_name).update({
                        "storage_path": storage_path,
                        "report_url": public_url,
                        "status": status,
                        "external_id": report_id_str
                    }).eq("id", report_internal_id).execute()
                else:
                    logger.warning("Found pending report but id is missing")
            else:
                logger.warning(
                    f"No report found with external_id={report_id_str} "
                    f"and no pending reports found to attach PDF upload."
                )

        logger.info("Successfully uploaded PDF to Supabase at %s", storage_path)
        return {
            "storage_path": storage_path,
            "public_url": public_url
        }

    except Exception as e:
        logger.error("Failed to upload/update Supabase for report_id=%s: %s", report_id, str(e), exc_info=True)
        raise


def _get_auto_approve_setting() -> bool:
    """
    Helper function to retrieve auto-approve setting from system_settings table.
    Defaults to True if the setting doesn't exist.
    """
    try:
        resp = supabase.table("system_settings").select("auto_approve_reports").execute()
        if hasattr(resp, "data") and resp.data:
            if isinstance(resp.data, list) and len(resp.data) > 0:
                return resp.data[0].get("auto_approve_reports") is not False
    except Exception as err:
        logger.warning(f"Could not get auto-approve setting: {str(err)}")
    
    return True  # Default to True if we can't read
