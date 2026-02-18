# GCP Scheduled Job — Minimal Demo

Minimal demo of a **cron-style job** on Google Cloud: **Docker image → Cloud Run Job → Cloud Scheduler**. No Cloud SQL or Vertex AI in this demo. See [GEMINI_REPORT.md](GEMINI_REPORT.md) for the full architecture including Cloud SQL and Gemini.

## Prerequisites

- `gcloud` CLI installed and authenticated (`gcloud auth login`, `gcloud config set project PROJECT_ID`)
- A GCP project with billing enabled
- APIs enabled: Cloud Build, Cloud Run, Cloud Scheduler

```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com cloudscheduler.googleapis.com
```

## Secrets (no Secret Manager)

Secrets are **not** read from GCP Secret Manager. Use **GitHub Secrets** (or env vars in CI) and pass them at **build time** as Docker build args so they are baked into the image.

- In GitHub Actions: `docker build --build-arg DB_PASSWORD=${{ secrets.DB_PASSWORD }} ...`
- Locally: `docker build --build-arg DB_PASSWORD="$DB_PASSWORD" ...`

In the Dockerfile, declare `ARG FOO` and set `ENV FOO=$FOO` (or write to a file the app reads). **Note:** Anyone with image pull access can inspect image layers; acceptable for this demo or controlled registries.

## Step-by-step deployment

Use the same `PROJECT_ID` and `REGION` (e.g. `us-central1`) for all steps.

### 1. Set variables

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
export JOB_NAME=gcp-scheduled-job-demo
export IMAGE=gcr.io/${PROJECT_ID}/${JOB_NAME}
```

### 2. Build the image

From the **project repo root** (so the Dockerfile build context can see this directory):

```bash
gcloud builds submit --tag "${IMAGE}" --file experimental/gcp_scheduled_job/Dockerfile experimental/gcp_scheduled_job
```

Or from **this directory**:

```bash
cd experimental/gcp_scheduled_job
gcloud builds submit --tag "${IMAGE}" .
```

### 3. Create the Cloud Run Job

No `--set-cloudsql-instances` or custom service account for the minimal demo. Default Compute Engine service account is acceptable.

```bash
gcloud run jobs create "${JOB_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}"
```

### 4. Create the Cloud Scheduler trigger

Cloud Scheduler will POST to the Job’s **v2** `:run` endpoint. Use a service account that has **Cloud Run Invoker** (`roles/run.invoker`) on this job (e.g. the same project’s Compute Engine default SA, or a dedicated SA).

Get your project number (for the default SA email):

```bash
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
```

Grant the invoker role to that SA on the job (if not already):

```bash
gcloud run jobs add-iam-policy-binding "${JOB_NAME}" \
  --region "${REGION}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker"
```

Create the scheduler job (e.g. hourly at minute 0):

```bash
gcloud scheduler jobs create http "${JOB_NAME}-trigger" \
  --location "${REGION}" \
  --schedule="0 * * * *" \
  --uri="https://run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/${JOB_NAME}:run" \
  --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}"
```

**URI note:** Official docs use the **v2** Run API. [GEMINI_REPORT.md](GEMINI_REPORT.md) shows a v1-style URL; the v2 format above is correct.

### 5. Run the job once (optional)

To test without waiting for the schedule:

```bash
gcloud run jobs execute "${JOB_NAME}" --region "${REGION}"
```

View executions and logs in the Cloud Console: **Cloud Run → Jobs →** select the job **→ Executions** and **Logs**.

## IAM summary

| Who / What              | Role / need |
|-------------------------|------------|
| Scheduler → Job         | Service account in `--oauth-service-account-email` must have **Cloud Run Invoker** on the job |
| Creating the Job        | Cloud Run Admin/Developer; Cloud Build and push to GCR for image build |
| Job runtime (minimal)   | Default Compute SA is fine; for production or Cloud SQL, use a dedicated SA with least privilege |

## Optional: deploy script

See [deploy.sh](deploy.sh) for a one-shot script that runs build, create job, and create scheduler. README remains the source of truth.

## References

- [Execute jobs on a schedule](https://cloud.google.com/run/docs/execute/jobs-on-schedule) — v2 URI and OAuth
- [Connect to Cloud SQL from Cloud Run](https://docs.cloud.google.com/sql/docs/mysql/connect-instance-cloud-run) — if you add Cloud SQL later, use public IP + Unix socket (no VPC connector)
