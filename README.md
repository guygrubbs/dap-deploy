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

### 4.1 OpenAI-Powered Report Generation

The backend uses **OpenAI's ChatCompletion API** for two main purposes:

#### 1. Initial Report Content Generation
- **Model**: Configurable via `OPENAI_MODEL` environment variable (defaults to "o1")
- **Orchestrator**: `app/api/ai/orchestrator.py` coordinates multiple AI agents
- **Specialized Agents**: Each handles a specific report section:
  - `ResearcherAgent` - Gathers external context and market data
  - `ExecutiveSummaryAgent` - Creates executive summary and investment rationale
  - `MarketAnalysisAgent` - Analyzes market opportunity and competitive landscape
  - `FinancialPerformanceAgent` - Evaluates financial performance and investment readiness
  - `GoToMarketAgent` - Assesses go-to-market strategy and customer traction
  - `LeadershipTeamAgent` - Reviews leadership and team composition
  - `InvestorFitAgent` - Determines investor fit and exit strategy
  - `RecommendationsAgent` - Provides final recommendations and next steps

#### 2. Summary Generation for Frontend
- **JSON Structure Processing**: OpenAI API processes report contents to create structured summaries
- **Frontend-Optimized Output**: Generates JSON data specifically formatted for React components
- **Database Storage**: Structured summaries stored in `deal_report_summaries` table as JSON strings

#### Report Generation Process
1. **Database Monitoring**: Backend monitors `analysis_requests` table for pending entries
2. **Context Gathering**: Combines pitch deck text, retrieved context, and company information
3. **Multi-Agent Processing**: Each agent generates its specialized section using OpenAI API
4. **Summary Generation**: OpenAI processes report contents to create structured JSON summaries
5. **Database Updates**: Updates Supabase tables with generated content and summaries
6. **Error Handling**: Retry logic with exponential backoff for API failures

### 4.2 Ephemeral PDF Usage

When generating a report, you can:
1. Provide a `pitch_deck_url` in your analysis request
2. The system downloads the PDF, extracts text with OCR fallback
3. That text is included in the AI prompt context ephemeral (not stored permanently)
4. OpenAI processes the pitch deck content along with other context
5. The pitch deck data is only used for that single request - no permanent training

**Privacy**: Pitch deck data is processed ephemeral and not stored in OpenAI's training data.

### 4.3 Structured Data Storage

Generated reports are stored in structured JSON format in the `deal_report_summaries` table:
- Each report section is stored as serialized JSON
- Frontend components parse JSON to render interactive report views
- Data structure matches exactly what React components expect
- Supports rich formatting, tables, charts, and interactive elements

### 4.4 External API Integration

The system integrates with an external report generation service:
- **Outbound**: Sends analysis requests to external API for additional processing
- **Webhook**: Receives completion notifications with structured report data
- **Dual Processing**: Combines OpenAI-generated content with external API results
- **Fallback**: Can operate independently if external service is unavailable

---

## 5. API Endpoints & Frontend Integration

### 5.1 Frontend Database Integration
**Frontend creates analysis requests directly in Supabase** - No direct API endpoint needed.

The frontend inserts records into the `analysis_requests` table:
```sql
INSERT INTO analysis_requests (
  user_id, founder_name, company_name, email, status, 
  industry, funding_stage, company_type, additional_info, pitch_deck_url
) VALUES (
  'uuid-string', 'John Doe', 'Example Startup Inc', 'jane@example.com', 'pending',
  'Technology', 'Seed', 'SaaS', 'Additional context...', 'https://supabase-url/pitch-deck.pdf'
);
```

### 5.2 Report Generation: `POST /api/reports/{report_id}/generate`
Triggers the complete report generation workflow:

1. **Updates Status**: Changes analysis request status from "pending" to "processing"
2. **External API Call**: Sends request to external report generation service
3. **Database Updates**: Creates placeholder records in `deal_reports` and `deal_report_summaries` tables
4. **OpenAI Integration**: Uses multiple AI agents to generate report sections
5. **Structured Data**: Inserts JSON-formatted report data for frontend consumption

#### Response
```json
{
  "message": "Report generation initiated",
  "external_request_id": "ext-report-123",
  "deal_id": "deal_1234567890_abc123"
}
```

### 5.3 Report Completion Webhook: `POST /webhook/report-completion`
Handles callbacks from the external API when report generation is complete.

