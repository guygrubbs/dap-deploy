# Complete Supabase SQL Schema for Investment Readiness Report System

## Overview
This document provides the complete SQL table structure required for the Investment Readiness Report system to work correctly in Supabase. The schema includes three main tables that handle the complete workflow from request submission to report generation and display.

## Table 1: analysis_requests

**Purpose**: Tracks user submissions and processing status for investment readiness report requests.

```sql
CREATE TABLE analysis_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    company_name TEXT NOT NULL DEFAULT 'Right Hand Operation',
    requestor_name TEXT NOT NULL,
    email TEXT NOT NULL,
    founder_name TEXT,
    industry TEXT,
    funding_stage TEXT,
    company_type TEXT,
    additional_info TEXT,
    pitch_deck_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    external_request_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    parameters JSONB
);

-- Indexes for performance
CREATE INDEX idx_analysis_requests_user_id ON analysis_requests(user_id);
CREATE INDEX idx_analysis_requests_status ON analysis_requests(status);
CREATE INDEX idx_analysis_requests_created_at ON analysis_requests(created_at);
```

### Column Details:
| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key, auto-generated |
| user_id | UUID | NO | - | Supabase auth user ID who submitted request |
| company_name | TEXT | NO | 'Right Hand Operation' | Company name (always "Right Hand Operation") |
| requestor_name | TEXT | NO | - | Name of person requesting the report |
| email | TEXT | NO | - | Email address for notifications |
| founder_name | TEXT | YES | NULL | Name of the founder being analyzed |
| industry | TEXT | YES | NULL | Industry/sector of the company |
| funding_stage | TEXT | YES | NULL | Current funding stage (Seed, Series A, etc.) |
| company_type | TEXT | YES | NULL | Type of company (B2B, B2C, SaaS, etc.) |
| additional_info | TEXT | YES | NULL | Additional context, stored as "Founder Company: [name]\n[extra info]" |
| pitch_deck_url | TEXT | YES | NULL | URL to pitch deck PDF |
| status | TEXT | NO | 'pending' | Processing status: 'pending', 'processing', 'completed', 'failed' |
| external_request_id | TEXT | YES | NULL | External API tracking ID |
| created_at | TIMESTAMPTZ | NO | NOW() | Record creation timestamp |
| updated_at | TIMESTAMPTZ | NO | NOW() | Last update timestamp |
| parameters | JSONB | YES | NULL | Additional data including generated_sections and pdf_url |

## Table 2: deal_reports

**Purpose**: Stores PDF report metadata and download links for completed reports.

```sql
CREATE TABLE deal_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    pdf_url TEXT,
    pdf_file_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_deal_reports_deal_id ON deal_reports(deal_id);
CREATE INDEX idx_deal_reports_company_name ON deal_reports(company_name);
CREATE INDEX idx_deal_reports_created_at ON deal_reports(created_at);
```

### Column Details:
| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key, auto-generated |
| deal_id | TEXT | NO | - | Unique deal identifier (format: "deal_{timestamp}_{uuid}") |
| company_name | TEXT | NO | - | Company name from the analysis request |
| pdf_url | TEXT | YES | NULL | Public URL to download the generated PDF report |
| pdf_file_path | TEXT | YES | NULL | Storage path for the PDF file |
| created_at | TIMESTAMPTZ | NO | NOW() | Record creation timestamp |
| updated_at | TIMESTAMPTZ | NO | NOW() | Last update timestamp |

## Table 3: deal_report_summaries

**Purpose**: Stores structured JSON content for each report section, optimized for frontend display.

```sql
CREATE TABLE deal_report_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    executive_summary TEXT,
    strategic_recommendations TEXT,
    market_analysis TEXT,
    financial_overview TEXT,
    competitive_landscape TEXT,
    action_plan TEXT,
    investment_readiness TEXT,
    key_metrics JSONB,
    financial_projections JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_deal_report_summaries_deal_id ON deal_report_summaries(deal_id);
CREATE INDEX idx_deal_report_summaries_company_name ON deal_report_summaries(company_name);
CREATE INDEX idx_deal_report_summaries_created_at ON deal_report_summaries(created_at);
```

