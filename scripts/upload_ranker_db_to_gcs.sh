#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

LOCAL_DB="${1:-$REPO_DIR/data/processed/app_causalclaims.db}"
DATA_BUCKET="${2:-${DATA_BUCKET:-}}"
DB_FILENAME="${3:-${DB_FILENAME:-app_causalclaims.db}}"

if [[ -z "$DATA_BUCKET" ]]; then
  echo "Usage: scripts/upload_ranker_db_to_gcs.sh [local_db] <bucket> [object_name]"
  echo "Or set DATA_BUCKET in the shell environment."
  exit 1
fi

if [[ ! -f "$LOCAL_DB" ]]; then
  echo "Database file not found: $LOCAL_DB"
  exit 1
fi

TARGET_URI="gs://${DATA_BUCKET}/${DB_FILENAME}"

echo "Uploading $LOCAL_DB to $TARGET_URI"
gcloud storage cp "$LOCAL_DB" "$TARGET_URI"
echo "Upload complete."
