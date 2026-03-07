from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def default_host() -> str:
    env_host = os.environ.get("ECON_RANKER_HOST")
    if env_host:
        return env_host
    if os.environ.get("K_SERVICE") or os.environ.get("PORT"):
        return "0.0.0.0"
    return "127.0.0.1"


def default_port() -> str:
    return os.environ.get("PORT") or os.environ.get("ECON_RANKER_PORT") or "8501"


def default_headless() -> bool:
    return env_flag("ECON_RANKER_HEADLESS", default=bool(os.environ.get("K_SERVICE")))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch FrontierGraph.")
    parser.add_argument(
        "--db",
        default=None,
        help="Optional SQLite database path. Defaults to data/processed/app_causalclaims.db when present.",
    )
    parser.add_argument("--host", default=default_host(), help="Streamlit server address.")
    parser.add_argument("--port", default=default_port(), help="Streamlit server port.")
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=default_headless(),
        help="Run without auto-opening a browser window.",
    )
    return parser.parse_args()


def default_db_path(repo_root: Path) -> Path:
    causalclaims = repo_root / "data" / "processed" / "app_causalclaims.db"
    demo = repo_root / "data" / "processed" / "app.db"
    if causalclaims.exists():
        return causalclaims
    return demo


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    app_path = repo_root / "app" / "streamlit_app.py"
    env_db = os.environ.get("ECON_OPPORTUNITY_DB", "").strip()
    db_path = Path(args.db).expanduser() if args.db else Path(env_db).expanduser() if env_db else default_db_path(repo_root)

    env = os.environ.copy()
    env["ECON_OPPORTUNITY_DB"] = str(db_path)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        str(args.host),
        "--server.port",
        str(args.port),
    ]
    if args.headless:
        cmd.extend(["--server.headless", "true"])

    return subprocess.run(cmd, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
