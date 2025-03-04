Below is an **example `README.md`** that consolidates all the updates and best practices we’ve covered for your backend. It describes how to **deploy**, **test**, and **integrate** the system, referencing **GCP**, **Supabase**, **PDF generation**, **AI orchestration**, and more.

Feel free to modify the sections and wording to match your organization’s naming conventions, secrets management, and actual deployment flow.

---

# GFV Investment Readiness Report Backend

A FastAPI-based backend for generating **GFV Tier-2 Investment Readiness** reports, integrating:

- **OpenAI** for AI-generated report sections
- **Supabase** for storing pitch decks, final JSON data, or user authentication
- **Postgres** (SQLAlchemy) for local storage of “reports” and “sections”
- **Google Cloud Storage (GCS)** for PDF uploads & signed URLs
- **Vertex AI Matching Engine** (optional) for vector-based retrieval

## Table of Contents

1. [Features & Architecture](#features--architecture)  
2. [Folder Structure](#folder-structure)  
3. [Environment Variables](#environment-variables)  
4. [Setup & Installation](#setup--installation)  
5. [Local Development](#local-development)  
6. [Deployment (GCP Example)](#deployment-gcp-example)  
7. [API Endpoints](#api-endpoints)  
8. [Supabase Integration](#supabase-integration)  
9. [Pitch Deck Handling](#pitch-deck-handling)  
10. [PDF Generation & Final Report Flow](#pdf-generation--final-report-flow)  
11. [Testing & Verification](#testing--verification)  
12. [Contributing](#contributing)

---

## 1. Features & Architecture

- **FastAPI** provides a RESTful API for creating and generating reports.
- **AI Orchestrator** calls multiple “AI Agent” classes (OpenAI’s ChatCompletion) to produce the 7 Tier‑2 sections:
  1) Executive Summary & Investment Rationale  
  2) Market Opportunity & Competitive Landscape  
  3) Financial Performance & Investment Readiness  
  4) Go-To-Market Strategy & Customer Traction  
  5) Leadership & Team  
  6) Investor Fit & Funding Narrative  
  7) Final Recommendations & Next Steps
- **Local Postgres**: The code uses SQLAlchemy to store and retrieve “reports” and “report_sections.”
- **Supabase** is used for:
  - Storing or retrieving pitch decks (PDFs).
  - Optionally upserting final Tier‑2 data into a “reports” table for external dashboards or integration.
- **GCS** is used to store the final PDF, with a signed URL for limited-time access.
- **Vertex AI** (optional) to augment the AI generation with chunk retrieval from pitch decks or other documents.

---

## 2. Folder Structure

A simplified structure (folders may vary):

```
├── app
│   ├── api
│   │   ├── ai
│   │   │   ├── agents.py          # GPT-4 AI Agents for each Tier-2 section
│   │   │   ├── orchestrator.py    # Orchestrates generation, calling each agent
│   │   ├── router.py              # FastAPI routes (create, generate, retrieve report)
│   │   ├── schemas.py             # Pydantic models for request/response
│   │   └── ...
│   ├── database
│   │   ├── crud.py                # CRUD ops (create_report, get_report, update status, etc.)
│   │   ├── database.py            # SQLAlchemy engine, SessionLocal, Base
│   │   ├── models.py              # SQLAlchemy models (Report, ReportSection)
│   ├── matching_engine
│   │   ├── matching_engine_setup.py  # Creates & deploys Vertex AI tree-AH index
│   │   ├── embedding_preprocessor.py # Extract text from local PDFs, embed in Vertex AI
│   │   ├── retrieval_utils.py        # Query Vertex AI for relevant doc chunks
│   │   └── supabase_pitchdeck_downloader.py # Example for pulling PDFs from Supabase & embedding
│   ├── main.py                    # FastAPI entrypoint
│   ├── notifications
│   │   ├── supabase_notifier.py   # Example code to post final data to Supabase
│   ├── storage
│   │   └── gcs.py                 # Upload PDFs to GCS, generate signed URLs
│   └── ...
├── deployments
│   ├── cloud_run_deploy.sh
│   └── env.example
├── docker
│   └── Dockerfile
└── docs
    └── ...
```

---

## 3. Environment Variables

Configure these environment variables to suit your environment:

| Variable                          | Description                                                          | Default / Example                                                                    |
|----------------------------------|----------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| `DATABASE_URL`                    | Postgres connection for local DB                                     | `postgresql://user:password@db.host:5432/dbname`                                    |
| `SUPABASE_URL`                    | Supabase project URL                                                 | `https://xyzcompany.supabase.co`                                                     |
| `SUPABASE_SERVICE_KEY`            | Supabase service role key                                            | `some-long-secret`                                                                   |
| `OPENAI_API_KEY`                  | Your OpenAI API key for ChatCompletion                              | *Required* (no default)                                                              |
| `REPORTS_BUCKET_NAME`             | GCS bucket name for PDFs                                            | `my-reports-bucket`                                                                  |
| `STATIC_API_TOKEN`                | A static token for dev or PoC auth                                   | `expected-static-token`                                                              |
| `VERTEX_ENDPOINT_RESOURCE_NAME`   | Vertex AI Matching Engine endpoint (optional)                       | `projects/PROJECT_ID/locations/us-central1/indexEndpoints/ENDPOINT_ID`               |
| `VERTEX_DEPLOYED_INDEX_ID`        | The deployed index ID in Vertex AI                                  | `my_vector_index_deployed`                                                           |
| `MAX_UPLOAD_SIZE_MB`              | (Optional) a max upload size used for your logic                    | `25`                                                                                 |
| `GOOGLE_APPLICATION_CREDENTIALS`  | JSON service account file path (if not using default creds)         | `~/keys/my-gcp-creds.json`                                                           |

---

## 4. Setup & Installation

1. **Clone** this repo:
   ```bash
   git clone https://github.com/yourorg/gfv-investment-backend.git
   cd gfv-investment-backend
   ```
2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install** dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Set** environment variables. For local dev, place them in a `.env` file:
   ```env
   DATABASE_URL=postgresql://...
   SUPABASE_URL=...
   SUPABASE_SERVICE_KEY=...
   OPENAI_API_KEY=...
   REPORTS_BUCKET_NAME=my-reports-bucket
   STATIC_API_TOKEN=expected-static-token
   ```
   Then run:
   ```bash
   export $(cat .env | xargs)
   ```

5. **Initialize** the database (if you want auto table creation):
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   The `@app.on_event("startup")` in `main.py` calls `init_db()`.

---

## 5. Local Development

- **Run the server**:
  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
- Access the **interactive docs** at:  
  [http://localhost:8000/docs](http://localhost:8000/docs)

- **Authentication**: By default, you must pass a Bearer token in requests:
  ```http
  Authorization: Bearer expected-static-token
  ```
  or the value of `STATIC_API_TOKEN` if changed.

---

## 6. Deployment (GCP Example)

1. **Dockerize** your app by creating a `Dockerfile`. For example:

   ```dockerfile
   FROM python:3.10-slim

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . /app

   EXPOSE 8080
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
   ```

2. **Build** and push the Docker image to **Google Container Registry** or **Artifact Registry**:
   ```bash
   docker build -t gcr.io/PROJECT_ID/gfv-backend:latest .
   docker push gcr.io/PROJECT_ID/gfv-backend:latest
   ```
3. **Deploy** to **Cloud Run**:
   ```bash
   gcloud run deploy gfv-backend \
     --image gcr.io/PROJECT_ID/gfv-backend:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars DATABASE_URL=...,REPORTS_BUCKET_NAME=...,OPENAI_API_KEY=...
   ```
4. **Cloud Logging**: The code automatically sets up structured logging if you run on GCP.

---

## 7. API Endpoints

### `POST /api/reports`
Create a new report record (status = “pending”).

Body example:
```json
{
  "user_id": "abc123",
  "startup_id": "startup-xyz",
  "report_type": "investment_readiness",
  "title": "My GFV Report",
  "parameters": {
    "pitchdeck_link": "https://xyzcompany.supabase.co/storage/v1/object/public/pitchdecks/demo.pdf",
    "industry": "FinTech"
  }
}
```

### `POST /api/reports/{report_id}/generate`
Generates all 7 Tier‑2 sections using the AI agents, updates DB, optionally creates a PDF & uploads to GCS, then notifies Supabase.

### `GET /api/reports/{report_id}`
Retrieves metadata (title, status, creation times) and final sections if available.

### `GET /api/reports/{report_id}/content`
Returns a simpler structure focusing on the text content of each section, plus a `signed_pdf_download_url` if it exists.

### `GET /api/reports/{report_id}/status`
Quickly check the status & progress of a report generation.

---

## 8. Supabase Integration

Two main ways the backend integrates with Supabase:

1. **Pitch Deck Storage**: You can store pitch decks in a “pitchdecks” bucket. The link is included in the `parameters` or a dedicated field, so the orchestrator can reference it.
2. **Final Report Data**: The code (e.g., `supabase_notifier.py`) calls:
   ```python
   supabase.table("reports").upsert({...}).execute()
   ```
   once the final Tier‑2 sections or PDF link is ready. This means you can view or parse the final data in a “reports” table inside Supabase.

---

## 9. Pitch Deck Handling

1. **Upload** the PDF pitch deck to Supabase Storage:
   - Typically `supabase.storage.from_("pitchdecks").upload("some-file.pdf", fileData)`.
2. **Pass** the resulting URL to the backend in the `parameters` (or a `pitchdeck_link` field).
3. If you want to **embed** that deck’s text in the final AI context, you can run code in the orchestrator to download & parse it. Or you can store it as part of “retrieved_context.”

---

## 10. PDF Generation & Final Report Flow

- **`pdfgenerator.py`** uses `FPDF` to build a nicely formatted PDF from the 7 Tier‑2 sections.
- **`gcs.py`** handles:
  - `upload_pdf(report_id, pdf_data)` → Uploading the in-memory bytes to GCS.
  - `generate_signed_url(blob_name, expiration=3600)` → Returning a temporary link.
  - `finalize_report_with_pdf(...)` → Combines PDF upload, URL creation, and calls `notify_supabase_final_report(...).`

**Flow**:
1. `generate_full_report` endpoint triggers the AI orchestration.  
2. The final text is stored in local DB.  
3. A PDF is generated from those sections.  
4. The PDF is uploaded to GCS.  
5. A signed URL is created.  
6. The code upserts final data (including the PDF link) to Supabase.

---

## 11. Testing & Verification

1. **Unit Tests**:  
   - You can write FastAPI tests using `pytest` and `TestClient`.  
   - Test each endpoint (`POST /reports`, etc.) to ensure the DB updates.

2. **Integration Tests**:  
   - In a staging environment with real **Supabase** + **GCS** + **OpenAI** credentials.  
   - Check a sample pitch deck is used to produce final sections. Confirm the PDF link is valid.

3. **Monitoring**:  
   - Inspect the logs in Cloud Logging if deployed on GCP.  
   - Validate that PDF uploads appear in the specified GCS bucket and that `supabase_notifier.py` entries appear in your “reports” table in Supabase.

---

## 12. Contributing

1. **Fork** or create a branch.  
2. Submit pull requests with detailed commit messages.  
3. Follow Pythonic style (PEP 8).  
4. Use docstrings for new endpoints.  
5. If adding new environment variables, update `.env.example` and the table in this README.

---

### Final Notes

- **Security**: If you want production-level auth, replace the `STATIC_API_TOKEN` approach with real **JWT** or **Supabase Auth** checks in `verify_token()`.  
- **Token Limits**: The OpenAI GPT-3.5 model has a ~4K token limit, GPT-4 might have 8K or 32K. If you pass large pitch decks or retrieval contexts, chunk or summarize them first.  
- **Performance**: AI calls can be time-consuming. For heavy usage, you might add a task queue (Celery or RQ) to handle the generation in the background.

---

That’s it! By following this **README**, you should be able to **deploy**, **test**, and **integrate** the GFV Tier-2 backend with **Lovable (Supabase)**, GCS, and OpenAI. If you have any questions or further customizations, refer to the individual modules in `app/` or open an issue in your repository.