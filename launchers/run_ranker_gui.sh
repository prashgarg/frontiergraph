#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$REPO_DIR/.ranker_runtime"
VENV_DIR="$RUNTIME_DIR/.venv"
LOG_DIR="$RUNTIME_DIR/logs"
LOG_FILE="$LOG_DIR/launcher.log"
PID_FILE="$RUNTIME_DIR/streamlit.pid"
STAMP_FILE="$RUNTIME_DIR/install.stamp"
PORT="8501"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

find_python() {
  local candidates=(
    "/usr/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11"
    "/usr/local/bin/python3.12"
    "/usr/local/bin/python3.11"
    "/opt/homebrew/bin/python3.12"
    "/opt/homebrew/bin/python3.11"
    "$HOME/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/CausalClaims/.venv/bin/python3.11"
    "$HOME/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/CausalClaims/.venv/bin/python3"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if [[ -d "$HOME/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg" ]]; then
    candidate="$(
      find "$HOME/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg" \
        -path '*/.venv/bin/python3.12' -o -path '*/.venv/bin/python3.11' -o -path '*/.venv/bin/python3' \
        2>/dev/null | head -n 1
    )"
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  fi
  return 1
}

PYTHON_BIN="$(find_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python 3.9 or newer is not installed. Install Python, then open this launcher again." | tee -a "$LOG_FILE" >&2
  exit 86
fi

echo "Using Python interpreter: $PYTHON_BIN" >>"$LOG_FILE"

if [[ -x "$VENV_DIR/bin/python" ]]; then
  if ! "$VENV_DIR/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    rm -rf "$VENV_DIR"
  fi
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR" >>"$LOG_FILE" 2>&1
fi

VENV_PY="$VENV_DIR/bin/python"

if [[ ! -f "$STAMP_FILE" || "$REPO_DIR/pyproject.toml" -nt "$STAMP_FILE" || "$REPO_DIR/app/streamlit_app.py" -nt "$STAMP_FILE" ]]; then
  "$VENV_PY" -m pip install "$REPO_DIR" >>"$LOG_FILE" 2>&1
  touch "$STAMP_FILE"
fi

if [[ -f "$PID_FILE" ]]; then
  EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" >/dev/null 2>&1; then
    printf '%s\n' "already_running"
    exit 0
  fi
fi

cd "$REPO_DIR"
nohup "$VENV_PY" -m src.run_ranker --headless --host 127.0.0.1 --port "$PORT" >>"$LOG_FILE" 2>&1 &
APP_PID=$!
echo "$APP_PID" >"$PID_FILE"

sleep 2
if ! kill -0 "$APP_PID" >/dev/null 2>&1; then
  echo "The ranker failed to start. See log: $LOG_FILE" >&2
  exit 88
fi

printf '%s\n' "started"
