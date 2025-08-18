#!/bin/bash -e

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $1"
}

INTY_SERVER_IMAGE_NAME="ghcr.io/nascentcore/inty-backend/inty-server"
IMAGE_TAG=$(git rev-parse --abbrev-ref HEAD)
DEPLOY_ENV="dev"
SERVICE_PORT_ON_HOST="8000"
REMOTE_HOST="inty"
SERVICE_PUBLIC_URL="https://dev.inty.sxwl.ai"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --environment)
      DEPLOY_ENV="$2"
      shift 2
      ;;
    --service-port-on-host)
      SERVICE_PORT_ON_HOST="$2"
      shift 2
      ;;
    --help|-h)
      log "Usage: $0 [--tag IMAGE_TAG]"
      log "  --tag IMAGE_TAG    Specify the image tag (default: main)"
      log "  --help, -h         Show this help message"
      exit 0
      ;;
    *)
      log "Unknown option: $1"
      log "Use --help for usage information"
      exit 1
      ;;
  esac
done



FULL_IMAGE_TAG="${INTY_SERVER_IMAGE_NAME}:${IMAGE_TAG}"
CONTAINER_NAME="inty-backend-${DEPLOY_ENV}"

log "--- Building and Deploying Inty Backend ---"
log "Image: ${FULL_IMAGE_TAG}"
log "Remote Host: ${REMOTE_HOST}"
log "Service Port on Host: ${SERVICE_PORT_ON_HOST}"

log "Building Docker image: ${FULL_IMAGE_TAG}..."
docker build --push --platform linux/amd64 --tag "${FULL_IMAGE_TAG}" .

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
    --publish ${SERVICE_PORT_ON_HOST}:8000 \
    --env LANGCHAIN_TRACING_V2=true \
    --env LANGCHAIN_PROJECT=inty-backend-${DEPLOY_ENV} \
    --env LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY} \
    --label application=inty-backend \
    --label environment=${DEPLOY_ENV} \
    --log-opt labels=application,environment \
    --volume /opt/inty-${DEPLOY_ENV}/config.yaml:/config.yaml \
    --volume /opt/inty-${DEPLOY_ENV}/inty-backend-key.json:/inty-backend-key.json \
    --volume /opt/inty-${DEPLOY_ENV}/inty-firebase-key.json:/inty-firebase-key.json \
    "${FULL_IMAGE_TAG}" || { log "Docker run failed."; exit 1; }

  log "Waiting for application startup..."
  # GEMINI: The original workflow waits for "Application startup complete".
  # Ensure your application logs this message upon successful startup.
  STARTUP_TIMEOUT_SECONDS=120
  ELAPSED_TIME=0
  while ! docker logs "${CONTAINER_NAME}" 2>&1 | grep -q "Application startup complete"
  do
    if [ \$ELAPSED_TIME -ge \$STARTUP_TIMEOUT_SECONDS ]; then
      log "Timeout waiting for application startup."
      exit 1
    fi
    sleep 1
    ELAPSED_TIME=\$((ELAPSED_TIME+1))
  done

  log "Application startup complete detected!"
EOF

log "Performing sanity check..."
curl --verbose --fail --retry 5 --retry-delay 5 "${SERVICE_PUBLIC_URL}" || { log "Sanity check failed."; exit 1; }

log "Deployment script finished successfully."
