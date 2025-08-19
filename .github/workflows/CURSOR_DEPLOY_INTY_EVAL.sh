#!/bin/bash -e

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $1"
}

INTY_EVAL_IMAGE_NAME="ghcr.io/nascentcore/inty-backend/inty-eval"
IMAGE_TAG=$(git rev-parse --abbrev-ref HEAD)
SERVICE_PORT_ON_HOST="8104"
REMOTE_HOST="inty"
SERVICE_PUBLIC_URL="https://new.test.inty.cc"

FULL_IMAGE_TAG="${INTY_EVAL_IMAGE_NAME}:${IMAGE_TAG}"
CONTAINER_NAME="inty-eval"

log "--- Building and Deploying Inty Evaluation ---"
log "Image: ${FULL_IMAGE_TAG}"
log "Remote Host: ${REMOTE_HOST}"
log "Service Port on Host: ${SERVICE_PORT_ON_HOST}"

log "Building Docker image: ${FULL_IMAGE_TAG}..."
pushd evaluation
docker build --push --platform linux/amd64 --tag "${FULL_IMAGE_TAG}" .
popd

# 3. Deploy to remote GCP instance via SSH
log "Deploying to remote host ${REMOTE_HOST}..."
ssh "${REMOTE_HOST}" << EOF
  # Function to log with timestamp on remote host
  log() {
      echo "[\$(date '+%Y-%m-%d %H:%M:%S %Z')] \$1"
  }
  
  log "Pulling Docker image: ${FULL_IMAGE_TAG} on remote host..."
  docker pull "${FULL_IMAGE_TAG}" || { log "Remote Docker pull failed."; exit 1; }

  log "Stopping and removing existing container (if any)..."
  docker stop "${CONTAINER_NAME}" || true
  docker rm "${CONTAINER_NAME}" || true

  log "Running new container: ${CONTAINER_NAME}..."
  docker run --detach --log-driver=gcplogs \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    --publish ${SERVICE_PORT_ON_HOST}:80 \
    --label application=inty-eval \
    --label environment=dev \
    --log-opt labels=application,environment \
    "${FULL_IMAGE_TAG}" || { log "Docker run failed."; exit 1; }
EOF

log "Performing sanity check..."
curl --user heartmate:heartmate.inty.cc --verbose --fail --retry 5 --retry-delay 5 "${SERVICE_PUBLIC_URL}" || { log "Sanity check failed."; exit 1; }

log "Deployment script finished successfully."
