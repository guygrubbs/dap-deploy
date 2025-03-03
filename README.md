# GFV Investment Readiness Report System

This repository contains a GFV Investment Readiness Report generation system, leveraging GPT‑4 AI agents, a FastAPI application for orchestration, a PostgreSQL database (or another relational DB) for persistence, Supabase as an external notification layer, and Google Cloud Storage (GCS) for final PDF file storage. It implements a Tier‑2–based template for generating comprehensive reports with the following sections:

1. Executive Summary & Investment Rationale  
2. Market Opportunity & Competitive Landscape  
3. Financial Performance & Investment Readiness  
4. Go‑To‑Market Strategy & Customer Traction  
5. Leadership & Team  
6. Investor Fit, Exit Strategy & Funding Narrative  
7. Final Recommendations & Next Steps  

Using AI agents, the system dynamically generates content for each report section, stores it in a relational database, notifies Supabase upon completion, and provides a signed URL for PDF download from GCS.

**_(New)_** Additionally, the system supports uploading **Pitch Decks (PDF, PPT, PPTX)** and **Microsoft Office documents (DOC, DOCX, XLS, XLSX, etc.)**, which can be included as supporting context in the GPT‑4 AI generation process to produce richer and more personalized investment readiness reports.

This README outlines project structure, necessary setup steps, GCP deployment guidelines, and usage instructions (including document upload).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)  
2. [Folder & File Structure](#folder--file-structure)  
3. [Prerequisites](#prerequisites)  
4. [Environment Variables](#environment-variables)  
5. [Local Development](#local-development)  
6. [Database Migrations (Optional)](#database-migrations-optional)  
7. [Google Cloud Deployment](#google-cloud-deployment)  
   1. [Google Cloud Platform Setup](#1-google-cloud-platform-setup)  
   2. [Building & Pushing Docker Image](#2-building--pushing-docker-image)  
   3. [Deploying to Cloud Run](#3-deploying-to-cloud-run)  
   4. [Setting Environment Variables on Cloud Run](#4-setting-environment-variables-on-cloud-run)  
   5. [Post-Deployment Verification](#5-post-deployment-verification)  
8. [Integration with Supabase & GCS](#integration-with-supabase--gcs)  
   1. [Supabase Configuration](#supabase-configuration)  
   2. [Google Cloud Storage](#google-cloud-storage)  
9. [API Usage](#api-usage)  
   1. [Authentication](#authentication)  
   2. [Core Endpoints](#core-endpoints)  
   3. [**_(New)_** Document Upload Usage](#new-document-upload-usage)  
   4. [Example Client Calls](#example-client-calls)  
10. [Front-End Integration](#front-end-integration)  
11. [Troubleshooting & Logs](#troubleshooting--logs)  
12. [License](#license)  

---

## Architecture Overview

1. **FastAPI**: Exposes endpoints for creating and retrieving GFV Investment Readiness Reports, as well as document uploads.  
2. **Database**: Stores reports and report sections in a relational schema (`Report`, `ReportSection`).  
3. **GPT‑4 AI Agents**: Dynamically generate Tier‑2 section content based on user context or data, including **_(New)_** any uploaded Pitch Deck or Office documents.  
4. **Orchestrator**: Manages calls to AI agents for each section, consolidating the results.  
5. **Supabase Notifier**: Posts asynchronous notifications to Supabase once a report is complete (or after a document is uploaded, if applicable).  
6. **GCS Module**:  
   - Uploads final PDF versions of the report to Google Cloud Storage.  
   - Generates signed URLs for download.  
   - **_(New)_** Uploads and manages user Pitch Deck / Office documents for context in AI generation.  
7. **Front-End**: Consumes the API endpoints to request or display the final Tier‑2 structured report (including any relevant context from uploaded documents), and retrieves signed URLs for both final reports and any stored documents.

---

## Folder & File Structure

A simplified structure:

```
├───app
│   │   main.py
│   │
│   ├───api
│   │   │   routes.py
│   │   │   schemas.py
│   │   │
│   │   └───ai
│   │           agents.py
│   │           orchestrator.py
│   │
│   ├───database
│   │       crud.py
│   │       database.py
│   │       models.py
│   │
│   ├───notifications
│   │       supabase_notifier.py
│   │
│   ├───storage
│   │       gcs.py
│   │       pdfgenerator.py
|
├───deployments
│       cloud_run_deploy.sh
│       env.example
│
├───docker
│       Dockerfile
│
└───docs
        iam_configuration.md
        security_configuration.md
```

---

## Prerequisites

- Python 3.8+  
- Poetry or pip for dependency management  
- PostgreSQL or another SQL‑compatible RDBMS  
- GCP Project with Cloud Storage and (optionally) Cloud Run / Google Container Registry  
- Supabase project (with table `reports` or similar for receiving upserts)  
- [LibreOffice](https://www.libreoffice.org/) or similar tool installed for converting Office files (if you plan to process or preview PPT/DOC files on the server).  
- Sufficient GCP Storage configuration to handle potentially large file uploads (Pitch Decks, Office docs).  

---

## Environment Variables

The system relies heavily on environment variables for secure configuration:

- `DATABASE_URL`: SQLAlchemy connection string (e.g., `postgresql://user:pass@hostname:5432/dbname`).  
- `SUPABASE_URL`: Supabase project URL.  
- `SUPABASE_SERVICE_KEY`: Supabase “service role” key with permissions to upsert data.  
- `REPORTS_BUCKET_NAME`: Name of the GCS bucket (e.g., `my-reports-bucket`).  
- `OPENAI_API_KEY`: GPT‑4 / OpenAI API key (if using directly).  
- **_(New)_** `MAX_UPLOAD_SIZE_MB` (Optional): Max file size for document uploads in MB (default could be 25MB, for example).  
- **_(Optional)_** `GOOGLE_CLOUD_PROJECT` + GCP service credentials if needed locally.

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
   export MAX_UPLOAD_SIZE_MB="25"
   # etc.
   ```

3. **Start FastAPI**  
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080
   ```
   The API is now running at [http://localhost:8080](http://localhost:8080).

---

## Database Migrations (Optional)

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

- Enable Cloud Run & Cloud Build in your GCP project.  
- Create or use an existing container registry (Artifact Registry or Container Registry).  
- Grant the appropriate roles to your service account for GCS read/write if needed.

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

Build & Push to GCR/Artifact Registry:

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
  --update-env-vars OPENAI_API_KEY="..." \
  --update-env-vars MAX_UPLOAD_SIZE_MB="25"
```

### 5. Post-Deployment Verification

- Check Cloud Run logs in GCP Console to confirm startup success.  
- Test endpoints using the service URL returned by Cloud Run, e.g. `https://gfv-report-service-xxx.run.app/health`.

---

## Integration with Supabase & GCS

### Supabase Configuration

- Create a `reports` table with columns such as `report_id` (PK), `report_data` (JSONB), `status`, `pdf_url`, etc.  
- The `supabase_notifier.py` module upserts data into this table.  
- **Service Key**: Ensure you use the service role key in `SUPABASE_SERVICE_KEY` so you can upsert rows.

### Google Cloud Storage

- Create a GCS bucket (e.g., `my-reports-bucket`).  
- Grant your service account permission to upload objects (e.g., `roles/storage.objectAdmin`).  
- The `gcs.py` module handles uploading PDFs and generating signed URLs for time-limited download access.  
- It also handles storage for uploaded Pitch Deck / Office documents. Once uploaded, these documents can be accessed by the GPT-4 orchestration logic to enhance the generated report.

---

## API Usage

### Authentication

The example uses a **static token** for demonstration. Real systems should implement JWT or other OAuth2 flows.

Provide a Bearer token `expected_static_token` in request headers:

```
Authorization: Bearer expected_static_token
```

### Core Endpoints

| Endpoint                               | Method | Description                                                                     | Auth Required |
|----------------------------------------|--------|---------------------------------------------------------------------------------|--------------:|
| `/api/reports`                         | POST   | Creates a new report generation request (stub in example)                       | Yes           |
| `/api/reports/{report_id}`            | GET    | Retrieves metadata for a given report (Tier‑2 sections, PDF URL if completed)   | Yes           |
| `/api/reports/{report_id}/content`    | GET    | Retrieves the content (sections array) for a given report.                      | Yes           |
| `/api/reports/{report_id}/status`     | GET    | Retrieves the status and progress for a given report.                           | Yes           |
| `/health`                              | GET    | A simple health check endpoint.                                                 | No            |

If desired, you can also retrieve references to uploaded documents for each report (or a general upload endpoint) depending on your design.

---

### Document Upload Usage

Users can optionally upload **Pitch Decks** (PDF, PPT, PPTX) or **Microsoft Office documents** (DOC, DOCX, XLS, XLSX, etc.) to include additional context when generating reports. The flow typically involves:

1. **Upload Document**  
   - A dedicated endpoint (e.g., `POST /api/reports/{report_id}/upload`) accepts file uploads.  
   - The file is stored in GCS using the configured `REPORTS_BUCKET_NAME`.  
   - A reference to the uploaded file is stored in the database (or in Supabase, depending on your architecture).

2. **AI Generation with Documents**  
   - The orchestrator or GPT-4 logic retrieves the GCS file reference, optionally extracts or parses the file’s text, and passes that text as part of the GPT-4 prompt.  
   - This ensures that the system’s final Tier‑2–based report factors in the content of the Pitch Deck or attached Office document(s).

3. **PDF Conversion / Parsing** (Optional)  
   - If needed, the server may convert Office documents to PDF or plain text using a library or external service (e.g., LibreOffice headless mode).  
   - The extracted text can then be fed to the GPT-4 API for context.

4. **Limits & Validation**  
   - By default, we recommend limiting files to a certain size (`MAX_UPLOAD_SIZE_MB`).  
   - The system may reject extremely large files or certain file types for security reasons.

**Client Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer expected_static_token" \
  -F "file=@/path/to/pitchdeck.pdf" \
  "https://your-cloudrun-url.run.app/api/reports/123/upload"
```
A successful response might return a JSON structure with:
```json
{
  "report_id": 123,
  "uploaded_file": "pitchdeck.pdf",
  "file_gcs_url": "gs://my-reports-bucket/reports/123/pitchdeck.pdf"
}
```
Once uploaded, the user can initiate or re-run the generation process, and GPT-4 will incorporate the newly attached document.

---

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
2. **Report Creation**: The front end calls `POST /api/reports` to initiate generation.  
3. **Document Upload (Optional)**: Before or after creating a report, the front end can call the new upload endpoint with a file form-data request.  
4. **Polling**: The front end can poll `/api/reports/{report_id}/status` to check if the report is finished generating.  
5. **Display Tier‑2**: Once completed, the front end fetches `/api/reports/{report_id}` (or `content`) to display each section.  
6. **Download PDF**: If needed, the user clicks the signed PDF URL returned in the JSON. Signed URLs typically expire, so a new link may be requested if the time window lapses.

---

## Troubleshooting & Logs

1. **Cloud Run Logs**: In GCP Console, navigate to Cloud Run → your service → “Logs” to view streaming logs.  
2. **Supabase Notification Failures**: If `_notify_supabase_final_report` fails, logs are printed with error details; the code retries up to a configured maximum.  
3. **Database**: Ensure your `DATABASE_URL` is correct. Check `psql` or your DB logs if you see connection issues.  
4. **OpenAI / GPT**: Ensure you have a valid API key in `OPENAI_API_KEY`. If not, AI generation calls may fail.  
5. **Bucket Permissions**: If PDF uploads or document uploads fail, confirm the GCS role `roles/storage.objectAdmin` or similar is granted to your service account.  
6. **Document Parsing**: If documents fail to parse, ensure you have the right libraries or system tools (e.g., LibreOffice) installed.

---

## License

(If applicable) This code base may be provided under MIT, Apache, or any license your organization uses. Include the appropriate LICENSE file if needed.


Below is an **updated README** excerpt that reflects the **new Vertex AI Matching Engine–based retrieval** workflow, including references to new files and where they reside in the directory structure. Feel free to merge these sections into your existing README. All newly added or updated sections are marked with **(New)** or **(Updated)** for clarity.

---

# GFV Investment Readiness Report System

This repository contains a GFV Investment Readiness Report generation system, leveraging GPT‑4 AI agents, a FastAPI application for orchestration, a PostgreSQL database (or another relational DB) for persistence, Supabase as an external notification layer, Google Cloud Storage (GCS) for final PDF file storage, **_(New)_** **Google Vertex AI Matching Engine** for vector-based retrieval, and optional pitch deck uploads for added context.

It implements a Tier‑2–based template for generating comprehensive reports with the following sections:

1. Executive Summary & Investment Rationale  
2. Market Opportunity & Competitive Landscape  
3. Financial Performance & Investment Readiness  
4. Go‑To‑Market Strategy & Customer Traction  
5. Leadership & Team  
6. Investor Fit, Exit Strategy & Funding Narrative  
7. Final Recommendations & Next Steps  
**_(New)_** and integrates pitch deck analysis, maturity models, and market research PDFs via embedding-based retrieval for richer context.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)  
2. [Folder & File Structure (Updated)](#folder--file-structure-updated)  
3. [Prerequisites](#prerequisites)  
4. [Environment Variables](#environment-variables)  
5. [Local Development](#local-development)  
6. [Database Migrations (Optional)](#database-migrations-optional)  
7. [Google Cloud Deployment](#google-cloud-deployment)  
8. [Integration with Supabase & GCS](#integration-with-supabase--gcs)  
9. [API Usage](#api-usage)  
10. [Vector-Based Document Retrieval (New)](#vector-based-document-retrieval-new)  
    - [Vertex AI Matching Engine Setup](#vertex-ai-matching-engine-setup)  
    - [Embedding & Indexing Documents](#embedding--indexing-documents)  
    - [Pitch Deck Processing Workflow](#pitch-deck-processing-workflow)  
11. [Troubleshooting & Logs](#troubleshooting--logs)  
12. [License](#license)  

---

## Architecture Overview

1. **FastAPI**: Exposes endpoints for creating and retrieving GFV Investment Readiness Reports, as well as document uploads.  
2. **Database**: Stores reports and report sections in a relational schema (`Report`, `ReportSection`).  
3. **GPT‑4 AI Agents**: Dynamically generate Tier‑2 section content based on user context or data, including any uploaded pitch decks.  
4. **Orchestrator**: Manages calls to AI agents and ensures the system references newly integrated vector-based retrieval.  
5. **Supabase Notifier**: Posts asynchronous notifications to Supabase once a report is complete.  
6. **GCS Module**: Uploads final PDF versions of the report to Google Cloud Storage and generates signed URLs for download.  
7. **Vertex AI Matching Engine (New)**: Stores embeddings of pitch decks, maturity models, and market research PDFs for real-time retrieval.  
8. **Front-End**: Consumes the API endpoints to request or display the final Tier‑2 structured report.

---

## Folder & File Structure (Updated)

Below is a simplified structure with the newly added **`matching_engine`** folder and scripts. (Only core changes shown for brevity.)

```
├───app
│   │   main.py
│   │
│   ├───api
│   │   │   routes.py
│   │   │   schemas.py
│   │   │
│   │   └───ai
│   │           agents.py        # Agents for each report section
│   │           orchestrator.py  # Orchestrator logic
│   │
│   ├───database
│   │       crud.py
│   │       database.py
│   │       models.py
│   │
│   ├───matching_engine  (New)
│   │   │   matching_engine_setup.py   # Creates & deploys Vertex AI Index
│   │   │   embedding_preprocessor.py  # Pre-processes PDFs, pitch decks
│   │   │   retrieval_utils.py         # Utility for searching index & returning snippets
│   │
│   ├───notifications
│   │       supabase_notifier.py
│   │
│   ├───storage
│   │       gcs.py
│   │       pdfgenerator.py
│   │
│   └───__pycache__
│
├───deployments
│       cloud_run_deploy.sh
│       env.example
│
├───docker
│       Dockerfile
│
└───docs
        iam_configuration.md
        security_configuration.md
```

### **(New) `matching_engine_setup.py`**  
- **Location**: `app/matching_engine/matching_engine_setup.py`  
- **Description**: Python script that initializes Google Vertex AI, creates a **tree-AH** approximate nearest neighbor index (dimension=1536), and deploys it to a Matching Engine **Index Endpoint** with streaming updates.  

### **(New) `embedding_preprocessor.py`**  
- **Location**: `app/matching_engine/embedding_preprocessor.py`  
- **Description**: Python script or module that reads PDFs (e.g., pitch decks, maturity models), extracts text with PyMuPDF, creates embeddings using OpenAI’s `text-embedding-ada-002`, then upserts those vectors into the Vertex AI index.  

### **(New) `retrieval_utils.py`**  
- **Location**: `app/matching_engine/retrieval_utils.py`  
- **Description**: Contains functions to query the Vertex AI Matching Engine for relevant text chunks. For example, `match()` calls that retrieve the top-k similar chunks of text to incorporate into prompts for GPT-4 AI agents.  

---

## Prerequisites

- Python 3.8+  
- Poetry or pip for dependency management  
- PostgreSQL or another SQL‑compatible RDBMS  
- GCP Project with Cloud Storage, Cloud Run / Google Container Registry, **(New)** Vertex AI Matching Engine enabled  
- Supabase project (with table `reports` or similar for receiving upserts, plus Storage bucket for pitch decks)  
- [LibreOffice](https://www.libreoffice.org/) or similar tool installed for converting Office files to PDF (if needed)  
- **(New)** `google-cloud-aiplatform` library for interacting with Vertex AI, e.g. `pip install google-cloud-aiplatform`  
- **(New)** `PyMuPDF` (pymupdf) or `pdfminer.six` for PDF extraction, e.g. `pip install pymupdf`

---

## Environment Variables

The system relies heavily on environment variables for secure configuration, plus **(New)** references for Vertex AI:

- `DATABASE_URL`  
- `SUPABASE_URL`  
- `SUPABASE_SERVICE_KEY`  
- `REPORTS_BUCKET_NAME`  
- `OPENAI_API_KEY`  
- **(New)** `GOOGLE_PROJECT_ID` (the GCP project hosting Vertex AI Matching Engine)  
- **(New)** `VERTEX_INDEX_RESOURCE_NAME` (the resource name of your index, e.g. `projects/123/locations/us-central1/indexes/456`)  
- **(New)** `VERTEX_ENDPOINT_RESOURCE_NAME` (the resource name of your index endpoint)

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
   See `env.example` for references and export additional variables (e.g., `GOOGLE_PROJECT_ID`, `VERTEX_INDEX_RESOURCE_NAME`).  
3. **Start FastAPI**  
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080
   ```
   The API is now running at http://localhost:8080.

---

## Database Migrations (Optional)

*... (Existing instructions for Alembic / migrations or `Base.metadata.create_all`) ...*

---

## Google Cloud Deployment

1. **Google Cloud Platform Setup**  
   - Enable Cloud Run, Cloud Build, and Vertex AI Matching Engine in your GCP project.  
   - Create or use an existing container registry (Artifact Registry or Container Registry).  

2. **Building & Pushing Docker Image**  
   *... (Existing instructions) ...*

3. **Deploying to Cloud Run**  
   *... (Existing instructions) ...*

4. **Setting Environment Variables on Cloud Run**  
   *... (Existing instructions + add new environment vars for `VERTEX_INDEX_RESOURCE_NAME` & `VERTEX_ENDPOINT_RESOURCE_NAME`)*

5. **Post-Deployment Verification**  
   *... (Existing instructions) ...*

---

## Integration with Supabase & GCS

*... (Existing instructions) ...*

---

## API Usage

*... (Existing instructions about Core Endpoints, uploading pitch decks, etc.) ...*

---

## Vector-Based Document Retrieval (New)

### Vertex AI Matching Engine Setup

In `app/matching_engine/matching_engine_setup.py`, we have a script that:

1. Initializes the Vertex AI environment (project/location).  
2. Creates a **tree-AH** approximate nearest neighbor index (dimension=1536) with `STREAM_UPDATE` for real-time upserts.  
3. Deploys it to an **Index Endpoint** for queries.

An example usage:

```bash
cd app/matching_engine
python matching_engine_setup.py
```

This script will print the newly created `INDEX_ID` and `INDEX_ENDPOINT_ID`, which you can store in environment variables.

### Embedding & Indexing Documents

In `app/matching_engine/embedding_preprocessor.py`, you’ll see functions to:

1. **Extract PDF text** (e.g., from pitch decks, maturity model).  
2. **Generate embeddings** using OpenAI’s `text-embedding-ada-002`.  
3. **Upsert** the vectors into the Vertex AI Matching Engine index.

For instance:

```bash
python embedding_preprocessor.py --pdf maturity_model.pdf
```

will parse the file, chunk or page-split it, embed each chunk, and upsert it to the index so it’s retrievable.

### Pitch Deck Processing Workflow

When a pitch deck PDF is uploaded to Supabase, you can:

1. **Download** it from Supabase, save it locally as `deck123.pdf`.  
2. **Call** `embedding_preprocessor.py` to index the new pages.  
3. **Query** the index for relevant sections when generating a new report.  

Alternatively, you can embed pitch decks on-the-fly within your FastAPI code if you prefer an automated pipeline. Either way, the new scripts in `app/matching_engine/` handle the logic for referencing Vertex AI’s vector index.

---

## Troubleshooting & Logs

*... (Existing instructions about checking logs, supabase errors, etc.) ...*

---

## License

*(Existing license details, if any.)*

---

**End of Updated README**  

With these changes, you now have instructions and file references for:
- **(New)** `app/matching_engine/matching_engine_setup.py`: Creating & deploying a Vertex AI vector index.  
- **(New)** `app/matching_engine/embedding_preprocessor.py`: Preprocessing PDFs and indexing them in Vertex AI.  
- **(New)** `app/matching_engine/retrieval_utils.py`: Searching the index for relevant content at report generation time.  

This ensures a consistent approach for integrating pitch decks, maturity models, and market analysis PDFs via **embedding-based retrieval** in Google Vertex AI Matching Engine.