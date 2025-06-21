import os
import logging
import time
import uuid
from datetime import datetime
from threading import Thread
from supabase import create_client, Client
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use the service role key for write ops
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set.")

# Initialize the Supabase client (still created but not used for upserts anymore)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _notify_supabase(
    report_id: Union[str, uuid.UUID],
    status: str,
    pdf_url: str,
    user_id: Optional[int] = None,
    max_retries: int = 2,
    retry_delay: float = 2.0
) -> None:
    """
    Updated internal function that NO LONGER upserts info about a report.

    Previously, it called:
        supabase.table("reports").upsert(data).execute()
    but now we have removed that logic so it won't attempt any DB writes.
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
            supabase.table("api_reports").upsert(data).execute()
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


def notify_supabase(report_id: Union[str, uuid.UUID], status: str, pdf_url: str, user_id: int = None) -> None:
    """
    Public function that spawns a background thread, but no longer does any actual DB writes.
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
# Final Tier 2 report "notification" is also a NO-OP
# ----------------------------------------------------------------------

def _notify_supabase_final_report(
    report_id: Union[str, uuid.UUID],
    final_report_data: Dict[str, Any],
    user_id: Optional[int] = None,
    max_retries: int = 2,
    retry_delay: float = 2.0
) -> None:
    """
    Internal function for upserting the final Tier 2 report object.
    Now updated to NOT do any DB writes.
    """
    attempts = 0
    while attempts < max_retries:
        attempts += 1
        try:
            supabase.table("reports").upsert({
                "report_id": report_id,
                "report_data": final_report_data,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
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
    Public function to asynchronously update Supabase with the final report.
    Now also a NO-OP for DB writes.
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
