#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$ROOT/site"
STAGE_DIR="${TMPDIR:-/tmp}/frontiergraph_site_cleanbuild"
REFRESH_DATA=0

for arg in "$@"; do
  case "$arg" in
    --refresh-data)
      REFRESH_DATA=1
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR/public"

cp "$SITE_DIR/package.json" "$STAGE_DIR/"
cp "$SITE_DIR/package-lock.json" "$STAGE_DIR/"
cp "$SITE_DIR/astro.config.mjs" "$STAGE_DIR/"
cp "$SITE_DIR/tsconfig.json" "$STAGE_DIR/"
cp -R "$SITE_DIR/src" "$STAGE_DIR/"
cp -R "$SITE_DIR/scripts" "$STAGE_DIR/"

# Astro only needs the tiny top-level assets during the build itself.
cp "$SITE_DIR/public/favicon.svg" "$STAGE_DIR/public/"
cp "$SITE_DIR/public/og-card.png" "$STAGE_DIR/public/"

(
  cd "$STAGE_DIR"
  npm install --prefer-offline --no-audit --no-fund
  node ./node_modules/.bin/astro build
)

mkdir -p "$SITE_DIR/dist"
rsync \
  -a \
  --delete \
  --exclude data \
  --exclude paper-assets \
  "$STAGE_DIR/dist/" \
  "$SITE_DIR/dist/"

# Keep the large static release assets out of the Astro build step.
mkdir -p "$SITE_DIR/dist/downloads"
rsync \
  -a \
  --delete \
  --exclude index.html \
  "$SITE_DIR/public/downloads/" \
  "$SITE_DIR/dist/downloads/"

if [[ -f "$STAGE_DIR/dist/downloads/index.html" ]]; then
  cp "$STAGE_DIR/dist/downloads/index.html" "$SITE_DIR/dist/downloads/index.html"
fi

rm -rf "$SITE_DIR/dist/paper-assets"
cp -R "$SITE_DIR/public/paper-assets" "$SITE_DIR/dist/"

if [[ "$REFRESH_DATA" -eq 1 ]]; then
  rm -rf "$SITE_DIR/dist/data"
fi

mkdir -p "$SITE_DIR/dist/data"
rsync \
  -a \
  --delete \
  "$SITE_DIR/public/data/" \
  "$SITE_DIR/dist/data/"
