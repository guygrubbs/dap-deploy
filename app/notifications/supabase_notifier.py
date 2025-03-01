import os
import logging
import time
from datetime import datetime
from threading import Thread
from supabase import create_client, Client
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use the service role key for write ops
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set.")

# Initialize the Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _notify_supabase(
    report_id: int,
    status: str,
    pdf_url: str,
    user_id: Optional[int] = None,
    max_retries: int = 2,
    retry_delay: float = 2.0
) -> None:
    """
    Existing internal function that upserts minimal info about a report (status, pdf_url).
    You can retain this if you only need partial updates or for intermediate statuses.
    """
    data = {
        "report_id": report_id,
        "status": status,
        "pdf_url": pdf_url,
        "completed_at": datetime.utcnow().isoformat(),
    }
    if user_id is not None:
        data["user_id"] = user_id

    attempts = 0
    while attempts < max_retries:
        attempts += 1
        try:
            supabase.table("reports").upsert(data).execute()
            logger.info(
                "Supabase notification succeeded on attempt %d/%d for report_id: %s",
                attempts, max_retries, report_id
            )
            break
        except Exception as e:
            logger.error(
                "Supabase notification attempt %d/%d failed for report_id %s: %s",
                attempts, max_retries, report_id, str(e),
                exc_info=True
            )
            if attempts < max_retries:
                logger.info(
                    "Retrying Supabase notification in %s seconds for report_id: %s",
                    retry_delay, report_id
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    "All retry attempts failed for report_id %s. No further retries will be made.",
                    report_id
                )


def notify_supabase(report_id: int, status: str, pdf_url: str, user_id: int = None) -> None:
    """
    Existing public function that calls _notify_supabase in a background thread.
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
# New function below to upsert the *final* Tier 2 report object (sections).
# ----------------------------------------------------------------------

def _notify_supabase_final_report(
    report_id: int,
    final_report_data: Dict[str, Any],
    user_id: Optional[int] = None,
    max_retries: int = 2,
    retry_delay: float = 2.0
) -> None:
    """
    Internal function for upserting the final Tier 2 report structure into the 'reports' table.
    final_report_data is a dictionary containing fields like:
      {
        "report_id": ...,
        "status": "completed",
        "signed_pdf_download_url": "...",
        "sections": [
          {"id": "...", "title": "...", "content": "..."},
          ...
        ]
      }
    We store the entire JSON object or selected fields as needed in Supabase.
    """
    attempts = 0
    while attempts < max_retries:
        attempts += 1
        try:
            # For example, store everything in 'report_data' column (a JSONB column).
            # You might also directly store each field in its own column if your schema is different.
            data = {
                "report_id": report_id,
                "report_data": final_report_data,
                "updated_at": datetime.utcnow().isoformat()
            }
            if user_id is not None:
                data["user_id"] = user_id

            supabase.table("reports").upsert(data).execute()
            logger.info(
                "Supabase final report update succeeded on attempt %d/%d for report_id: %s",
                attempts, max_retries, report_id
            )
            break
        except Exception as e:
            logger.error(
                "Supabase final report update attempt %d/%d failed for report_id %s: %s",
                attempts, max_retries, report_id, str(e),
                exc_info=True
            )
            if attempts < max_retries:
                logger.info(
                    "Retrying final report update in %s seconds for report_id: %s",
                    retry_delay, report_id
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    "All retry attempts failed for report_id %s. No further retries will be made.",
                    report_id
                )


def notify_supabase_final_report(report_id: int, final_report_data: Dict[str, Any], user_id: int = None) -> None:
    """
    Public function to asynchronously update Supabase with the *complete final report*,
    including Tier 2 sections, 'completed' status, and signed PDF URL if applicable.
    """
    logger.debug(
        "Queuing final report upsert to Supabase in a background thread "
        "for report_id=%s, user_id=%s", report_id, user_id
    )
    Thread(
        target=_notify_supabase_final_report,
        args=(report_id, final_report_data, user_id),
        daemon=True
    ).start()
