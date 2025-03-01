import os
import logging
from datetime import datetime, timedelta
from google.cloud import storage
from google.cloud.exceptions import NotFound, Forbidden, GoogleCloudError

logger = logging.getLogger(__name__)

def upload_pdf(report_id: int, pdf_data: bytes) -> str:
    """
    Upload the generated PDF to a Google Cloud Storage bucket and return
    the unique blob name (storage key) under which it is saved.

    Args:
        report_id (int): Identifier of the report, used to construct a unique filename.
        pdf_data (bytes): Raw byte content of the PDF file.

    Returns:
        str: The blob name where the PDF is stored in GCS.

    Raises:
        ValueError: If REPORTS_BUCKET_NAME is not set in the environment.
        NotFound: If the specified bucket does not exist.
        Forbidden: If insufficient permissions exist to access the bucket.
        GoogleCloudError: For broader errors encountered during storage operations.
        Exception: For any unhandled error cases.
    """
    bucket_name = os.getenv("REPORTS_BUCKET_NAME")
    if not bucket_name:
        logger.error("REPORTS_BUCKET_NAME environment variable is not set.")
        raise ValueError("REPORTS_BUCKET_NAME environment variable is not set.")

    try:
        # Initialize the Cloud Storage client
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # Check if the bucket actually exists (optional but good for clarity)
        if not bucket.exists():
            logger.error("Bucket %s does not exist; cannot upload PDF.", bucket_name)
            raise NotFound(f"Bucket '{bucket_name}' not found.")

        # Generate a unique blob name using the report ID and current UTC timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        blob_name = f"reports/report_{report_id}_{timestamp}.pdf"

        blob = bucket.blob(blob_name)
        blob.upload_from_string(pdf_data, content_type="application/pdf")

        logger.info("Successfully uploaded PDF to GCS with blob name: %s", blob_name)
        return blob_name

    except NotFound as nf:
        logger.error("Bucket or blob not found: %s", str(nf), exc_info=True)
        raise
    except Forbidden as fb:
        logger.error("Insufficient permissions to access bucket: %s", str(fb), exc_info=True)
        raise
    except GoogleCloudError as gce:
        logger.error("Google Cloud Storage error: %s", str(gce), exc_info=True)
        raise
    except Exception as e:
        logger.error("Unexpected error while uploading PDF: %s", str(e), exc_info=True)
        raise


def generate_signed_url(blob_name: str, expiration_seconds: int = 3600) -> str:
    """
    Generate a version 4 signed URL for a PDF file in GCS, allowing time-limited
    external access.

    Args:
        blob_name (str): The name of the blob (file) in GCS.
        expiration_seconds (int): Duration in seconds for which the URL is valid
                                  (default is 3600 seconds = 1 hour).

    Returns:
        str: The generated signed URL for accessing the PDF.

    Raises:
        ValueError: If REPORTS_BUCKET_NAME is not set in the environment.
        NotFound: If the specified bucket or blob does not exist.
        Forbidden: If insufficient permissions exist to generate a signed URL.
        GoogleCloudError: For broader errors encountered during URL generation.
        Exception: For any unhandled error cases.
    """
    bucket_name = os.getenv("REPORTS_BUCKET_NAME")
    if not bucket_name:
        logger.error("REPORTS_BUCKET_NAME environment variable is not set.")
        raise ValueError("REPORTS_BUCKET_NAME environment variable is not set.")

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # Check if the bucket exists before generating the URL
        if not bucket.exists():
            logger.error("Bucket %s does not exist; cannot generate signed URL.", bucket_name)
            raise NotFound(f"Bucket '{bucket_name}' not found.")

        blob = bucket.blob(blob_name)

        # You may also want to check if the blob itself exists if your use case requires it:
        # if not blob.exists():
        #     logger.error("Blob %s not found in bucket %s.", blob_name, bucket_name)
        #     raise NotFound(f"Blob '{blob_name}' not found in bucket '{bucket_name}'.")

        expiration = timedelta(seconds=expiration_seconds)
        signed_url = blob.generate_signed_url(
            expiration=expiration,
            version="v4",
            method="GET",
        )

        logger.info("Signed URL generated successfully for blob: %s", blob_name)
        return signed_url

    except NotFound as nf:
        logger.error("Bucket or blob not found: %s", str(nf), exc_info=True)
        raise
    except Forbidden as fb:
        logger.error("Insufficient permissions to generate signed URL: %s", str(fb), exc_info=True)
        raise
    except GoogleCloudError as gce:
        logger.error("Google Cloud Storage error while generating URL: %s", str(gce), exc_info=True)
        raise
    except Exception as e:
        logger.error("Unexpected error while generating signed URL: %s", str(e), exc_info=True)
        raise
