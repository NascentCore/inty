#！/bin/bash -e
# 记录计时器的函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $1"
}

INTY_SERVER_IMAGE_NAME="ghcr.io/nascentcore/inty-backend/inty-server"
# 使用短提交作为图片标签
IMAGE_TAG=$(git rev-parse HEAD | cut -c 1-7)
DEPLOY_ENV="dev"
REMOTE_HOST="inty"
# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --environment)
      DEPLOY_ENV="$2"
      shift 2
      ;;
    --help|-h)
      log "Usage: $0 [--environment DEPLOY_ENV]"
      log "  --environment DEPLOY_ENV    Specify the environment to deploy to (default: dev)"
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

if [ "$DEPLOY_ENV" == "dev" ]; then
# 回复github dev部署环境里的环境变量
  SERVICE_PORT_ON_HOST="8000"
  SERVICE_PUBLIC_URL="https://dev.inty.sxwl.ai"
elif [ "$DEPLOY_ENV" == "prod" ]; then
# 对应 github prod 配置环境里的环境变量
  SERVICE_PORT_ON_HOST="8100"
  SERVICE_PUBLIC_URL="https://app.inty.cc"
else
  log "Unknown environment: $DEPLOY_ENV"
  exit 1
fi

FULL_IMAGE_TAG="${INTY_SERVER_IMAGE_NAME}:${IMAGE_TAG}"
CONTAINER_NAME="inty-backend-${DEPLOY_ENV}"

log "--- Building and Deploying Inty Backend ---"
log "Image: ${FULL_IMAGE_TAG}"
log "Remote Host: ${REMOTE_HOST}"
log "Service Port on Host: ${SERVICE_PORT_ON_HOST}"

log "Building Docker image: ${FULL_IMAGE_TAG}..."
docker build --push --platform linux/amd64 --tag "${FULL_IMAGE_TAG}" .
＃3。通过 SSH 部署到远程 GCP 实例
log "Deploying to remote host ${REMOTE_HOST}..."
ssh "${REMOTE_HOST}" << EOF
# 在远程主机上记录时间的函数
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
    --label application=inty-backend \
    --label environment=${DEPLOY_ENV} \
    --log-opt labels=application,environment \
    --volume /opt/inty-${DEPLOY_ENV}/config.yaml:/config.yaml \
    --volume /opt/inty-${DEPLOY_ENV}/inty-backend-key.json:/inty-backend-key.json \
    --volume /opt/inty-${DEPLOY_ENV}/inty-firebase-key.json:/inty-firebase-key.json \
    "${FULL_IMAGE_TAG}" || { log "Docker run failed."; exit 1; }

  log "Waiting for application startup..."
# GEMINI：原始工作流程等待“应用程序启动完成”。
#确保您的应用程序在成功启动时记录此消息。
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
