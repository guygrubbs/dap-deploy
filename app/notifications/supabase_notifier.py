import os
import logging
import time
from datetime import datetime
from threading import Thread
from supabase import create_client, Client
from typing import Optional

logger = logging.getLogger(__name__)

# Retrieve Supabase configuration from environment variables.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use the service role key for write ops.
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set.")

# IMPORTANT: Do not hard-code or log your API keys. They must be kept secret.
# Initialize the Supabase client securely using the provided credentials.
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
    Internal function that performs the actual notification (upsert) to Supabase.
    It attempts the operation multiple times (based on max_retries) to handle transient failures.

    Args:
        report_id (int): The report identifier.
        status (str): The report status (e.g., "completed").
        pdf_url (str): Signed or public URL where the PDF can be accessed.
        user_id (int, optional): The ID of the user who initiated the report request.
        max_retries (int): The number of times to retry the operation on failure.
        retry_delay (float): Delay in seconds between retries.

    Returns:
        None
    """
    # Prepare the data payload
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
            response = supabase.table("reports").upsert(data).execute()
            logger.info(
                "Supabase notification succeeded on attempt %d/%d for report_id: %s",
                attempts, max_retries, report_id
            )
            # If successful, break out of the retry loop
            break
        except Exception as e:
            # Log the error and retry if attempts remain
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
    Public function that asynchronously notifies Supabase about a report's status.
    Runs _notify_supabase in a background thread to avoid blocking the main process.

    Args:
        report_id (int): The unique identifier for the report.
        status (str): The report's status (e.g., "completed").
        pdf_url (str): The URL for downloading the PDF report.
        user_id (int, optional): The ID of the user who requested the report.

    Returns:
        None
    """
    logger.debug(
        "Queuing Supabase notification in background thread for report_id=%s, status=%s, user_id=%s",
        report_id, status, user_id
    )
    # Start the notification in a background (daemon) thread so it does not block or
    # hold up the application in case of network delays or transient errors.
    Thread(
        target=_notify_supabase,
        args=(report_id, status, pdf_url, user_id),
        daemon=True
    ).start()
