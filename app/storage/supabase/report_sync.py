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
        logger.info(f"Syncing report with ID: {report_id_str}")
        
        # Check if the report already exists in the reports table
        # This is important to avoid creating duplicate entries
        logger.info("Checking if report already exists in reports table")
        existing_report_response = None
        
        try:
            # First try by report_id column
            existing_report_response = supabase.table("reports").select("*").eq("report_id", report_id_str).execute()
            if hasattr(existing_report_response, "data") and existing_report_response.data:
                if isinstance(existing_report_response.data, list) and len(existing_report_response.data) > 0:
                    logger.info(f"Found existing report with report_id: {report_id_str}")
        except Exception as e:
            logger.warning(f"Error checking for existing report by report_id: {e}")
            
            # Try by id column as fallback
            try:
                existing_report_response = supabase.table("reports").select("*").eq("id", report_id_str).execute()
            except Exception as inner_e:
                logger.warning(f"Error checking for existing report by id: {inner_e}")
        
        # Determine if the report exists
        report_exists = False
        existing_report_id = None
        if existing_report_response and hasattr(existing_report_response, "data") and existing_report_response.data:
            if isinstance(existing_report_response.data, list) and len(existing_report_response.data) > 0:
                report_exists = True
                existing_report_id = existing_report_response.data[0].get("id")
                logger.info(f"Found existing report with database ID: {existing_report_id}")
        
        # Get the title from report_requests if available
        title = _get_report_title(report_id_str)
        
        # Find original report request to get additional metadata
        req_data = _get_report_request_data(report_id_str)
        
        # If we found the original request, extract metadata
        original_user_id = req_data.get("user_id") if req_data else None
        original_startup_id = req_data.get("startup_id") if req_data else None
        report_type = req_data.get("report_type") if req_data else None
        
        # Check if this is a report for a new company (entered by investor)
        startup_details = None
        if req_data and req_data.get("parameters") and isinstance(req_data["parameters"], dict):
            startup_details = req_data["parameters"].get("startup_details")
            
        # If we have startup details but the startup_id matches the user_id, 
        # this is likely a report created by an investor for a new company
        is_new_company_report = (startup_details and 
                               original_startup_id and 
                               original_user_id and 
                               original_startup_id == original_user_id)
            
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
            
        # If this is a new company report (from investor), add company name in report data
        if is_new_company_report and startup_details and startup_details.get("company_name"):
            # Include company name in report data
            if "report_data" not in data or not isinstance(data["report_data"], dict):
                data["report_data"] = {}
            data["report_data"]["company_name"] = startup_details["company_name"]
            
            # Log that we're handling a new company report
            logger.info(f"Handling report for new company: {startup_details['company_name']}")
        
        # Always include startup_id (either existing one or the investor's ID as fallback)
        if startup_id:
            data["startup_id"] = startup_id
        
        # If the report exists, update it; otherwise insert it
        if report_exists and existing_report_id:
            logger.info(f"Updating existing report with database ID: {existing_report_id}")
            # Update by primary key 'id' which is most reliable
            try:
                response = supabase.table("reports").update(data).eq("id", existing_report_id).execute()
                logger.info(f"Update response status code: {getattr(response, 'status_code', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error updating report: {e}", exc_info=True)
                return False
        else:
            logger.info(f"Inserting new report with report_id: {report_id_str}")
            try:
                response = supabase.table("reports").insert(data).execute()
                logger.info(f"Insert response status code: {getattr(response, 'status_code', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error inserting report: {e}", exc_info=True)
                return False
            
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

def _get_report_request_data(external_id: str) -> dict:
    """
    Gets the report request data from the report_requests table
    based on the external ID.
    
    Args:
        external_id: The external ID of the report
        
    Returns:
        dict: The report request data or None if not found
    """
    try:
        if not supabase:
            logger.warning("Supabase client not initialized. Cannot get report request data.")
            return None
            
        # Try to find the report request by external_id
        response = supabase.table("report_requests").select("*").eq("external_id", external_id).execute()
        
        if hasattr(response, "data") and response.data:
            if isinstance(response.data, list) and len(response.data) > 0:
                logger.info(f"Found report request with external ID: {external_id}")
                return response.data[0]
                
        logger.info(f"No report request found with external ID: {external_id}")
        return None
    except Exception as e:
        logger.warning(f"Error getting report request data: {str(e)}")
        return None

def _get_auto_approve_setting() -> bool:
    """
    Gets the auto-approve setting from the system_settings table.
    
    Returns:
        bool: True if auto-approve is enabled, False otherwise
    """
    try:
        if not supabase:
            logger.warning("Supabase client not initialized. Cannot get auto-approve setting.")
            return True  # Default to auto-approve if we can't check
            
        response = supabase.table("system_settings").select("auto_approve_reports").limit(1).execute()
        
        if hasattr(response, "data") and response.data:
            if isinstance(response.data, list) and len(response.data) > 0:
                # If setting exists and is explicitly set to false, return false
                if "auto_approve_reports" in response.data[0] and response.data[0]["auto_approve_reports"] is False:
                    return False
                    
        # Default to auto-approve if setting doesn't exist or is not explicitly false
        return True
    except Exception as e:
        logger.warning(f"Error getting auto-approve setting: {str(e)}")
        return True  # Default to auto-approve if there's an error

def _get_report_title(report_id: str) -> str:
    """
    Gets the title for a report, either from an existing report or
    from the report_requests table.
    
    Args:
        report_id: The external ID of the report
        
    Returns:
        str: The report title or a default title if none is found
    """
    try:
        if not supabase:
            logger.warning("Supabase client not initialized. Cannot get report title.")
            return f"Report {report_id}"
            
        # First try to get the title from the report_requests table
        req_data = _get_report_request_data(report_id)
        
        if req_data and "title" in req_data and req_data["title"]:
            return req_data["title"]
            
        # If no title is found in report_requests, use a default title
        return f"Generated Report {report_id}"
    except Exception as e:
        logger.warning(f"Error getting report title: {str(e)}")
        return f"Report {report_id}"

def _extract_valid_status(report_data: dict) -> str:
    """
    Helper function to extract a valid status from report data.
    Ensures we have a string status value to avoid database constraints.
    """
    # Default status if nothing can be extracted from report_data
    report_status = "pending"
    
    if report_data:
        if isinstance(report_data, dict):
            # Get status from report_data or default to "pending"
            status_value = report_data.get("status")
            
            # Make sure we have a valid string status value
            if status_value and isinstance(status_value, str):
                report_status = status_value
    
    # Final safety check - never return None or empty string
    if not report_status or not isinstance(report_status, str):
        report_status = "pending"
    
    return report_status
