#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$ROOT/site"
PORT="${PORT:-4321}"
HOST="${HOST:-127.0.0.1}"

cd "$SITE_DIR"
exec npm run dev -- --host "$HOST" --port "$PORT"
