Below is a **final guide** on securely managing your sensitive credentials (e.g., **OPENAI_API_KEY**, **DATABASE_URL**, **SUPABASE_URL**, **SUPABASE_SERVICE_KEY**, and **REPORTS_BUCKET_NAME**) for your FastAPI project running on Cloud Run. This guide emphasizes best practices, including storing credentials in a **.env** file only for local development, and using **Google Secret Manager** or deployment-time environment variable injection for production.

---

## 1. Use `.env` for Local Development Only

When developing or testing locally, you can store your secrets in a **.env** file to simplify the workflow. **Ensure** you add `.env` to your `.gitignore` so it does not get committed to version control.

### Sample `.env` File

```bash
# ------------------------------------------------------------------------------
# SAMPLE ENV FILE (LOCAL DEVELOPMENT ONLY)
# ------------------------------------------------------------------------------
# Copy this file to .env, and fill in actual values for local testing.
# Do NOT commit .env to version control in production.

# OpenAI API Key
OPENAI_API_KEY="sk-1234youropenaiapikey"

# Database URL for local dev/testing
DATABASE_URL="postgresql+psycopg2://db_user:db_pass@localhost:5432/mydatabase"

# Supabase Project URL
SUPABASE_URL="https://abcdefghi.supabase.co"

# Supabase Service Key (for write-level operations)
SUPABASE_SERVICE_KEY="supabase-service-key-here"

# Google Cloud Storage bucket name for storing PDF reports
REPORTS_BUCKET_NAME="dev-reports-bucket"
```

**Key Points**  
1. **.env** is only for local development convenience; never check it into source control.  
2. Use a **safe** location on your local machine or use a vault for real secrets, even in development, if possible.

---

## 2. Production Secrets with Google Secret Manager

For **production** deployments on GCP (Cloud Run, GKE, or other platforms), you should rely on **Google Secret Manager** to store and retrieve credentials. This approach is much more secure and easier to audit. Below is a high-level workflow:

1. **Create a Secret** in Google Secret Manager (e.g., `OPENAI_API_KEY`).  
2. **Add a Secret Version** containing the actual key.  
3. **Grant your Cloud Run service account** (or a dedicated service account) the **`roles/secretmanager.secretAccessor`** role to read the secret.  
4. **Inject the secret** as an environment variable during deployment or by using references to Secret Manager. For instance, using **`gcloud run deploy`** with `--update-secrets`, or by having your application code retrieve the secret at runtime.

Example (`gcloud run deploy` with secrets injection):
```bash
gcloud run deploy my-service \
  --image gcr.io/my-project/my-image:latest \
  --region us-central1 \
  --update-secrets OPENAI_API_KEY=projects/MY_PROJECT/secrets/OPENAI_API_KEY:latest \
  --platform managed
```
You can also specify other secrets, like `SUPABASE_SERVICE_KEY`, in the same command.

---

## 3. Environment Variable Injection at Deployment

If you prefer to set environment variables without using Secret Manager (or in combination with it), you can inject them at deployment time:

```bash
gcloud run deploy my-service \
  --image gcr.io/my-project/my-image:latest \
  --region us-central1 \
  --set-env-vars "OPENAI_API_KEY=your_openai_api_key_here" \
  --set-env-vars "DATABASE_URL=postgresql+psycopg2://db_user:db_pass@/db_name?host=/cloudsql/project-id:region:instance" \
  ...
```

**Note**: This approach is simpler, but it places secrets directly into Cloud Run configuration, which is still relatively secure if you limit who can edit/view the Cloud Run service in your IAM settings. The logs and revision history in Cloud Run could expose secrets if you are not careful. Secret Manager is the more robust and auditable approach.

---

## 4. Additional Best Practices

1. **Avoid Hard-Coding**  
   - Never store secrets directly in code or in Dockerfiles. Instead, rely on environment variables or in-memory retrieval from a secure vault system (Secret Manager).

2. **Least Privilege IAM**  
   - Give your Cloud Run or application service account only the necessary roles, e.g., `roles/secretmanager.secretAccessor`, `roles/cloudsql.client`, `roles/storage.objectAdmin`, etc. Refrain from broad roles like `Owner` or `Editor`.

3. **Automated CI/CD**  
   - In a CI/CD pipeline, retrieve secrets from a vault/Secret Manager and inject them as environment variables (for example, using GitHub Actions or Cloud Build steps).

4. **Audit and Rotation**  
   - Periodically rotate credentials (e.g., database passwords, API keys).  
   - Enable logs in Google Secret Manager to audit secret access.  
   - Use alerts in Google Cloud Monitoring to watch for unusual activity or access patterns.

5. **Local vs. Production**  
   - Maintain separate configuration for local development and production.  
   - For example, your local `.env` might point to a test database, while your production environment variables reference the actual production database.

---

## Conclusion

By storing credentials in **Secret Manager** or injecting them at deployment time, you ensure that your application has access to necessary secrets while maintaining a **high level of security**. The sample `.env` file provided here is for local development only and must be **excluded** from production deployments and **version control**.