"""
PDF upload functionality for Supabase storage, plus optional email notification.

This version builds a direct PUBLIC link from `upload_resp.full_path` or `upload_resp.path`
so that you can email the user a link immediately. It does NOT call `get_public_url(...)`.
"""

import os
import logging
import base64
from email.mime.text import MIMEText

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
    to_email: str,
    pdf_url: str,
    from_email: str = "noreply@yourdomain.com",
    subject: str = "Your PDF is ready!",
    body_prefix: str = None
):
    """
    Sends an email via the Gmail API using domain-wide delegated service account credentials.
    """
    SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "/path/to/service_account.json")
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    delegated_credentials = credentials.with_subject(from_email)
    service = build("gmail", "v1", credentials=delegated_credentials)

    # Build the email body
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

    try:
        response = service.users().messages().send(
            userId=from_email,
            body={"raw": raw}
        ).execute()
        logger.info("Sent email to %s. Message ID=%s", to_email, response.get("id"))
    except Exception as e:
        logger.error("Failed sending email to %s via Gmail API: %s", to_email, str(e))


# ---------------------------------------------
# (2) MAIN LOGIC: Upload PDF + Optional Email
# ---------------------------------------------
def upload_pdf_to_supabase(
    user_id: int,
    report_id: int,
    pdf_file_path: str,
    bucket_name: str = "report-pdfs",
    user_email: str = "guy.grubbs@righthandoperation.com"
) -> dict:
    """
    1) Uploads a local PDF file to the specified Supabase Storage bucket,
       under '{user_id}/{report_id}.pdf'.
    2) Builds a direct "public" URL from the upload response, assuming
       that the bucket or file is publicly accessible.
    3) Sends an email with the PDF link if user_email is provided.

    Returns a dict:
      {
        "storage_path": <str>,
        "public_url": <str>
      }
    """
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check environment variables.")

    # We'll store the PDF at: bucket_name/user_id/report_id.pdf
    storage_path = f"{user_id}/{report_id}.pdf"

    # You can remove trailing slash from SUPABASE_URL to avoid double slashes:
    base_supabase_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")

    try:
        # 1) Upload to Supabase Storage
        upload_resp = supabase.storage.from_(bucket_name).upload(
            path=storage_path,
            file=pdf_file_path,
            file_options={"content-type": "application/pdf"}
        )

        # 2) Handle typed or dict-based response
        if HAS_UPLOADRESPONSE and isinstance(upload_resp, UploadResponse):
            logger.info(
                "Upload success (UploadResponse). path=%s, full_path=%s",
                upload_resp.path,
                getattr(upload_resp, "full_path", None)
            )
            # We'll build a direct public link from .full_path
            full_path = getattr(upload_resp, "full_path", None)
            if full_path:
                public_url = f"{base_supabase_url}/storage/v1/object/public/{full_path}"
            else:
                # fallback if full_path is missing
                public_url = f"{base_supabase_url}/storage/v1/object/public/{bucket_name}/{upload_resp.path}"

        elif isinstance(upload_resp, dict):
            logger.info("Upload success (dict) => %s", upload_resp)
            if upload_resp.get("error") is None:
                data = upload_resp.get("data", {})
                # old-style dict may store 'path' or 'fullPath'
                custom_path = data.get("fullPath") or data.get("path") or storage_path
                public_url = f"{base_supabase_url}/storage/v1/object/public/{custom_path}"
            else:
                logger.warning("Upload returned an error: %s", upload_resp.get("error"))
                # We'll still build a fallback link:
                public_url = f"{base_supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"

        else:
            # Some unrecognized type, assume success but no known fields
            logger.info("Upload success (unrecognized type). raw_response=%s", upload_resp)
            public_url = f"{base_supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"

        logger.info("Constructed PDF public URL: %s", public_url)

        # 3) If we have a user_email, send the link
        if user_email:
            logger.info("Sending PDF link email to %s (report_id=%s)", user_email, report_id)
            _send_email_via_gmail(
                to_email=user_email,
                pdf_url=public_url,
                from_email="noreply@righthandoperation.com",
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
