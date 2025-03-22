
"""
PDF upload functionality for Supabase storage.
"""

import logging
from .client import supabase
from .report_sync import sync_report_to_supabase

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

        # Get auto-approve setting
        auto_approve = _get_auto_approve_setting()
        status = "approved" if auto_approve else "ready_for_review"
        
        # 4. Update the record in the specified Supabase table
        # Always use external_id as string to match the report_id
        report_id_str = str(report_id)
        
        # Check if there's an existing record with this external_id
        check_resp = supabase.table(table_name).select("id").eq("external_id", report_id_str).execute()
        
        if hasattr(check_resp, "data") and check_resp.data and len(check_resp.data) > 0:
            # Record exists, update it
            update_resp = supabase.table(table_name).update({
                "storage_path": storage_path,
                "report_url": public_url,
                "status": status
            }).eq("external_id", report_id_str).execute()
        else:
            # Try to find a pending report without external_id (as a fallback)
            # Correct syntax for order method - using just two arguments
            pending_resp = supabase.table(table_name).select("id").is_("external_id", None).eq("status", "pending").order("created_at", desc=True).limit(1).execute()
            
            if hasattr(pending_resp, "data") and pending_resp.data and isinstance(pending_resp.data, list) and len(pending_resp.data) > 0:
                # Found a pending report, update it
                report_internal_id = pending_resp.data[0].get("id")
                if report_internal_id:
                    logger.info(f"Found pending report {report_internal_id}, updating with external_id {report_id}")
                    update_resp = supabase.table(table_name).update({
                        "storage_path": storage_path,
                        "report_url": public_url,
                        "status": status,
                        "external_id": report_id_str
                    }).eq("id", report_internal_id).execute()
                else:
                    logger.warning(f"Found pending report but id is missing")
            else:
                logger.warning(f"No report found with external_id {report_id_str} and no pending reports found")

        # 5. Sync the report data to ensure a single consistent entry in the reports table
        # Create minimal report data with the PDF URL
        report_data = {
            "status": status,
            "pdf_url": public_url
        }
        
        # Use report_sync.py to ensure consistent syncing with reports table
        sync_result = sync_report_to_supabase(
            report_id=report_id,
            report_data=report_data,
            user_id=str(user_id) if user_id else None
        )
        
        if not sync_result:
            logger.warning(f"Failed to sync report {report_id} to reports table")

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
        settings_resp = supabase.table("system_settings").select("auto_approve_reports").execute()
        if hasattr(settings_resp, "data") and settings_resp.data:
            if isinstance(settings_resp.data, list) and len(settings_resp.data) > 0:
                # Return True if auto_approve_reports is True or None
                return settings_resp.data[0].get("auto_approve_reports") is not False
    except Exception as err:
        logger.warning(f"Could not get auto-approve setting: {str(err)}")
    
    # Default to True if we can't get the setting
    return True