#### Expected Webhook Payload
```json
{
  "reportId": "deal_1234567890_abc123",
  "pdfUrl": "https://storage.googleapis.com/reports/final-report.pdf",
  "summaryData": {
    "executive_summary": {
      "context_purpose": "Executive summary content...",
      "investment_attractiveness": {
        "level": "high",
        "description": "Strong investment potential"
      },
      "key_metrics": ["Revenue: $1M", "Growth: 50%"],
      "strengths": ["Strong team", "Market opportunity"],
      "challenges": ["Competition", "Scaling"]
    },
    "strategic_recommendations": {
      "recommendations": [
        {
          "priority": "high",
          "timeframe": "0-3 Months",
          "items": ["Action item 1", "Action item 2"]
        }
      ]
    },
    "market_analysis": { /* structured market data */ },
    "financial_overview": { /* structured financial data */ },
    "competitive_landscape": { /* structured competitive data */ },
    "action_plan": { /* structured action plan data */ },
    "investment_readiness": { /* structured readiness assessment */ }
  }
}
```

### 5.4 Report Status Monitoring: `GET /api/reports/{report_id}/status`
Check the current status and progress of report generation.

#### Response
```json
{
  "report_id": "uuid-string",
  "status": "processing|completed|failed",
  "progress": 75
}
```

### 5.5 Report Content Retrieval: `GET /api/reports/{report_id}/content`
Retrieve the generated report sections for frontend display.

#### Response (`ReportContentResponse`)
```json
{
  "report_id": "uuid-string",
  "sections": [
    {
      "section_name": "executive_summary",
      "content": "Generated executive summary content..."
    },
    {
      "section_name": "market_analysis",
      "content": "Generated market analysis content..."
    }
  ]
}
```

### 5.6 Report Metadata: `GET /api/reports/{report_id}`
Retrieve basic report information and metadata.

## 6. Frontend-Backend Integration Workflow

### Actual Report Generation Sequence

1. **Frontend Database Entry Creation**
   ```javascript
   // Frontend creates analysis request directly in Supabase
   const { data: newRequest, error } = await supabase
     .from('analysis_requests')
     .insert({
       user_id: userId,
       founder_name: founderName,
       company_name: companyName,
       email: email,
       status: 'pending',
       // ... other fields
     })
     .select()
     .single();
   
   // Trigger backend processing via edge function
   const { data, error } = await supabase.functions.invoke('generate-analysis-report', {
     body: { analysisRequestId: newRequest.id }
   });
   ```

2. **Backend Monitoring and Processing**
   ```javascript
   // Backend monitors analysis_requests table and processes pending requests
   // GET /api/reports/{report_id}/generate endpoint:
   // 1. Retrieves analysis request from Supabase
   // 2. Updates status to 'processing'
   // 3. Calls external API for additional processing
   // 4. Uses OpenAI agents to generate report sections
   // 5. Updates Supabase with generated content
   ```

3. **OpenAI Summary Generation**
   ```javascript
   // Backend uses OpenAI API to generate structured summaries
   // 1. Feeds report contents to OpenAI ChatCompletion API
   // 2. Uses specialized prompts to create JSON-structured summaries
   // 3. Stores results in deal_report_summaries table as JSON strings
   // 4. Updates analysis_requests status to 'completed'
   ```

4. **Frontend Data Consumption**
   ```javascript
   // Frontend loads completed report data from Supabase
   const { data: summary } = await supabase
     .from('deal_report_summaries')
     .select('*')
     .eq('deal_id', dealId)
     .maybeSingle();
   
   // Parse JSON sections for React components
   const reportData = {
     executiveSummary: JSON.parse(summary.executive_summary),
     strategicRecommendations: JSON.parse(summary.strategic_recommendations),
     marketAnalysis: JSON.parse(summary.market_analysis),
     financialOverview: JSON.parse(summary.financial_overview),
     competitiveLandscape: JSON.parse(summary.competitive_landscape),
     actionPlan: JSON.parse(summary.action_plan),
     investmentReadiness: JSON.parse(summary.investment_readiness)
   };
   ```

### 5.7 Legacy Endpoints (Still Available)

- **Fine-tuning**: `POST /pitchdecks/{deck_file}/upload_to_openai` - For offline fine-tuning approach
- **Direct Report Creation**: Legacy report creation (if needed for backward compatibility)

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
