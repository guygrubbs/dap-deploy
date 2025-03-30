"""
PDF upload functionality for Supabase storage, plus optional email notification.
"""

import os
import logging
import base64
from email.mime.text import MIMEText

try:
    # If your environment has storage3 and you want typed responses:
    from storage3 import UploadResponse
    HAS_UPLOADRESPONSE = True
except ImportError:
    # If storage3 is not installed or is an older version without UploadResponse
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
    user_email: str = None
) -> dict:
    """
    1) Uploads a local PDF file to the specified Supabase Storage bucket,
       under '{user_id}/{report_id}.pdf'.
    2) Retrieves a public URL from that storage location.
    3) If `user_email` is provided, sends an email with the PDF URL.
    
    Returns:
      {
        "storage_path": <str>,
        "public_url": <str>
      }
    """
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check environment variables.")

    storage_path = f"{user_id}/{report_id}.pdf"
    try:
        # 1) Upload to Supabase Storage
        upload_resp = supabase.storage.from_(bucket_name).upload(
            path=storage_path,
            file=pdf_file_path,
            file_options={"content-type": "application/pdf"}
        )

        # 2) Handle success / error depending on type:
        if HAS_UPLOADRESPONSE and isinstance(upload_resp, UploadResponse):
            # Typed response approach
            logger.info(
                "Upload success (UploadResponse). path=%s full_path=%s",
                upload_resp.path,
                getattr(upload_resp, "full_path", None)
            )
        elif isinstance(upload_resp, dict):
            # Dict approach
            if upload_resp.get("error") is None:
                data = upload_resp.get("data", {})
                logger.info("Upload success (dict). path=%s", data.get("path"))
            else:
                logger.warning("Upload failed with error: %s", upload_resp.get("error"))
        else:
            # Unexpected type
            logger.warning("Unexpected upload_resp type: %s => %s", type(upload_resp), upload_resp)

        # 3) Retrieve the public URL
        public_url_data = supabase.storage.from_(bucket_name).get_public_url(storage_path)
        if isinstance(public_url_data, dict):
            public_url = (
                public_url_data.get("publicURL")
                or (public_url_data.get("data") or {}).get("publicUrl")
                or ""
            )
        else:
            # Possibly older or different response shape
            public_url = ""

        logger.info("PDF uploaded. Public URL: %s", public_url)

        # 4) Optionally send email
        if user_email and public_url:
            logger.info("Sending PDF link email to %s (report_id=%s)", user_email, report_id)
            _send_email_via_gmail(
                to_email=user_email,
                pdf_url=public_url,
                from_email="noreply@righthandoperation.com",
                subject=f"Your PDF for report {report_id} is ready!",
                body_prefix="Hello!\n"
            )

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
