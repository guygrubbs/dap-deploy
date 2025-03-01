#!/bin/bash
# This shell script deploys the containerized FastAPI app to Cloud Run.
# Adjust the following variables with your actual project values.
SERVICE_NAME="report-generation-service"
IMAGE_URL="gcr.io/your-project-id/report-generation-service:latest"
REGION="us-central1"
CLOUD_SQL_INSTANCE="your-project-id:us-central1:your-sql-instance"

# IMPORTANT: Set your environment variables securely.
# You can use Secret Manager or pass them via the CLI to avoid hard-coding secrets.
# The following environment variables must be defined:
#   - OPENAI_API_KEY: Your OpenAI API key.
#   - SUPABASE_URL: Your Supabase project URL.
#   - SUPABASE_SERVICE_KEY: Your Supabase service role key (for write operations).
#   - DATABASE_URL: Yo#!/bin/bash
# This shell script deploys the containerized FastAPI app to Cloud Run.

# ------------------------------------------------------------------------------
# REQUIRED CONFIGURATION
# ------------------------------------------------------------------------------
# Adjust the following variables with the appropriate values for your GCP project,
# Docker image, Cloud SQL instance, and any other relevant details.

SERVICE_NAME="report-generation-service"
IMAGE_URL="gcr.io/your-project-id/report-generation-service:latest"
REGION="us-central1"
CLOUD_SQL_INSTANCE="your-project-id:us-central1:your-sql-instance"

# ------------------------------------------------------------------------------
# DEPLOYMENT NOTES
# ------------------------------------------------------------------------------
# 1. The --add-cloudsql-instances flag binds the specified Cloud SQL instance(s)
#    to the service, enabling the use of Unix domain sockets for connections.
# 2. The --no-allow-unauthenticated flag restricts public access; only
#    authenticated identities can invoke the service (unless you add further
#    IAM policy to allow specific roles).
# 3. Environment variables can be set here via --update-env-vars, or you can
#    load them from a separate file or from Secret Manager. This example
#    demonstrates static placeholders only.

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_URL}" \
  --platform managed \
  --region "${REGION}" \
  --add-cloudsql-instances "${CLOUD_SQL_INSTANCE}" \
  --update-env-vars "OPENAI_API_KEY=your_openai_api_key,\
SUPABASE_URL=https://your_supabase_url.supabase.co,\
SUPABASE_SERVICE_KEY=your_supabase_service_key,\
DATABASE_URL=postgresql+psycopg2://db_user:db_password@/dbname?host=/cloudsql/${CLOUD_SQL_INSTANCE},\
REPORTS_BUCKET_NAME=your_reports_bucket" \
  --no-allow-unauthenticated
ur database connection string, e.g.:
#         "postgresql+psycopg2://<db_user>:<db_password>@/dbname?host=/cloudsql/your-project-id:us-central1:your-sql-instance"
#   - REPORTS_BUCKET_NAME: Your Google Cloud Storage bucket name for PDF reports.

gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_URL} \
  --platform managed \
  --region ${REGION} \
  --add-cloudsql-instances ${CLOUD_SQL_INSTANCE} \
  --update-env-vars "OPENAI_API_KEY=your_openai_api_key,SUPABASE_URL=https://your-supabase-url.supabase.co,SUPABASE_SERVICE_KEY=your_supabase_service_key,DATABASE_URL=postgresql+psycopg2://db_user:db_password@/dbname?host=/cloudsql/${CLOUD_SQL_INSTANCE},REPORTS_BUCKET_NAME=your_reports_bucket" \
  --no-allow-unauthenticated
