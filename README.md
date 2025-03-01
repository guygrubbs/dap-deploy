# GFV Investment Readiness Report System

This repository contains a **GFV Investment Readiness Report** generation system, leveraging **GPT‑4** AI agents, a FastAPI application for orchestration, a PostgreSQL database (or another relational DB) for persistence, **Supabase** as an external notification layer, and **Google Cloud Storage** (GCS) for final PDF file storage. It implements a **Tier‑2–based** template for generating comprehensive reports with the following sections:

1. Executive Summary & Investment Rationale  
2. Market Opportunity & Competitive Landscape  
3. Financial Performance & Investment Readiness  
4. Go‑To‑Market Strategy & Customer Traction  
5. Leadership & Team  
6. Investor Fit, Exit Strategy & Funding Narrative  
7. Final Recommendations & Next Steps  

Using AI agents, the system dynamically generates content for each report section, stores it in a relational database, notifies Supabase upon completion, and provides a signed URL for PDF download from GCS. This README outlines project structure, necessary setup steps, and GCP deployment guidelines.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Folder & File Structure](#folder--file-structure)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
  - [Database Migrations (Optional)](#database-migrations-optional)
- [Google Cloud Deployment](#google-cloud-deployment)
  - [1. Google Cloud Platform Setup](#1-google-cloud-platform-setup)
  - [2. Building & Pushing Docker Image](#2-building--pushing-docker-image)
  - [3. Deploying to Cloud Run](#3-deploying-to-cloud-run)
  - [4. Setting Environment Variables on Cloud Run](#4-setting-environment-variables-on-cloud-run)
  - [5. Post-Deployment Verification](#5-post-deployment-verification)
- [Integration with Supabase & GCS](#integration-with-supabase--gcs)
  - [Supabase Configuration](#supabase-configuration)
  - [Google Cloud Storage](#google-cloud-storage)
- [API Usage](#api-usage)
  - [Authentication](#authentication)
  - [Core Endpoints](#core-endpoints)
  - [Example Client Calls](#example-client-calls)
- [Front-End Integration](#front-end-integration)
- [Troubleshooting & Logs](#troubleshooting--logs)
- [License](#license)

---

## Architecture Overview

1. **FastAPI**: Exposes endpoints for creating and retrieving GFV Investment Readiness Reports.  
2. **Database**: Stores reports and report sections in a relational schema (`Report`, `ReportSection`).  
3. **GPT‑4 AI Agents**: Dynamically generate Tier‑2 section content based on user context or data.  
4. **Orchestrator**: Manages calls to AI agents for each section and consolidates the results.  
5. **Supabase Notifier**: Posts asynchronous notifications to Supabase once a report is complete.  
6. **GCS Module**: Uploads final PDF versions of the report to Google Cloud Storage and generates signed URLs for download.  
7. **Front-End**: Consumes the API endpoints to request or display the final Tier‑2 structured report, including the signed PDF URL.

---

## Folder & File Structure

A simplified structure:

```
app/
  ├─ api/
  │   └─ routes.py        # FastAPI endpoints for /reports, includes Tier‑2 structured responses
  ├─ ai/
  │   ├─ agents.py        # AI Agents with dynamic prompt templates
  │   └─ orchestrator.py  # Orchestrator calls agents for each Tier‑2 section
  ├─ database/
  │   ├─ database.py      # SQLAlchemy engine + session setup
  │   ├─ models.py        # SQLAlchemy models (Report, ReportSection)
  │   └─ crud.py          # CRUD operations for creating/updating/fetching reports
  ├─ notifications/
  │   └─ supabase_notifier.py  # Sends async upserts to Supabase, includes final report JSON
  ├─ storage/
  │   └─ gcs.py           # Upload to GCS, generate signed URLs
  └─ ...
pdfgenerator.py           # Generates PDFs from Tier‑2 report data
main.py                   # FastAPI entry point
README.md                 # This document
```

---

## Prerequisites

- **Python 3.8+**  
- **Poetry** or **pip** for dependency management  
- **PostgreSQL** or another SQL‑compatible RDBMS  
- **GCP Project** with Cloud Storage and (optionally) Cloud Run / Google Container Registry  
- **Supabase** project (with table `reports` or similar for receiving upserts)

---

## Environment Variables

The system relies heavily on environment variables for secure configuration:

1. `DATABASE_URL`: SQLAlchemy connection string (e.g., `postgresql://user:pass@hostname:5432/dbname`).  
2. `SUPABASE_URL`: Supabase project URL.  
3. `SUPABASE_SERVICE_KEY`: Supabase “service role” key with permissions to upsert data.  
4. `REPORTS_BUCKET_NAME`: Name of the GCS bucket (e.g., `my-reports-bucket`).  
5. `OPENAI_API_KEY`: GPT‑4 / OpenAI API key (if using directly).  
6. (Optional) `GOOGLE_CLOUD_PROJECT` + GCP service credentials if needed for local.  

---

## Local Development

1. **Clone Repo & Install Dependencies**  
   ```bash
   git clone https://github.com/your-org/gfv-investment-readiness.git
   cd gfv-investment-readiness
   pip install -r requirements.txt
   ```
   or  
   ```bash
   poetry install
   ```

2. **Set Environment Variables**  
   Create a `.env` file (or export vars) with the required variables:
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:5432/db"
   export SUPABASE_URL="https://xyzcompany.supabase.co"
   export SUPABASE_SERVICE_KEY="super-secret-key"
   export REPORTS_BUCKET_NAME="my-reports-bucket"
   export OPENAI_API_KEY="sk-..."
   # etc.
   ```

3. **Start FastAPI**  
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080
   ```
   The API is now running at `http://localhost:8080`.

### Database Migrations (Optional)

If using Alembic or another tool, ensure your DB schema is up to date:

```bash
alembic upgrade head
```

You may also manually create tables from the `models.py` definitions:

```python
# Inside a small script or Python REPL:
from app.database.database import Base, engine
Base.metadata.create_all(bind=engine)
```

---

## Google Cloud Deployment

There are multiple GCP deployment strategies (Cloud Run, GKE, etc.). Below is an example using **Cloud Run**:

### 1. Google Cloud Platform Setup

1. **Enable Cloud Run** & **Cloud Build** in your GCP project.  
2. **Create** or **use** an existing container registry (Artifact Registry or Container Registry).  
3. **Grant** the appropriate roles to your service account for GCS read/write if needed.

### 2. Building & Pushing Docker Image

Include a `Dockerfile` at the root. A simple example:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Build & Push** to GCR/Artifact Registry:
```bash
# Build
docker build -t gcr.io/your-project-id/gfv-report-app:v1 .

# Push to registry
docker push gcr.io/your-project-id/gfv-report-app:v1
```

### 3. Deploying to Cloud Run
```bash
gcloud run deploy gfv-report-service \
  --image gcr.io/your-project-id/gfv-report-app:v1 \
  --platform managed \
  --region your-region \
  --allow-unauthenticated
```
Replace `your-region` with a valid region (e.g., `us-central1`).

### 4. Setting Environment Variables on Cloud Run

Use the Cloud Console or the CLI:
```bash
gcloud run services update gfv-report-service \
  --update-env-vars DATABASE_URL="..." \
  --update-env-vars SUPABASE_URL="..." \
  --update-env-vars SUPABASE_SERVICE_KEY="..." \
  --update-env-vars REPORTS_BUCKET_NAME="..." \
  --update-env-vars OPENAI_API_KEY="..."
```

### 5. Post-Deployment Verification

1. Check Cloud Run logs in GCP Console to confirm startup success.  
2. Test endpoints using the service URL returned by Cloud Run, e.g. `https://gfv-report-service-xxx.run.app/health`.

---

## Integration with Supabase & GCS

### Supabase Configuration

1. Create a **`reports`** table with columns such as `report_id` (PK), `report_data` (JSONB), `status`, `pdf_url`, etc.  
2. The **`supabase_notifier.py`** module upserts data into this table.  
3. **Service Key**: Ensure you use the service role key in `SUPABASE_SERVICE_KEY` so you can upsert rows.

### Google Cloud Storage

1. Create a GCS bucket (e.g., `my-reports-bucket`).  
2. Grant your service account permission to upload objects (e.g., `roles/storage.objectAdmin`).  
3. The `gcs.py` module handles uploading PDFs and generating signed URLs for time-limited download access.

---

## API Usage

### Authentication

- The example uses a **static token** for demonstration. Real systems should implement JWT or other OAuth2 flows.  
- Provide a Bearer token `expected_static_token` in request headers.  

### Core Endpoints

| Endpoint                           | Method | Description                                                                      | Auth Required |
|------------------------------------|--------|----------------------------------------------------------------------------------|--------------|
| `/api/reports`                     | `POST` | Creates a new report generation request (stub in example)                        | Yes          |
| `/api/reports/{report_id}`         | `GET`  | Retrieves metadata for a given report (Tier‑2 sections, PDF URL if completed)    | Yes          |
| `/api/reports/{report_id}/content` | `GET`  | Retrieves the **content** (sections array) for a given report.                   | Yes          |
| `/api/reports/{report_id}/status`  | `GET`  | Retrieves the **status** and progress for a given report.                        | Yes          |
| `/health`                          | `GET`  | A simple health check endpoint.                                                  | No           |

### Example Client Calls

Use any HTTP client (e.g., `curl`, Postman, or a front‑end app).

```bash
curl -X GET \
  -H "Authorization: Bearer expected_static_token" \
  "https://your-cloudrun-url.run.app/api/reports/123"
```

```json
{
  "report_id": 123,
  "status": "completed",
  "sections": [
    {
      "id": "section_1",
      "title": "Executive Summary & Investment Rationale",
      "content": "Full text of section 1..."
    },
    ...
  ],
  "signed_pdf_download_url": "https://storage.googleapis.com/..."
}
```

---

## Front-End Integration

1. **Authorization**: The front end must supply the correct Bearer token (or real OAuth tokens if extended).  
2. **Report Creation**: The front end can call a `POST /api/reports` endpoint to initiate generation.  
3. **Polling**: The front end can poll `/api/reports/{report_id}/status` to check if the report is done.  
4. **Display Tier‑2**: Once completed, the front end can fetch `/api/reports/{report_id}` (or `content`) to display each section.  
5. **Download PDF**: If needed, the user can click the **signed PDF** URL returned in the JSON. Signed URLs typically expire, so a new link may be requested if the time window lapses.

---

## Troubleshooting & Logs

1. **Cloud Run Logs**: In GCP Console, navigate to **Cloud Run** → your service → “Logs” to view streaming logs.  
2. **Supabase Notification Failures**: If `_notify_supabase_final_report` fails, logs are printed with error details; the code retries up to a configured maximum.  
3. **Database**: Ensure your `DATABASE_URL` is correct. Check `psql` or your DB logs if you see connection issues.  
4. **OpenAI / GPT**: Ensure you have a valid API key in `OPENAI_API_KEY`. If not, AI generation calls may fail.  
5. **Bucket Permissions**: If PDF uploads fail, confirm the GCS role `roles/storage.objectAdmin` or similar is granted to your service account.

---

## License

(If applicable) This code base may be provided under MIT, Apache, or any license your organization uses. Include the appropriate LICENSE file if needed.