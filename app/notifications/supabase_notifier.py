import os
import logging
import time
from datetime import datetime
from threading import Thread
from supabase import create_client, Client
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Environment & Supabase Initialization
# ----------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service role key for write ops
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ----------------------------------------------------------------------
# Basic Notify Function: Minimal partial update (status, pdf_url)
# ----------------------------------------------------------------------
def _notify_supabase(
    report_id: int,
    status: str,
    pdf_url: str,
    user_id: Optional[int] = None,
    max_retries: int = 2,
    retry_delay: float = 2.0
) -> None:
    """
    Internal function that upserts minimal info about a report
    (status, pdf_url, etc.) into the 'reports' table.
    """
    # Convert report_id to string if your 'report_id' column is text
    report_id_str = str(report_id)

    data = {
        "report_id": report_id_str,  # The external identifier in text form
        "status": status,            # Must not be NULL (table has NOT NULL constraint)
        "pdf_url": pdf_url,
        "updated_at": datetime.utcnow().isoformat()
    }

    # If the report is completed, set completed_at
    if status.lower() == "completed":
        data["completed_at"] = datetime.utcnow().isoformat()

    # Add user_id if provided
    if user_id is not None:
        # If the DB column is text, convert to str:
        data["user_id"] = str(user_id)

    attempts = 0
    while attempts < max_retries:
        attempts += 1
        try:
            supabase.table("reports").upsert(data).execute()
            logger.info(
                "Supabase notification succeeded on attempt %d/%d for report_id=%s",
                attempts, max_retries, report_id_str
            )
            break
        except Exception as e:
            logger.error(
                "Supabase notification attempt %d/%d failed for report_id %s: %s",
                attempts, max_retries, report_id_str, str(e),
                exc_info=True
            )
            if attempts < max_retries:
                logger.info(
                    "Retrying Supabase notification in %s seconds for report_id=%s",
                    retry_delay, report_id_str
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    "All retry attempts failed for report_id=%s. No further retries will be made.",
                    report_id_str
                )


def notify_supabase(report_id: int, status: str, pdf_url: str, user_id: int = None) -> None:
    """
    Public function that calls _notify_supabase in a background thread.
    Useful for partial or intermediate report status updates.
    """
    logger.debug(
        "Queuing Supabase notification in background thread for report_id=%s, status=%s, user_id=%s",
        report_id, status, user_id
    )
    Thread(
        target=_notify_supabase,
        args=(report_id, status, pdf_url, user_id),
        daemon=True
    ).start()


# ----------------------------------------------------------------------
# Final Report Notify Function: Upserts Tier 2 data in 'report_data'
# ----------------------------------------------------------------------
def _notify_supabase_final_report(
    report_id: int,
    final_report_data: Dict[str, Any],
    user_id: Optional[int] = None,
    max_retries: int = 2,
    retry_delay: float = 2.0
) -> None:
    """
    Internal function for upserting the final Tier 2 report structure
    into the 'reports' table. final_report_data might look like:
      {
        "status": "completed",
        "signed_pdf_download_url": "...",
        "sections": [...],
        ...
      }
    We'll store that entire dict in 'report_data' (a jsonb column).
    We'll also set top-level 'status' and 'pdf_url'.
    """
    # Convert the integer to string if the column expects text
    report_id_str = str(report_id)

    # Extract or default status so the top-level 'status' column is never NULL
    report_status = final_report_data.get("status", "completed")
    # Optionally handle a PDF URL field if you want it at top-level
    pdf_url = final_report_data.get("signed_pdf_download_url", None)

    attempts = 0
    while attempts < max_retries:
        attempts += 1
        try:
            data = {
                "report_id": report_id_str,
                "report_data": final_report_data,  # JSONB column
                "status": report_status,           # Must not be NULL
                "updated_at": datetime.utcnow().isoformat()
            }
            # If the final report is completed, set completed_at
            if report_status.lower() == "completed":
                data["completed_at"] = datetime.utcnow().isoformat()

            # If we have a final PDF URL, store it at top-level
            if pdf_url:
                data["pdf_url"] = pdf_url

            if user_id is not None:
                data["user_id"] = str(user_id)

            supabase.table("reports").upsert(data).execute()
            logger.info(
                "Supabase final report update succeeded on attempt %d/%d for report_id=%s",
                attempts, max_retries, report_id_str
            )
            break
        except Exception as e:
            logger.error(
                "Supabase final report update attempt %d/%d failed for report_id=%s: %s",
                attempts, max_retries, report_id_str, str(e),
                exc_info=True
            )
            if attempts < max_retries:
                logger.info(
                    "Retrying final report update in %s seconds for report_id=%s",
                    retry_delay, report_id_str
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    "All retry attempts failed for report_id=%s. No further retries will be made.",
                    report_id_str
                )


def notify_supabase_final_report(report_id: int, final_report_data: Dict[str, Any], user_id: int = None) -> None:
    """
    Public function to asynchronously update Supabase with the complete final report,
    including Tier 2 sections, 'completed' status, and an optional PDF URL.
    """
    logger.debug(
        "Queuing final report upsert to Supabase in a background thread for report_id=%s, user_id=%s",
        report_id, user_id
    )
    Thread(
        target=_notify_supabase_final_report,
        args=(report_id, final_report_data, user_id),
        daemon=True
    ).start()
