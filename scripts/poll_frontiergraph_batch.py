from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.request


DEFAULT_API_KEY_PATH = "../key/openai_key_prashant.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poll a FrontierGraph OpenAI batch and optionally download output/error files.")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--api-key-path", default=DEFAULT_API_KEY_PATH)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--download-dir", default=None)
    parser.add_argument("--cancel", action="store_true", help="Cancel the batch before polling it.")
    parser.add_argument("--skip-download", action="store_true", help="Do not download output/error files even if IDs are present.")
    return parser.parse_args()


def load_api_key(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"API key file not found: {path}")
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError(f"API key file is empty: {path}")
    return key


def get_json(*, url: str, api_key: str) -> dict:
    req = urllib.request.Request(
        url=url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(*, url: str, api_key: str) -> dict:
    req = urllib.request.Request(
        url=url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="POST",
        data=b"",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_bytes(*, url: str, api_key: str) -> bytes:
    req = urllib.request.Request(
        url=url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    args = parse_args()
    api_key = load_api_key(Path(args.api_key_path))
    cancelled = None
    if args.cancel:
        cancelled = post_json(url=f"https://api.openai.com/v1/batches/{args.batch_id}/cancel", api_key=api_key)
    batch = get_json(url=f"https://api.openai.com/v1/batches/{args.batch_id}", api_key=api_key)
    payload = {
        "polled_at_utc": datetime.now(timezone.utc).isoformat(),
        "batch": batch,
    }
    if cancelled is not None:
        payload["cancel_response"] = cancelled

    download_dir = Path(args.download_dir) if args.download_dir else None
    if download_dir and not args.skip_download:
        if batch.get("output_file_id"):
            output_bytes = get_bytes(
                url=f"https://api.openai.com/v1/files/{batch['output_file_id']}/content",
                api_key=api_key,
            )
            output_path = download_dir / f"{args.batch_id}.output.jsonl"
            write_bytes(output_path, output_bytes)
            payload["downloaded_output_path"] = str(output_path)
        if batch.get("error_file_id"):
            error_bytes = get_bytes(
                url=f"https://api.openai.com/v1/files/{batch['error_file_id']}/content",
                api_key=api_key,
            )
            error_path = download_dir / f"{args.batch_id}.errors.jsonl"
            write_bytes(error_path, error_bytes)
            payload["downloaded_error_path"] = str(error_path)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote batch poll metadata: {out_json}")
    print(f"status={batch['status']}")


if __name__ == "__main__":
    main()
