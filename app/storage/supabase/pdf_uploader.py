"""
PDF upload functionality for Supabase storage, plus optional email notification.

This version allows sending to multiple emails, plus always BCC two admin emails.
"""

import os
import logging
import base64
import json
from email.mime.text import MIMEText
from typing import Union, List

try:
    from storage3 import UploadResponse
    HAS_UPLOADRESPONSE = True
except ImportError:
    UploadResponse = None
    HAS_UPLOADRESPONSE = False

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .client import supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------
# (1) HELPER: Domain-wide delegated Gmail sender
# ---------------------------------------------
def _send_email_via_gmail(
    to_email: Union[str, List[str]],
    pdf_url: str,
    from_email: str = "noreply@righthandoperation.com",
    subject: str = "Your PDF is ready!",
    body_prefix: str = None
):
    """
    Sends an email via the Gmail API using domain-wide delegated service account credentials,
    allowing multiple recipients in 'to_email', plus always BCC two admin addresses.

    'to_email' can be a single string or a list of recipient strings.
    We'll also BCC two addresses: admin1@yourdomain.com and admin2@yourdomain.com.

    Make sure 'from_email' matches a user/alias in your Google Workspace for domain-wide delegation.
    """
    # 1) Load the entire JSON credentials from environment
    SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON", "")
    if not SERVICE_ACCOUNT_JSON.strip():
        raise RuntimeError("SERVICE_ACCOUNT_JSON env var is empty or not set.")
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    # 2) Parse and build credentials
    info = json.loads(SERVICE_ACCOUNT_JSON)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    # 3) Impersonate 'from_email'
    delegated_credentials = credentials.with_subject(from_email)
    service = build("gmail", "v1", credentials=delegated_credentials)

    # 4) Convert single to_email to a list if needed
    if isinstance(to_email, str):
        to_list = [to_email]
    else:
        to_list = to_email  # already a list

    # 5) Always BCC these admin addresses
    admin_bcc_list = [
        "shweta.mokashi@righthandoperation.com",
        "guy.grubbs@righthandoperation.com"
    ]

    # Build the email body
    body_lines = []
    if body_prefix:
        body_lines.append(body_prefix)
    body_lines.append(f"Your PDF is ready! Click the link below:\n{pdf_url}\n")
    body_text = "\n".join(body_lines)

    # 6) Create a MIMEText object
    message = MIMEText(body_text)
    # For multiple "To" recipients, join them with commas
    message["to"] = ",".join(to_list)
    message["from"] = from_email
    message["subject"] = subject
    # BCC the admin addresses
    message["bcc"] = ",".join(admin_bcc_list)

    # 7) Encode and send
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    try:
        response = service.users().messages().send(
            userId=from_email,
            body={"raw": raw}
        ).execute()
        logger.info("Sent email to %s. Message ID=%s", to_list, response.get("id"))
    except Exception as e:
        logger.error("Failed sending email to %s via Gmail API: %s", to_list, str(e))


# ---------------------------------------------
# (2) MAIN LOGIC: Upload PDF + Optional Email
# ---------------------------------------------
def upload_pdf_to_supabase(
    user_id: int,
    report_id: int,
    pdf_file_path: str,
    bucket_name: str = "report-pdfs",
    # Let’s accept multiple recipients in a list for 'user_email'
    user_email: Union[str, List[str], None] = None
) -> dict:
    """
    1) Uploads a local PDF file to the specified Supabase Storage bucket,
       under '{user_id}/{report_id}.pdf'.
    2) Builds a direct "public" URL from the upload response, assuming
       that the bucket or file is publicly accessible.
    3) Sends an email with the PDF link if user_email is provided (which can be single or list).

    Returns a dict:
      {
        "storage_path": <str>,
        "public_url": <str>
      }
    """
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check environment variables.")

    storage_path = f"{user_id}/{report_id}.pdf"
    base_supabase_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")

    try:
        # 1) Upload the PDF
        upload_resp = supabase.storage.from_(bucket_name).upload(
            path=storage_path,
            file=pdf_file_path,
            file_options={"content-type": "application/pdf"}
        )

        # 2) Build the public URL from the response
        if HAS_UPLOADRESPONSE and isinstance(upload_resp, UploadResponse):
            logger.info(
                "Upload success (UploadResponse). path=%s, full_path=%s",
                upload_resp.path,
                getattr(upload_resp, "full_path", None)
            )
            full_path = getattr(upload_resp, "full_path", None)
            if full_path:
                public_url = f"{base_supabase_url}/storage/v1/object/public/{full_path}"
            else:
                public_url = f"{base_supabase_url}/storage/v1/object/public/{bucket_name}/{upload_resp.path}"
        elif isinstance(upload_resp, dict):
            logger.info("Upload success (dict) => %s", upload_resp)
            if upload_resp.get("error") is None:
                data = upload_resp.get("data", {})
                custom_path = data.get("fullPath") or data.get("path") or storage_path
                public_url = f"{base_supabase_url}/storage/v1/object/public/{custom_path}"
            else:
                logger.warning("Upload returned an error: %s", upload_resp.get("error"))
                public_url = f"{base_supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"
        else:
            logger.info("Upload success (unrecognized type). raw_response=%s", upload_resp)
            public_url = f"{base_supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"

        logger.info("Constructed PDF public URL: %s", public_url)

        # 3) If user_email is provided, send to them + BCC the admins
        if user_email:
            logger.info("Sending PDF link email to %s (report_id=%s)", user_email, report_id)
            _send_email_via_gmail(
                to_email=user_email,  # can be a single string or list
                pdf_url=public_url,
                from_email="noreply@yourdomain.com",
                subject=f"Your PDF for report {report_id} is ready!",
                body_prefix="Hello!\n"
            )
        else:
            logger.info("No user_email was provided; skipping email send.")

        return {
            "storage_path": storage_path,
            "public_url": public_url
        }

    except Exception as e:
        logger.error(
            "Failed to upload PDF to Supabase (report_id=%s): %s",
            report_id,
            str(e),
            exc_info=True
        )
        raise