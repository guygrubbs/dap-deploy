# GFV Investment Readiness Report Backend

This repository provides a **FastAPI-based** backend for generating “Investment Readiness” reports. It integrates:
- **Supabase** (for file storage & optional vector storage / database),
- **OpenAI** (for GPT-based text generation, ephemeral or fine-tuning),
- **Google Cloud** (optional Matching Engine for retrieval-augmented generation; GCS for PDF storage).

> **Key Feature:** You can *ephemerally* include a pitch-deck’s PDF text in the GPT prompt **without** permanently training the model, ensuring data privacy and single-request usage of that deck’s content.

---

## 1. High-Level Architecture

```
Frontend --> (HTTP) --> FastAPI/uvicorn
     \
      --> Supabase (PDF store or DB)
      
FastAPI uses:
- orchestrator.py for orchestrating GPT calls
- GCS for PDF upload (final PDF reports)
- Supabase for downloading pitch decks (if public or via client)
- Optional fine-tuning route to OpenAI
```

1. **Reports** are stored in a `reports` table (PostgreSQL via SQLAlchemy).  
2. **Pitch decks** can come from a public Supabase URL or local file.  
3. **Ephemeral usage** of PDF text merges pitch deck text into GPT prompt.  
4. **Fine-tuning** is optional for static or universal data (market analysis, maturity models, etc.).

---

## 2. Installation & Setup

### 2.1 Clone and Install

```bash
git clone https://github.com/<your-repo>/gfv-investment-readiness.git
cd gfv-investment-readiness

# If using pip:
pip install -r requirements.txt

# If using Docker, see Dockerfile instructions below
docker build -t gfv-backend .
```

### 2.2 Tesseract Installation

To support OCR fallback (for scanned PDFs), install Tesseract at the system level. E.g. on Ubuntu:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```
Also ensure `pytesseract` is in your Python dependencies.

### 2.3 Environment Variables

Create a `.env` or set these in your deployment environment:

| Variable                  | Description                                                             | Required?             |
|--------------------------|-------------------------------------------------------------------------|-----------------------|
| `DATABASE_URL`           | SQLAlchemy-compatible DB URL (PostgreSQL).                             | **Yes** for DB usage  |
| `SUPABASE_URL`           | Supabase project URL (e.g. https://xyzcompany.supabase.co).            | If using Supabase     |
| `SUPABASE_SERVICE_KEY`   | Supabase service role key.                                             | If using Supabase     |
| `OPENAI_API_KEY`         | Your OpenAI API key.                                                   | **Yes** (GPT usage)   |
| `OPENAI_MODEL`           | Model name to use (e.g. `gpt-4` or a fine-tuned ID). Defaults `"gpt-4"`.| Optional             |
| `REPORTS_BUCKET_NAME`    | GCS bucket name for storing final PDFs.                                | If storing in GCS     |
| `VERTEX_ENDPOINT_RESOURCE_NAME` | Matching Engine endpoint (e.g. `projects/.../indexEndpoints/...`). | If using retrieval   |
| `VERTEX_DEPLOYED_INDEX_ID`     | Deployed index ID in Vertex (e.g. `my_deployed_idx`).              | If using retrieval   |
| `STATIC_API_TOKEN`       | Basic token for FastAPI’s `verify_token` auth.                         | Optional             |

---

## 3. Directory Structure

```
app/
  api/
    ai/               # GPT agent definitions + orchestrator
    router.py         # Main FastAPI routes for reports, pitchdecks, etc.
    schemas.py        # Pydantic models
  database/
    models.py         # SQLAlchemy models (Report, ReportSection)
    crud.py           # DB queries (create_report, etc.)
    database.py       # DB init & engine
  matching_engine/
    retrieval_utils.py         # Optional: Vertex AI retrieval
    pdf_to_openai_jsonl.py     # Fine-tuning approach for PDFs
    embedding_preprocessor.py  # Basic PDF->embedding->Vertex
    supabase_pitchdeck_downloader.py  # Another approach for pitchdeck + vertex
  notifications/
    supabase_notifier.py       # Notifies Supabase table about report updates
  storage/
    pdfgenerator.py    # FPDF-based PDF creation
    gcs.py            # GCS upload + signed URLs
  main.py             # FastAPI entry point