### Column Details:
| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| id | UUID | NO | gen_random_uuid() | Primary key, auto-generated |
| deal_id | TEXT | NO | - | Links to deal_reports table via deal_id |
| company_name | TEXT | NO | - | Company name for display purposes |
| executive_summary | TEXT | YES | NULL | JSON string containing executive summary data |
| strategic_recommendations | TEXT | YES | NULL | JSON string containing strategic recommendations |
| market_analysis | TEXT | YES | NULL | JSON string containing market analysis data |
| financial_overview | TEXT | YES | NULL | JSON string containing financial overview |
| competitive_landscape | TEXT | YES | NULL | JSON string containing competitive analysis |
| action_plan | TEXT | YES | NULL | JSON string containing action plan data |
| investment_readiness | TEXT | YES | NULL | JSON string containing investment readiness assessment |
| key_metrics | JSONB | YES | NULL | Structured metrics data including external_report_id |
| financial_projections | JSONB | YES | NULL | Financial projection data and status |
| created_at | TIMESTAMPTZ | NO | NOW() | Record creation timestamp |
| updated_at | TIMESTAMPTZ | NO | NOW() | Last update timestamp |

## Data Flow and Relationships

### 1. Request Submission Flow
```
Frontend → analysis_requests (status: 'pending')
```

### 2. Report Generation Flow
```
analysis_requests (status: 'processing') 
→ AI Processing 
→ deal_reports (PDF metadata)
→ deal_report_summaries (structured JSON content)
→ analysis_requests (status: 'completed', parameters.pdf_url updated)
```

### 3. Frontend Display Flow
```
Dashboard: deal_report_summaries (list all reports)
Report View: deal_report_summaries (specific deal_id) + deal_reports (PDF URL)
```

## JSON Data Structure Examples

### Executive Summary JSON Structure
```json
{
  "overview": "Company overview text",
  "key_strengths": ["Strength 1", "Strength 2"],
  "investment_highlights": ["Highlight 1", "Highlight 2"],
  "recommendation": "Investment recommendation"
}
```

### Key Metrics JSONB Structure
```json
{
  "external_report_id": "uuid-string",
  "api_status": "completed",
  "processing_time": "2024-01-01T12:00:00Z"
}
```

### Financial Projections JSONB Structure
```json
{
  "status": "completed",
  "external_report_id": "uuid-string",
  "revenue_growth": "25%",
  "market_size": "$1B"
}
```

## Required Supabase Configuration

### Row Level Security (RLS)
Enable RLS on all tables and create policies based on user authentication:

```sql
-- Enable RLS
ALTER TABLE analysis_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE deal_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE deal_report_summaries ENABLE ROW LEVEL SECURITY;

-- Example policy for analysis_requests (adjust based on your auth requirements)
CREATE POLICY "Users can view their own requests" ON analysis_requests
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own requests" ON analysis_requests
    FOR INSERT WITH CHECK (auth.uid() = user_id);
```

### Real-time Subscriptions
Enable real-time for status updates:

```sql
-- Enable real-time on analysis_requests for status monitoring
ALTER PUBLICATION supabase_realtime ADD TABLE analysis_requests;
```

## Migration Notes

1. **UUID Extension**: Ensure the `uuid-ossp` extension is enabled:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   ```

2. **Timestamps**: All tables use `TIMESTAMPTZ` for proper timezone handling.

3. **JSONB vs TEXT**: Report sections are stored as TEXT (JSON strings) for compatibility with the current backend implementation, while metadata uses JSONB for better querying.

4. **Indexes**: Create indexes on frequently queried columns for optimal performance.

5. **Foreign Keys**: No explicit foreign keys are defined between tables to maintain flexibility, but logical relationships exist via `deal_id`.

## Backend Integration Points

### API Endpoints That Use These Tables:
- `POST /api/reports` → Inserts into `analysis_requests`
- `POST /api/reports/{id}/generate` → Updates `analysis_requests`, inserts into `deal_reports` and `deal_report_summaries`
- `GET /api/reports/{id}/status` → Queries `analysis_requests`
- `GET /api/reports/{id}/content` → Queries `analysis_requests` for PDF URL and sections
- `POST /webhook/report-completion` → Updates `deal_reports` and `deal_report_summaries`

### Frontend Queries:
- Dashboard: `SELECT * FROM deal_report_summaries ORDER BY created_at DESC`
- Report View: `SELECT * FROM deal_report_summaries WHERE deal_id = ?`
- PDF Download: `SELECT pdf_url FROM deal_reports WHERE deal_id = ?`
- Status Monitoring: Real-time subscription to `analysis_requests` table
