Below is a **comprehensive guide** for deploying the GFV Investment Readiness Report System to **Google Cloud Platform (GCP)**, focusing on Cloud Run, Cloud Storage, Vertex AI Matching Engine, and (optionally) Cloud SQL or other resources needed.

---

# **Comprehensive GCP Deployment Instructions**

## 1. Prerequisites

1. **GCP Project**: You have a Google Cloud project with **Owner** or **Editor** privileges.  
2. **Billing Enabled**: Ensure your project has billing configured.  
3. **Cloud SDK / gcloud**: Install and authenticate the gcloud CLI locally.  
4. **Docker**: For building images locally if you don’t use Cloud Build.  
5. **SQL Database**: You can run PostgreSQL locally, in GCP’s Cloud SQL, or use another managed DB. We’ll outline Cloud SQL below.  
6. **OpenAI Key**: For GPT-4 usage (`OPENAI_API_KEY`).  
7. **Supabase** (Optional): If you plan to store pitch decks or final statuses in Supabase.  
8. **Code & Dependencies**: The final code for your GFV system, with the Dockerfile in the repository’s root.

---

## 2. Enable Required Services

1. **Cloud Run**  
   ```bash
   gcloud services enable run.googleapis.com
   ```
2. **Cloud Build** (for building Docker images automatically if desired)  
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   ```
3. **Artifact Registry** (optional alternative to Container Registry)  
   ```bash
   gcloud services enable artifactregistry.googleapis.com
   ```
   or if you use the older Container Registry, ensure `containerregistry.googleapis.com` is enabled.
4. **Vertex AI** (for the Matching Engine)  
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```
5. **Cloud Logging** is typically enabled by default. If not:  
   ```bash
   gcloud services enable logging.googleapis.com
   ```

---

## 3. Create or Configure GCS Bucket

If you plan to store final PDFs or large artifacts in Google Cloud Storage:

1. **Create** a bucket (e.g., `my-reports-bucket`):
   ```bash
   gsutil mb -p YOUR_PROJECT_ID -c standard -l us-central1 gs://my-reports-bucket/
   ```
2. Ensure your Cloud Run service account (or relevant service accounts) have appropriate roles, e.g. `storage.objectAdmin` on that bucket, if you plan to write.

---

## 4. (Optional) Configure Cloud SQL for PostgreSQL

If you plan to host your DB in GCP:

1. **Enable** the Cloud SQL Admin API:
   ```bash
   gcloud services enable sqladmin.googleapis.com
   ```
2. **Create** a PostgreSQL instance:
   ```bash
   gcloud sql instances create my-postgres-instance \
       --database-version=POSTGRES_13 \
       --tier=db-f1-micro \
       --region=us-central1
   ```
3. **Set** a root password:
   ```bash
   gcloud sql users set-password postgres --instance my-postgres-instance --password YOUR_DB_PASSWORD
   ```
4. Create a database within that instance:
   ```bash
   gcloud sql databases create gfv_db --instance=my-postgres-instance
   ```
5. **Construct** your `DATABASE_URL`:
   - Something like: `postgresql://postgres:YOUR_DB_PASSWORD@/gfv_db?host=/cloudsql/YOUR_PROJECT_ID:us-central1:my-postgres-instance`
   - If you connect from Cloud Run, you’ll also need `--add-cloudsql-instances` in your Cloud Run deploy command.  

**Alternatively**, if you want to run PostgreSQL on a VM or use a separate host, just make sure your `DATABASE_URL` is set accordingly in environment variables.

---

## 5. Configure Vertex AI Matching Engine

**If** you plan to do retrieval-augmented generation with pitch decks or maturity models:

1. **Create** your index using `matching_engine_setup.py` or the console:
   - A typical command in code:
     ```bash
     cd app/matching_engine
     python matching_engine_setup.py
     ```
   - This will create a tree-AH index with streaming updates, then deploy it to an index endpoint.
2. Note the **Index Resource Name** and the **Index Endpoint Resource Name** (something like `projects/PROJECT_ID/locations/us-central1/indexEndpoints/1234567890`).
3. Set them as environment variables:  
   ```bash
   export VERTEX_ENDPOINT_RESOURCE_NAME="projects/PROJECT_ID/locations/us-central1/indexEndpoints/INDEXENDPOINT_ID"
   export VERTEX_DEPLOYED_INDEX_ID="my_vector_index_deployed"
   ```
4. Adjust code references (`retrieval_utils.py`, `orchestrator.py`) accordingly.

---

## 6. Build & Push Docker Image

Inside your project directory with the **Dockerfile**:

```bash
# If using Artifact Registry:
gcloud auth configure-docker us-central1-docker.pkg.dev

# or if using Container Registry:
gcloud auth configure-docker

# Build:
docker build -t gcr.io/YOUR_PROJECT_ID/gfv-report-app:v1 .

# Push:
docker push gcr.io/YOUR_PROJECT_ID/gfv-report-app:v1
```

