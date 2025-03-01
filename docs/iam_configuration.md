# IAM Configuration for Cloud Run

This document provides guidelines for granting the necessary permissions to the Cloud Run service account that runs your FastAPI application. Assigning the correct roles ensures smooth operation when integrating with Cloud SQL, Cloud Storage, and Google Cloud’s logging and monitoring services.

## 1. Identify or Create a Service Account

1. **User-Managed Service Account**  
   - For better security and auditability, create a dedicated service account (e.g., `my-cloud-run-sa@my-project.iam.gserviceaccount.com`).
   - When deploying your service, specify `--service-account` to use this custom service account instead of the default Cloud Run-managed service agent.

2. **Default Cloud Run Service Agent**  
   - If you do not specify a custom service account, Cloud Run automatically uses the default service agent named `service-PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com`.  
   - In this case, you must grant roles to the **serverless-robot-prod** service agent rather than a user-managed service account.

## 2. Required IAM Roles

Below is a minimal set of IAM roles you will typically need:

1. **Cloud SQL Access**  
   - **Role**: `roles/cloudsql.client`  
   - **Purpose**: Required to connect to Cloud SQL from Cloud Run, especially if using Unix domain sockets for secure connections (`--add-cloudsql-instances`).

2. **Cloud Storage Access**  
   - **Role**: `roles/storage.objectAdmin`  
   - **Purpose**: Allows creating, reading, and modifying objects in a Google Cloud Storage bucket (e.g., uploading PDF reports, generating signed URLs).  
   - **Alternative**: Instead of `objectAdmin`, you can combine `roles/storage.objectCreator` + `roles/storage.objectViewer` if you want finer-grained privileges (depending on your usage patterns).

3. **Logging Access**  
   - **Role**: `roles/logging.logWriter`  
   - **Purpose**: Allows the service to write logs to Cloud Logging.

4. **Monitoring Access**  
   - **Role**: `roles/monitoring.metricWriter`  
   - **Purpose**: Lets the service push custom metrics to Cloud Monitoring (if you use custom metrics), and ensures Cloud Monitoring can gather standard service metrics as well.

### Example gcloud Commands

Below is an example of how to assign these roles using the `gcloud` CLI. Update `PROJECT_ID` and `SERVICE_ACCOUNT_EMAIL` accordingly:

```bash
# Cloud SQL Client
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client"

# Cloud Storage Object Admin (or alternate combinations)
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin"

# Logging Log Writer
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/logging.logWriter"

# Monitoring Metric Writer
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/monitoring.metricWriter"
```

> **Note**: If you are using the default Cloud Run service agent, replace `SERVICE_ACCOUNT_EMAIL` with the format:  
> `service-PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com`.

## 3. Monitoring and Alerting

1. **Basic Cloud Monitoring Metrics**  
   - By default, Cloud Run provides metrics such as request count, request latency, and error rate in Cloud Monitoring.
   - You can view these metrics in the **Google Cloud Console** under **Monitoring > Metrics Explorer**.

2. **Setting Up Alerts**  
   - You can configure alerts on error rates or latency thresholds using **Alerting** in Cloud Monitoring.  
   - For example, you can create an alert policy that triggers if the **5xx error rate** exceeds 1% or if **p95 latency** goes above a certain threshold for 5 minutes.
   - Alerts can be routed to email, Slack, PagerDuty, etc. via **Notification Channels** in Cloud Monitoring.

3. **SLO / SLA Monitoring**  
   - Consider creating a Service Level Objective (SLO) for your service (e.g., 99.9% availability or a certain threshold of latency).  
   - This helps track reliability over time and can integrate with incident management workflows.

### Example Alert Policy

In the Cloud Console (Monitoring > Alerting > Create Policy):
1. **Select a metric**: For example, `Cloud Run Revision > Request Latency (95th percentile)`.
2. **Set a condition**: `p95 latency > 2 seconds for 5 minutes`.
3. **Add notification channels**: Email, SMS, Slack, etc.
4. **Name and save** the policy.

With these steps in place, your Cloud Run service will have the necessary IAM permissions to interact with Cloud SQL, Cloud Storage, logging, and monitoring, while also providing alerts to help you proactively manage application health.