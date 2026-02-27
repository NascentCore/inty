#!/usr/bin/env bash
# One-shot deploy: build image, create Cloud Run Job, create Cloud Scheduler trigger.
# Usage: PROJECT_ID=my-project REGION=us-central1 ./deploy.sh
# Optional: JOB_NAME=my-job SCHEDULE="0 * * * *"
# See README.md for full documentation.

set -e

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
JOB_NAME="${JOB_NAME:-gcp-scheduled-job-demo}"
SCHEDULE="${SCHEDULE:-0 * * * *}"
IMAGE="gcr.io/${PROJECT_ID}/${JOB_NAME}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DOCKERFILE_DIR="${REPO_ROOT}/experimental/gcp_scheduled_job"

echo "Building image ${IMAGE}..."
gcloud builds submit --tag "${IMAGE}" --file "${DOCKERFILE_DIR}/Dockerfile" "${DOCKERFILE_DIR}"

echo "Creating Cloud Run Job ${JOB_NAME}..."
gcloud run jobs create "${JOB_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  2>/dev/null || gcloud run jobs update "${JOB_NAME}" --image "${IMAGE}" --region "${REGION}"

PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting Cloud Run Invoker to ${SA_EMAIL}..."
gcloud run jobs add-iam-policy-binding "${JOB_NAME}" \
  --region "${REGION}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker" \
  --quiet

TRIGGER_NAME="${JOB_NAME}-trigger"
echo "Creating Cloud Scheduler job ${TRIGGER_NAME}..."
gcloud scheduler jobs create http "${TRIGGER_NAME}" \
  --location "${REGION}" \
  --schedule="${SCHEDULE}" \
  --uri="https://run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/${JOB_NAME}:run" \
  --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}" \
  2>/dev/null || echo "Scheduler job may already exist; update manually if needed."

echo "Done. Run once: gcloud run jobs execute ${JOB_NAME} --region ${REGION}"