Alternatively, you can use **Cloud Build**:

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/gfv-report-app:v1 .
```

---

## 7. Deploy to Cloud Run

**Single command** if you have your container image ready:

```bash
gcloud run deploy gfv-report-service \
  --image gcr.io/YOUR_PROJECT_ID/gfv-report-app:v1 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**If** you need to connect to Cloud SQL, add:
```bash
--add-cloudsql-instances=YOUR_PROJECT_ID:us-central1:my-postgres-instance
```
and ensure your `DATABASE_URL` is formatted for the Cloud SQL socket.

---

## 8. Set Environment Variables on Cloud Run

Use the GCP Console or CLI to set environment variables like `DATABASE_URL`, `OPENAI_API_KEY`, `REPORTS_BUCKET_NAME`, etc.:

```bash
gcloud run services update gfv-report-service \
  --update-env-vars DATABASE_URL="postgresql://..." \
  --update-env-vars OPENAI_API_KEY="sk-..." \
  --update-env-vars REPORTS_BUCKET_NAME="my-reports-bucket" \
  --update-env-vars VERTEX_ENDPOINT_RESOURCE_NAME="projects/PROJECT_ID/locations/us-central1/indexEndpoints/ENDPOINT_ID" \
  --update-env-vars VERTEX_DEPLOYED_INDEX_ID="my_vector_index_deployed"
```

If you integrate with **Supabase**, also set:
```bash
--update-env-vars SUPABASE_URL="https://YOURPROJECT.supabase.co" \
--update-env-vars SUPABASE_SERVICE_KEY="your-supabase-service-key"
```

---

## 9. Post-Deployment Checks

1. **Logs**: In GCP Console → Cloud Run → your service → “Logs,” ensure the container started successfully.  
2. **Health Check**: Hit `[CLOUDRUN_URL]/health`. You should get `{"status":"ok"}`.  
3. **Database**: Confirm your system can connect to the DB. If using Cloud SQL, ensure you have the correct socket or external IP.  
4. **Endpoints**: Try `POST /api/reports` or `POST /api/reports/{id}/generate` to confirm end-to-end.

---

## 10. Optional Steps

### Pitch Deck Embedding

If you want to embed **pitch decks** from Supabase into Vertex AI:

1. Set your supabase environment variables:
   ```bash
   export SUPABASE_URL="https://YOURPROJECT.supabase.co"
   export SUPABASE_SERVICE_KEY="service-role-key..."
   ```
2. Use `supabase_pitchdeck_downloader.py`:
   ```bash
   cd app/matching_engine
   python supabase_pitchdeck_downloader.py \
       --file_name "acme_pitchdeck.pdf" \
       --index "projects/PROJECT_ID/locations/us-central1/indexes/INDEX_ID"
   ```
3. Your pitch deck pages are now in Vertex AI for retrieval.

### Maturity Model / Market Data

Similarly, run `embedding_preprocessor.py` to embed your static reference docs:

```bash
python embedding_preprocessor.py --pdf path/to/mymaturitymodel.pdf \
    --index "projects/PROJECT_ID/locations/us-central1/indexes/INDEX_ID"
```

---

## 11. Workflow Summary

1. **Create** a new report: `POST /api/reports`.  
2. **(Optional)** Upload pitch decks to Supabase or embed new docs in Vertex AI.  
3. **Generate** final Tier‑2 sections: `POST /api/reports/{report_id}/generate`.  
4. The orchestrator calls GPT-4 and references Vertex AI retrieval if configured.  
5. The system may store final text in DB, mark the report “completed,” or upload a PDF to GCS.  
6. **Retrieve** final data: `GET /api/reports/{report_id}`, or `GET /api/reports/{report_id}/content`.

---

## 12. Troubleshooting & Logs

- **Cloud Run Logs**:  
  - GCP Console → Cloud Run → your service → “Logs.”  
- **Supabase**:  
  - Check your “reports” table if you’re calling `notify_supabase_final_report(...)`.
- **Vertex AI**:  
  - Confirm your index & endpoint are set with streaming updates for real-time upserts.  
- **OpenAI**:  
  - Verify your `OPENAI_API_KEY` is set.  
- **Database**:  
  - If `DATABASE_URL` is invalid, or if Cloud SQL connectivity isn’t correct, you’ll see DB errors on container startup or in logs.

---

## 13. License

*(Include or remove license text as appropriate, e.g., MIT, Apache, or proprietary.)*

---

**With these steps**, you have a **complete** GCP deployment approach:

1. **Enable** GCP services.  
2. **Build & push** Docker.  
3. **Deploy** to Cloud Run, setting your env vars.  
4. **Test** end-to-end with `POST /api/reports` → `POST /api/reports/{report_id}/generate`.  

You can now seamlessly generate **GFV Investment Readiness Reports** with GPT‑4 in a fully managed GCP environment.