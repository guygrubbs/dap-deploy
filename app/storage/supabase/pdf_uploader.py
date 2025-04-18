import os
import logging
import base64
import json
import uuid
import time  # new import for retry delay
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

def _send_email_via_gmail(
    to_email: Union[str, List[str]],
    pdf_url: str,
    from_email: str = "noreply@righthandoperation.com",
    subject: str = "Your PDF is ready!",
    body_prefix: str = None
):
    """
    Sends an HTML email via the Gmail API using domain-wide delegated service
    account credentials, BCC-ing two admin addresses.
    """
    SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON", "")
    if not SERVICE_ACCOUNT_JSON.strip():
        raise RuntimeError("SERVICE_ACCOUNT_JSON env var is empty or not set.")

    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    info = json.loads(SERVICE_ACCOUNT_JSON)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    delegated_credentials = credentials.with_subject(from_email)
    service = build("gmail", "v1", credentials=delegated_credentials)

    if isinstance(to_email, str):
        to_list = [to_email]
    else:
        to_list = to_email

    admin_bcc_list = [
        "shweta.mokashi@righthandoperation.com",
        "guy.grubbs@righthandoperation.com"
    ]

    lines = []
    if body_prefix:
        lines.append(f"<p>{body_prefix}</p>")
    lines.append(
        f"<p>Your PDF is ready! "
        f'<a href="{pdf_url}" target="_blank">Open your PDF here</a>.</p>'
    )
    html_content = "\n".join(lines)
    message = MIMEText(html_content, "html")
    message["to"] = ",".join(to_list)
    message["from"] = from_email
    message["subject"] = subject
    message["bcc"] = ",".join(admin_bcc_list)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    try:
        response = service.users().messages().send(
            userId=from_email,
            body={"raw": raw}
        ).execute()
        logger.info("Sent email to %s. Message ID=%s", to_list, response.get("id"))
    except Exception as e:
        logger.error("Failed sending email to %s via Gmail API: %s", to_list, str(e))

def upload_pdf_to_supabase(
    user_id: int,
    report_id: Union[str, uuid.UUID],
    pdf_file_path: str,
    bucket_name: str = "report-pdfs",
    user_email: Union[str, List[str], None] = None
) -> dict:
    """
    1) Uploads a local PDF file to the specified Supabase Storage bucket,
       under '{user_id}/{report_id}.pdf'.
    2) Constructs a public URL from the upload response.
    3) Sends an email with a hyperlink if user_email is provided.
    """

    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check environment variables.")

    storage_path = f"{user_id}/{report_id}.pdf"
    base_supabase_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")

    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            # 1) Upload PDF with a retry mechanism
            upload_resp = supabase.storage.from_(bucket_name).upload(
                path=storage_path,
                file=pdf_file_path,
                file_options={"content-type": "application/pdf"}
            )
            break   # Exit the loop if upload succeeds
        except Exception as e:
            attempt += 1
            logger.error(
                "Attempt %s: Failed to upload PDF to Supabase (report_id=%s): %s",
                attempt, report_id, str(e),
                exc_info=True
            )
            if attempt < max_retries:
                time.sleep(2)  # Wait a bit before retrying
            else:
                raise

    # 2) Build public URL from upload response
    public_url = None
    if HAS_UPLOADRESPONSE and isinstance(upload_resp, UploadResponse):
        logger.info(
            "Upload success (UploadResponse). path=%s, full_path=%s",
            upload_resp.path, getattr(upload_resp, "full_path", None)
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
    else:
        logger.info("Upload success (unrecognized type). raw_response=%s", upload_resp)

    if not public_url:
        public_url = f"{base_supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"

    logger.info("Constructed PDF public URL: %s", public_url)

    # 3) Send email if user_email is provided
    if user_email:
        logger.info("Sending PDF link email to %s (report_id=%s)", user_email, report_id)
        _send_email_via_gmail(
            to_email=user_email,
            pdf_url=public_url,
            from_email="noreply@righthandoperation.com",
            subject="Your PDF is ready!",
            body_prefix="Hello!"
        )
    else:
        logger.info("No user_email provided; skipping email send.")

    return {
        "storage_path": storage_path,
        "public_url": public_url
    }