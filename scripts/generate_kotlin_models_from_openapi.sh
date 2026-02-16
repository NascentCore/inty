#!/usr/bin/env bash
# CREATED_BY_AGENT: Cursor GPT-5.2
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/generate_kotlin_models_from_openapi.sh [--out <dir>] [--package <pkg>] [--model-package <pkg>]
                                                [--serialization <kotlinx_serialization|jackson>]

What it does:
  1) Generate OpenAPI spec from FastAPI app (in memory, no committed file)
  2) Use OpenAPI Generator (Docker) to generate Kotlin models only

Defaults:
  --out             generated/kotlin_openapi_models
  --package         ai.sxwl.inty.openapi
  --model-package   ai.sxwl.inty.openapi.model
  --serialization   kotlinx_serialization

Notes:
  - Override generator image via env OPENAPI_GENERATOR_IMAGE (default: openapitools/openapi-generator-cli:latest)
EOF
}

OUT_DIR="generated/kotlin_openapi_models"
PACKAGE_NAME="ai.sxwl.inty.openapi"
MODEL_PACKAGE="ai.sxwl.inty.openapi.model"
SERIALIZATION_LIBRARY="kotlinx_serialization"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      OUT_DIR="${2:?missing value for --out}"
      shift 2
      ;;
    --package)
      PACKAGE_NAME="${2:?missing value for --package}"
      shift 2
      ;;
    --model-package)
      MODEL_PACKAGE="${2:?missing value for --model-package}"
      shift 2
      ;;
    --serialization)
      SERIALIZATION_LIBRARY="${2:?missing value for --serialization}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "${SERIALIZATION_LIBRARY}" != "kotlinx_serialization" && "${SERIALIZATION_LIBRARY}" != "jackson" ]]; then
  echo "--serialization must be one of: kotlinx_serialization, jackson" >&2
  exit 2
fi

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
OUT_ABS="${ROOT_DIR}/${OUT_DIR}"
OPENAPI_TEMP="${ROOT_DIR}/.openapi_generated.json"

OPENAPI_GENERATOR_IMAGE="${OPENAPI_GENERATOR_IMAGE:-openapitools/openapi-generator-cli:latest}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found in PATH" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found in PATH (required to run openapi-generator-cli image)" >&2
  exit 1
fi

# 任意退出时删除临时 OpenAPI 文件（含 Python 或 docker 失败时）
trap 'rm -f "${OPENAPI_TEMP}"' EXIT

echo "==> Generating OpenAPI spec from FastAPI app"
(cd "${ROOT_DIR}" && PYTHONPATH="${ROOT_DIR}" python3 -c "
import json
from backend.inty.main import app
with open('${OPENAPI_TEMP}', 'w', encoding='utf-8') as f:
    json.dump(app.openapi(), f, indent=2)
")

echo "==> Cleaning output dir: ${OUT_ABS}"
rm -rf "${OUT_ABS}"
mkdir -p "${OUT_ABS}"

echo "==> Generating Kotlin models (image: ${OPENAPI_GENERATOR_IMAGE})"
docker run --rm \
  -v "${ROOT_DIR}:/local" \
  "${OPENAPI_GENERATOR_IMAGE}" generate \
  -i "/local/.openapi_generated.json" \
  -g kotlin \
  -o "/local/${OUT_DIR}" \
  --global-property "models,modelDocs=false,modelTests=false,apis=false,apiDocs=false,apiTests=false,supportingFiles=false" \
  --additional-properties "packageName=${PACKAGE_NAME},modelPackage=${MODEL_PACKAGE},dateLibrary=java8,serializationLibrary=${SERIALIZATION_LIBRARY}"

echo "==> Done. Output: ${OUT_ABS}"
