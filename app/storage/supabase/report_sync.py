"""
Functions for syncing report data with Supabase.
"""

import logging
from .client import supabase

logger = logging.getLogger(__name__)

def sync_report_to_supabase(
    report_id: int,
    report_data: dict,
    user_id: str = None,
    startup_id: str = None
) -> bool:
    """
    Sync report data to the Supabase reports table.
    Used by the notification system to keep Supabase in sync with report status.
    
    Args:
        report_id: The external ID of the report
        report_data: The complete report data including sections, status, etc.
        user_id: Optional user ID
        startup_id: Optional startup ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not supabase:
        logger.warning("Supabase client not initialized. Cannot sync report data.")
        return False
        
    try:
        # Convert report_id to string for consistent querying
        report_id_str = str(report_id)
        
        # SCHEMA CORRECTION: Check the actual column structure
        # Try to get the table structure first to verify what fields exist
        table_info = supabase.table("reports").select("*").limit(1).execute()
        if hasattr(table_info, "data") and table_info.data:
            # Log the actual column names for debugging
            if isinstance(table_info.data, list) and len(table_info.data) > 0:
                logger.info(f"Reports table columns: {list(table_info.data[0].keys())}")
        
        # Check if 'report_id' column exists, otherwise try using 'id' column
        report_exists = False
        
        # First try to query based on 'report_id' column if it exists
        try:
            logger.info(f"Trying to find report using 'report_id' column with value: {report_id_str}")
            existing_report = supabase.table("reports").select("id").eq("report_id", report_id_str).execute()
            
            if hasattr(existing_report, "data") and existing_report.data:
                if isinstance(existing_report.data, list) and len(existing_report.data) > 0:
                    report_exists = True
                    logger.info(f"Found existing report with report_id: {report_id_str}")
        except Exception as e:
            logger.warning(f"Error querying 'report_id' column: {str(e)}")
            
            # Fallback: Try using 'id' column instead if 'report_id' query failed
            try:
                logger.info(f"Trying to find report using 'id' column with value: {report_id_str}")
                existing_report = supabase.table("reports").select("*").eq("id", report_id_str).execute()
                
                if hasattr(existing_report, "data") and existing_report.data:
                    if isinstance(existing_report.data, list) and len(existing_report.data) > 0:
                        report_exists = True
                        logger.info(f"Found existing report with id: {report_id_str}")
            except Exception as inner_e:
                logger.warning(f"Error querying 'id' column: {str(inner_e)}")
        
        # Get the title from report_requests if available
        title = _get_report_title(report_id)
        
        # Find original report request to get additional metadata
        req_data = _get_report_request_data(report_id)
        
        # If we found the original request, extract metadata
        original_user_id = req_data.get("user_id") if req_data else None
        original_startup_id = req_data.get("startup_id") if req_data else None
        report_type = req_data.get("report_type") if req_data else None
            
        # Prepare the data to upsert
        # Ensure we have a valid status - this was the root cause of the error
        report_status = _extract_valid_status(report_data)
        
        # Log what we're about to insert for debugging
        logger.info(f"Syncing report {report_id} with status: {report_status}")
        
        # Check if auto-approve is enabled in system settings
        auto_approve = _get_auto_approve_setting()
        
        # If auto-approve is enabled and status is completed, change to approved
        if auto_approve and report_status in ["completed", "ready_for_review"]:
            report_status = "approved"
            logger.info(f"Auto-approve enabled, changing status to: {report_status}")
        
        # Use passed parameters or fall back to data from original report request
        user_id = user_id or original_user_id
        startup_id = startup_id or original_startup_id
        
        data = {
            "report_data": report_data,
            "status": report_status,  # Make sure status is explicitly set and valid
            "title": title,  # Use the title we retrieved or the default
            "report_type": report_type
        }
        
        # Add report_id column explicitly for consistency
        data["report_id"] = report_id_str
        
        # Add optional fields if provided
        if user_id:
            data["user_id"] = user_id
        if startup_id:
            data["startup_id"] = startup_id
        
        # If the report exists, update it; otherwise insert it
        if report_exists:
            logger.info(f"Updating existing report with report_id: {report_id_str}")
            # Try updating by 'report_id' first
            try:
                response = supabase.table("reports").update(data).eq("report_id", report_id_str).execute()
            except Exception as e:
                logger.warning(f"Error updating by 'report_id', trying 'id' instead: {str(e)}")
                # Fallback to updating by 'id'
                response = supabase.table("reports").update(data).eq("id", report_id_str).execute()
        else:
            logger.info(f"Inserting new report with report_id: {report_id_str}")
            response = supabase.table("reports").insert(data).execute()
            
        # Check response
        if hasattr(response, "status_code") and response.status_code not in [200, 201, 204]:
            logger.warning(
                "Supabase reports sync failed. Status code: %s; Data: %s; Error: %s",
                response.status_code,
                getattr(response, "data", None),
                getattr(response, "error", None)
            )
            return False
            
        logger.info(f"Successfully synced report {report_id} to Supabase")
        
        # Also update the report_requests table with the external ID if we have it
        if req_data and "id" in req_data and report_id:
            _update_report_request_external_id(req_data["id"], report_id)
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync report {report_id} to Supabase: {str(e)}", exc_info=True)
        return False

def _update_report_request_external_id(request_id: str, external_id: int) -> None:
    """
    Updates the report_requests table with the external ID from the API.
    This ensures the connection between our internal UUID and the external numeric ID.
    """
    try:
        # Only update if external_id is not already set
        check_resp = supabase.table("report_requests").select("external_id").eq("id", request_id).execute()
        
        if hasattr(check_resp, "data") and check_resp.data:
            if isinstance(check_resp.data, list) and len(check_resp.data) > 0:
                # If external_id is already set and matches, don't update
                existing_external_id = check_resp.data[0].get("external_id")
                if existing_external_id and existing_external_id == str(external_id):
                    logger.info(f"External ID {external_id} already set for request {request_id}")
                    return
        
        # Update the report_requests table with the external ID
        update_resp = supabase.table("report_requests").update({"external_id": str(external_id)}).eq("id", request_id).execute()
        
        if hasattr(update_resp, "status_code") and update_resp.status_code not in [200, 201, 204]:
            logger.warning(
                "Failed to update report_requests with external ID. Status code: %s; Error: %s",
                update_resp.status_code,
                getattr(update_resp, "error", None)
            )
        else:
            logger.info(f"Updated report_requests with external ID {external_id} for request {request_id}")
    except Exception as e:
        logger.warning(f"Error updating report_requests with external ID: {str(e)}")

def _get_report_request_data(report_id: int) -> dict:
    """
    Helper function to retrieve report data from report_requests table.
    """
    try:
        # Convert to string for consistent querying
        report_id_str = str(report_id)
        
        # First try to look up by external_id
        report_req_resp = supabase.table("report_requests").select("*").eq("external_id", report_id_str).execute()
        
        if hasattr(report_req_resp, "data") and report_req_resp.data:
            if isinstance(report_req_resp.data, list) and len(report_req_resp.data) > 0:
                return report_req_resp.data[0]
                
        # If not found, we might be dealing with the internal ID
        # (though this is less likely for this function's use case)
        report_req_resp = supabase.table("report_requests").select("*").eq("id", str(report_id)).execute()
        
        if hasattr(report_req_resp, "data") and report_req_resp.data:
            if isinstance(report_req_resp.data, list) and len(report_req_resp.data) > 0:
                return report_req_resp.data[0]
    except Exception as err:
        logger.warning(f"Could not get report request data: {str(err)}")
    
    return {}

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

def _get_report_title(report_id: int) -> str:
    """
    Helper function to retrieve report title from report_requests table.
    """
    try:
        report_id_str = str(report_id)
        report_req_resp = supabase.table("report_requests").select("title").eq("external_id", report_id_str).execute()
        if hasattr(report_req_resp, "data") and report_req_resp.data:
            if isinstance(report_req_resp.data, list) and len(report_req_resp.data) > 0:
                return report_req_resp.data[0].get("title", "Generated Report")
    except Exception as title_err:
        logger.warning(f"Could not get report title: {str(title_err)}")
    
    return "Generated Report"

def _extract_valid_status(report_data: dict) -> str:
    """
    Helper function to extract a valid status from report data.
    Ensures we have a string status value to avoid database constraints.
    """
    report_status = "pending"  # Default status
    if report_data:
        if isinstance(report_data, dict):
            # Get status from report_data or default to "pending"
            report_status = report_data.get("status", "pending")
            
            # Make sure we have a valid status value
            if not report_status or not isinstance(report_status, str):
                report_status = "pending"
    
    return report_status