```

---

## 4. How It Works

### 4.1 Ephemeral PDF Usage

When generating a report, you can:
1. Provide a `pitch_deck_url` in `report_model.parameters` or your request.  
2. The `/reports/{report_id}/generate` endpoint sees the URL, downloads the PDF, extracts text with OCR fallback.  
3. That text is appended to `request_params["pitch_deck_text"]`.  
4. In `orchestrator.py`, we combine that text with any snippet-based retrieval context.  
5. GPT sees the ephemeral PDF text in the prompt but does NOT store it long-term.

**This means** the pitch-deck data is only used for that single request. No permanent fine-tuning or training.

### 4.2 Fine-Tuning with PDF

If you want to **fine-tune** your model on certain decks or standard docs:
- Use the new route `/pitchdecks/{deck_file}/upload_to_openai` or the script `pdf_to_openai_jsonl.py`.
- That logic downloads a PDF from Supabase, extracts text, splits it into .jsonl records, and optionally uploads to OpenAI with `purpose="fine-tune"`.

**Note**: This is separate from ephemeral usage. Fine-tuning is for universal knowledge you want the model to always retain.

---

## 5. Endpoints & Usage

### 5.1 `/reports [POST]`
Create a new report record in DB. Returns a `report_id`.

#### Request Body (`CreateReportRequest`)
```json
{
  "user_id": "123",
  "startup_id": "456",
  "report_type": "investment_readiness",
  "title": "My Test Report",
  "parameters": {
    "pitch_deck_url": "https://your-supabase-or-public-url"
  }
}
```
**Response**: A `ReportResponse` with ID, status, etc.

### 5.2 `/reports/{report_id}/generate [POST]`
1. Looks up `report_id`.
2. Reads `report_model.parameters["pitch_deck_url"]` (if any).
3. Downloads the PDF, extracts text ephemeral for GPT usage.
4. Calls `generate_report(...)`.
5. Stores the final sections in DB.
6. Optionally builds a PDF, uploads to GCS, returns the final metadata.

**Response**: Full `ReportResponse` with final sections and optional signed PDF URL.

### 5.3 `/pitchdecks/{deck_file}/upload_to_openai [POST]`
- **Offline fine-tuning** approach: 
  1. `deck_file` is the PDF name in a Supabase bucket.  
  2. Downloads the PDF, extracts text, creates `.jsonl`.  
  3. Optionally uploads `.jsonl` to OpenAI for training.  

**Response**: `{"deck_file": ..., "openai_file_id": ...}` or error.

### 5.4 Other /reports GETs
- `/reports/{report_id}` retrieves metadata.  
- `/reports/{report_id}/content` returns the sections.  
- `/reports/{report_id}/status` checks current progress.

---

## 6. Database Schema

**reports** table (via `Report` model):
- `id` (pk), `user_id`, `startup_id`, `report_type`, `title`, `status`, `created_at`, `completed_at`, `pdf_url`, `parameters`.

**report_sections** (via `ReportSection` model):
- `id` (pk), `report_id` (fk), `section_name`, `content`, `created_at`.

---

## 7. Google Cloud & Vertex AI (Optional)

- If `VERTEX_ENDPOINT_RESOURCE_NAME` and `VERTEX_DEPLOYED_INDEX_ID` are set, the system can fetch relevant text chunks from a Matching Engine index.  
- `embedding_preprocessor.py` or `matching_engine_setup.py` let you build an index and upsert embeddings.

---

## 8. Troubleshooting

1. **`requests is not defined`**:
   - Make sure `import requests` is in `router.py` if you’re using HTTP GET for pitch deck URLs.

2. **Tesseract Not Found**:
   - Install Tesseract at the OS level. Check `pytesseract.pytesseract.tesseract_cmd` if on a custom path.

3. **`OpenAI API key not set`**:
   - You must export `OPENAI_API_KEY`. e.g. `export OPENAI_API_KEY=sk-...`.

4. **Database**:
   - If `DATABASE_URL` is empty or invalid, the server can’t store or retrieve any `reports`.

5. **Supabase**:
   - If you see `FileNotFoundError` from `supabase.storage.from_(...).download(...)`, confirm the bucket name and file path. Also ensure `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.

6. **Excessive Token Usage**:
   - If your pitch deck is very large, ephemeral usage may exceed GPT context windows. You can chunk or summarize it before injection.

---

## 9. Example Docker Deployment

```dockerfile
FROM python:3.9-slim

# 1) System-level dependencies for Tesseract & PyMuPDF
RUN apt-get update && apt-get install -y tesseract-ocr libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# 2) Copy code
WORKDIR /app
COPY . /app

# 3) Python deps
RUN pip install --no-cache-dir -r requirements.txt

# 4) Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 10. Final Notes

- This code base uses ephemeral usage to incorporate pitch decks dynamically.  
- For more advanced scenarios (like fine-tuning or indexing multiple pitch decks), check the scripts in `app/matching_engine`.  
- Logging is set to `INFO`. Adjust as needed.  
- A real production environment might integrate robust error handling, chunking, and an OAuth-based token check in `verify_token`.
