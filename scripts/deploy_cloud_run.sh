#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${1:-$REPO_DIR/deploy/public_release.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE"
  echo "Copy deploy/public_release.env.example to deploy/public_release.env and fill it in."
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

required_vars=(
  PROJECT_ID
  REGION
  SERVICE_NAME
  AR_REPOSITORY
  IMAGE_NAME
  CPU
  MEMORY
  TIMEOUT
  CONCURRENCY
  MIN_INSTANCES
  MAX_INSTANCES
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required setting: $var_name"
    exit 1
  fi
done

IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Using image: $IMAGE_URI"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project "$PROJECT_ID"

if ! gcloud artifacts repositories describe "$AR_REPOSITORY" \
  --location "$REGION" \
  --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$AR_REPOSITORY" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Container images for FrontierGraph" \
    --project "$PROJECT_ID"
fi

gcloud builds submit "$REPO_DIR" \
  --tag "$IMAGE_URI" \
  --project "$PROJECT_ID"

env_vars=(
  "ECON_RANKER_HOST=0.0.0.0"
  "ECON_RANKER_HEADLESS=true"
)

optional_env_vars=(
  FRONTIERGRAPH_POSTHOG_KEY
  FRONTIERGRAPH_POSTHOG_HOST
  FRONTIERGRAPH_FEEDBACK_EMAIL
)

deploy_args=(
  gcloud run deploy "$SERVICE_NAME"
  --project "$PROJECT_ID"
  --region "$REGION"
  --platform managed
  --allow-unauthenticated
  --execution-environment gen2
  --image "$IMAGE_URI"
  --cpu "$CPU"
  --memory "$MEMORY"
  --timeout "$TIMEOUT"
  --concurrency "$CONCURRENCY"
  --min-instances "$MIN_INSTANCES"
  --max-instances "$MAX_INSTANCES"
)

if [[ -n "${DATA_BUCKET:-}" ]]; then
  DB_FILENAME="${DB_FILENAME:-frontiergraph-economics-public.db}"
  CONCEPT_DB_FILENAME="${CONCEPT_DB_FILENAME:-}"
  MOUNT_PATH="${MOUNT_PATH:-/mnt/ranker-data}"
  VOLUME_NAME="${VOLUME_NAME:-ranker-data}"
  env_vars+=("ECON_OPPORTUNITY_DB=${MOUNT_PATH}/${DB_FILENAME}")
  if [[ -n "$CONCEPT_DB_FILENAME" ]]; then
    env_vars+=("ECON_CONCEPT_DB=${MOUNT_PATH}/${CONCEPT_DB_FILENAME}")
  fi
  deploy_args+=(
    --add-volume "name=${VOLUME_NAME},type=cloud-storage,bucket=${DATA_BUCKET},readonly=true"
    --add-volume-mount "volume=${VOLUME_NAME},mount-path=${MOUNT_PATH}"
  )
else
  echo "DATA_BUCKET is not set. Deploying the tiny packaged demo DB instead of the economics corpus."
  env_vars+=("ECON_OPPORTUNITY_DB=/app/data/processed/app.db")
fi

for var_name in "${optional_env_vars[@]}"; do
  if [[ -n "${!var_name:-}" ]]; then
    env_vars+=("${var_name}=${!var_name}")
  fi
done

SET_ENV_VARS="$(IFS=,; echo "${env_vars[*]}")"
deploy_args+=(--set-env-vars "$SET_ENV_VARS")

"${deploy_args[@]}"

SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format='value(status.url)')"

echo
echo "App deployed successfully."
echo "Service URL: $SERVICE_URL"
