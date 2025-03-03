# GFV Investment Readiness Report System

This repository contains a **GFV Investment Readiness Report generation system**, leveraging **GPT‑4** AI agents, a **FastAPI** application for orchestration, a **PostgreSQL** database (or another SQL-compatible DB) for persistence, **Supabase** as an optional external notification layer, **Google Cloud Storage (GCS)** for final PDF file storage, and **Google Vertex AI Matching Engine** for vector-based retrieval. The system implements a **Tier‑2–based** template that generates comprehensive reports in 7 major sections:

1. **Executive Summary & Investment Rationale**  
2. **Market Opportunity & Competitive Landscape**  
3. **Financial Performance & Investment Readiness**  
4. **Go-To-Market (GTM) Strategy & Customer Traction**  
5. **Leadership & Team**  
6. **Investor Fit, Exit Strategy & Funding Narrative**  
7. **Final Recommendations & Next Steps**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)  
2. [Folder & File Structure](#folder--file-structure)  
3. [Prerequisites](#prerequisites)  
4. [Environment Variables](#environment-variables)  
5. [Local Development](#local-development)  
6. [Database Migrations (Optional)](#database-migrations-optional)  
7. [Google Cloud Deployment](#google-cloud-deployment)  
8. [Integration with Supabase & GCS](#integration-with-supabase--gcs)  
9. [Vector-Based Document Retrieval (Vertex AI)](#vector-based-document-retrieval-vertex-ai)  
10. [API Usage](#api-usage)  
11. [Code Module References](#code-module-references)  
12. [Troubleshooting & Logs](#troubleshooting--logs)  
13. [License](#license)  

---

## Architecture Overview

1. **FastAPI**:  
   - Exposes endpoints (`/api/reports`, etc.) to create or retrieve GFV Investment Readiness Reports.  
   - Includes an orchestrator route to generate all 7 Tier-2 sections with GPT-4.  

2. **Database**:  
   - Stores reports and sections in a relational schema.  
   - Handles parameters, user references, status, timestamps, etc.

3. **GPT-4 AI Agents**:  
   - Dynamically generate each Tier-2 section.  
   - Subheadings are spelled out in prompt templates.

4. **Orchestrator**:  
   - Coordinates retrieving relevant doc chunks from Vertex AI, calls each GPT-4 agent, assembles a final dictionary.  
   - Called by a “generate” endpoint in `router.py`.

5. **Supabase** (Optional):  
   - If storing pitch decks or final statuses.  
   - `supabase_notifier.py` can log final data asynchronously.

6. **Google Cloud Storage (GCS)** (Optional):  
   - `gcs.py` handles final PDF uploads, signed URLs.  
   - Tied in if you want a PDF version of the final Tier-2 report.

7. **Vertex AI Matching Engine** (Optional):  
   - Stores pitch deck embeddings, maturity models, or market analysis.  
   - `retrieval_utils.py` fetches relevant doc chunks, appended to GPT-4 prompts.

---

## Folder & File Structure

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

## Prerequisites

- **Python 3.8+**  
- **Poetry** or **pip** for dependency management  
- **PostgreSQL** or another SQL-compatible DB  
- **OpenAI** API key for GPT-4 usage  
- **Google Cloud Project** with Vertex AI, Cloud Storage, and optionally Cloud Run  
- **Supabase** project if you want doc storage or notifications  
- PyMuPDF (`pymupdf`) or pdfminer for PDF extraction  
- google-cloud-aiplatform for Vertex AI calls

---

## Environment Variables

- `DATABASE_URL` e.g. `postgresql://user:pass@host:5432/dbname`  
- `OPENAI_API_KEY` for GPT-4  
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (if using Supabase)  
- `REPORTS_BUCKET_NAME` (if using GCS to store PDFs)  
- `VERTEX_ENDPOINT_RESOURCE_NAME`, `VERTEX_DEPLOYED_INDEX_ID` (if using Vertex AI retrieval)  
- etc.

---

## Local Development

1. **Clone & Install**  
   ```bash
   git clone https://github.com/your-org/gfv-investment-readiness.git
   cd gfv-investment-readiness
   pip install -r requirements.txt
   ```
   or:
   ```bash
   poetry install
   ```
2. **Set** environment variables (`DATABASE_URL`, `OPENAI_API_KEY`, etc.).  
3. **Start** FastAPI:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080
   ```
   Then visit [http://localhost:8080](http://localhost:8080).

---

## Database Migrations (Optional)

If using Alembic or another migration tool:

```bash
alembic upgrade head
```

Or manually create tables from the SQLAlchemy models:

```python
from app.database.database import init_db
init_db()  # calls Base.metadata.create_all(bind=engine)
```

---

## Google Cloud Deployment

A typical approach is **Cloud Run**:

1. **Enable** Cloud Run & Vertex AI in your GCP project.  
2. **Build & Push** Docker:
   ```bash
   docker build -t gcr.io/YOUR_PROJECT_ID/gfv-report-app:v1 .
   docker push gcr.io/YOUR_PROJECT_ID/gfv-report-app:v1
   ```
3. **Deploy**:
   ```bash
   gcloud run deploy gfv-report-service \
     --image gcr.io/YOUR_PROJECT_ID/gfv-report-app:v1 \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```
4. **Set** environment variables for DB, OpenAI, Vertex AI, etc.

---

## Integration with Supabase & GCS

- **Supabase**:  
  - `supabase_pitchdeck_downloader.py` can show how to fetch a pitch deck from a Supabase bucket, embed it in Vertex AI.  
  - `supabase_notifier.py` can post final report data or statuses back to Supabase.

- **GCS**:  
  - `gcs.py` has `upload_pdf(...)` and `generate_signed_url(...)` for storing final PDFs.  
  - Example usage: `finalize_report_with_pdf(...)` shows how you might tie it all together.

---

## Vector-Based Document Retrieval (Vertex AI)

- **`matching_engine_setup.py`**: Creates a tree-AH index with streaming updates. Typically run once.  
- **`embedding_preprocessor.py`**: Extract text from local PDF, embed with OpenAI, upsert vectors to Vertex AI.  
- **`retrieval_utils.py`**:  
  - `retrieve_relevant_chunks(...)` performs approximate nearest neighbor queries for relevant text.  
  - `build_context_from_matches(...)` merges them into a chunk for GPT-4 prompts.

---

## API Usage

By default, the **router** is prefixed with `/api`, so:

1. **`POST /api/reports`**: Create a new “report stub.”  
2. **`POST /api/reports/{report_id}/generate`**: Runs the orchestrator-based GPT-4 generation for all 7 sections.  
3. **`GET /api/reports/{report_id}`**: Retrieve the final metadata & stored sections.  
4. **`GET /api/reports/{report_id}/content`**: Retrieve the Tier-2 content specifically.  
5. **`GET /api/reports/{report_id}/status`**: Check generation status (pending, completed, etc.).

**Health Check**: `GET /health` returns `{"status": "ok"}`.

---

## Code Module References

Below is a quick map of **where** each main file fits and what it does:

1. **`app/main.py`**  
   - FastAPI entrypoint.  
   - Configures logging, middlewares, DB init.  
   - Defines a `verify_token(...)` stub.  
   - Includes `router.py` with prefix `/api`.

2. **`app/api/router.py`**  
   - Declares `POST /reports`, `POST /reports/{report_id}/generate`, etc.  
   - Calls `crud.py` for DB ops, `orchestrator.py` for GPT-4 generation.  
   - Returns typed models from `schemas.py`.

3. **`app/api/schemas.py`**  
   - Pydantic models for request (`CreateReportRequest`) and responses (`ReportResponse`, etc.).  
   - Ensures consistent types (title, user_id, sections, etc.).

4. **`app/api/ai/orchestrator.py`**  
   - `generate_report(request_params)`: Orchestrates GPT-4 calls.  
   - Optionally calls `retrieve_relevant_chunks(...)` from `retrieval_utils.py`.  
   - Instantiates 7 agents from `agents.py`, assembles a final dict.

5. **`app/api/ai/agents.py`**  
   - GPT-4 classes (one per Tier-2 section).  
   - Each has a `prompt_template` referencing subheadings.  
   - `BaseAIAgent` calls `openai.ChatCompletion.create(model="gpt-4")`.

6. **`app/database/crud.py`**  
   - Create/fetch/update logic for `Report` and `ReportSection`.  
   - `create_report_entry(...)`, `update_report_status(...)`, `update_report_sections(...)`, etc.

7. **`app/database/database.py`**  
   - Sets up `engine`, `SessionLocal`, `Base`.  
   - `init_db()` to create tables.  

8. **`app/database/models.py`**  
   - Defines `Report` and `ReportSection` SQLAlchemy models.  
   - Relationship for cascade deletion.

9. **`app/matching_engine/*`**  
   - `matching_engine_setup.py`: Creates & deploys the Vertex AI index.  
   - `embedding_preprocessor.py`: Embeds a local PDF into that index.  
   - `retrieval_utils.py`: Queries the index for relevant doc chunks.  
   - `supabase_pitchdeck_downloader.py`: If you store pitch decks in Supabase, an example script to embed them.

10. **`app/notifications/supabase_notifier.py`**  
    - Example code to post final Tier-2 data or partial statuses to a `reports` table in Supabase.

11. **`app/storage/gcs.py`**  
    - Functions to `upload_pdf(...)` and `generate_signed_url(...)` in GCS.  
    - Optionally used if final PDF outputs are needed.

---

## Troubleshooting & Logs

1. **Cloud Logs**: If running on Cloud Run or GCP, logs are shipped to Cloud Logging (since `google.cloud.logging.Client().setup_logging()` is used).  
2. **Supabase**: Check the `reports` table if you upsert final data.  
3. **Vertex AI**: Confirm `VERTEX_ENDPOINT_RESOURCE_NAME` and `VERTEX_DEPLOYED_INDEX_ID` match your index.  
4. **OpenAI**: Ensure `OPENAI_API_KEY` is valid.  
5. **DB**: If local dev, confirm `DATABASE_URL`. For production, set it in your environment (Cloud Run env vars, etc.).

---

## License

MIT