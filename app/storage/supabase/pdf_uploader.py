"""
PDF upload functionality for Supabase storage, plus sending an email with the link.
"""

import os
import logging
import base64
from email.mime.text import MIMEText

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .client import supabase
from .report_sync import sync_report_to_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------
# (1) HELPER: Domain-wide delegated Gmail sender
# ---------------------------------------------
def _send_email_via_gmail(
    to_email: str,
    pdf_url: str,
    from_email: str = "noreply@yourdomain.com",
    subject: str = "Your PDF is ready!",
    body_prefix: str = None
):
    """
    Sends an email via the Gmail API using domain-wide delegated service account credentials.

    Args:
        to_email: Recipient address
        pdf_url: The public or signed URL to the PDF
        from_email: The Workspace user you want to 'impersonate'
        subject: Email subject line
        body_prefix: Optional extra text to prepend to the message body
    """

    # 1) Load service account JSON from a secure location
    #    e.g., store the path in an env var: SERVICE_ACCOUNT_FILE=/var/secrets/gmail-key.json
    SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "/path/to/service_account.json")

    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    # 2) Delegate to the 'from_email' user
    delegated_credentials = credentials.with_subject(from_email)

    # 3) Build Gmail API service
    service = build("gmail", "v1", credentials=delegated_credentials)

    # 4) Construct message body
    body_lines = []
    if body_prefix:
        body_lines.append(body_prefix)
    body_lines.append(f"Your PDF is ready! Click the link below:\n{pdf_url}\n")
    body_text = "\n".join(body_lines)

    message = MIMEText(body_text)
    message["to"] = to_email
    message["from"] = from_email
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    # 5) Send the email
    try:
        response = service.users().messages().send(
            userId=from_email,
            body={"raw": raw}
        ).execute()
        logger.info("Sent email to %s. Message ID=%s", to_email, response.get("id"))
    except Exception as e:
        logger.error("Failed sending email to %s via Gmail API: %s", to_email, str(e))


# ---------------------------------------------
# (2) MAIN LOGIC: Upload PDF + Email
# ---------------------------------------------
def upload_pdf_to_supabase(
    user_id: int,
    report_id: int,
    pdf_file_path: str,
    table_name: str = "report_requests",
    user_email: str = None  # <--- NEW optional argument
) -> dict:
    """
    Uploads a local PDF file to the 'report-pdfs' bucket in Supabase Storage
    under '{user_id}/{report_id}.pdf'.

    Then updates the 'report_requests' table with 'storage_path' and
    a public URL. Returns a dict with:
      {
        "storage_path": <str>,
        "public_url": <str>
      }

    If user_email is provided, an email is sent with the PDF URL.
    """
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check environment variables.")

    storage_path = f"{user_id}/{report_id}.pdf"
    try:
        # 1. Upload the file to Supabase Storage
        upload_resp = supabase.storage.from_("report-pdfs").upload(
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
        public_url_data = supabase.storage.from_("report-pdfs").get_public_url(storage_path)
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
        report_id_str = str(report_id)
        check_resp = supabase.table(table_name).select("id").eq("external_id", report_id_str).execute()
        
        if hasattr(check_resp, "data") and check_resp.data and len(check_resp.data) > 0:
            # Record exists, update it
            supabase.table(table_name).update({
                "storage_path": storage_path,
                "report_url": public_url,
                "status": status
            }).eq("external_id", report_id_str).execute()
        else:
            # Try to find a pending report without external_id (as a fallback)
            pending_resp = supabase.table(table_name).select("id").is_("external_id", None)\
                .eq("status", "pending").order("created_at", desc=True).limit(1).execute()
            
            if hasattr(pending_resp, "data") and pending_resp.data and isinstance(pending_resp.data, list) and len(pending_resp.data) > 0:
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

        # (NEW) 6. Optionally send an email to the user with the PDF URL
        if user_email and public_url:
            logger.info("Sending PDF link email to %s (report_id=%s)", user_email, report_id)
            _send_email_via_gmail(
                to_email=user_email,
                pdf_url=public_url,
                from_email="noreply@righthandoperation.com",  # or read from env
                subject=f"Your PDF for report {report_id} is ready!",
                body_prefix="Hello!\n"
            )

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
