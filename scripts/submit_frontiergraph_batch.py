from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
import urllib.request


DEFAULT_API_KEY_PATH = "../key/openai_key_prashant.txt"
DEFAULT_HTTP_TIMEOUT = 1800


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload a FrontierGraph batch JSONL file and create a Batch job.")
    parser.add_argument("--jsonl-path", required=True)
    parser.add_argument("--api-key-path", default=DEFAULT_API_KEY_PATH)
    parser.add_argument("--completion-window", default="24h")
    parser.add_argument("--metadata-description", default="FrontierGraph extraction batch")
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--http-timeout", type=int, default=DEFAULT_HTTP_TIMEOUT)
    return parser.parse_args()


def load_api_key(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"API key file not found: {path}")
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError(f"API key file is empty: {path}")
    return key


def post_json(*, url: str, api_key: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed with HTTP {exc.code}: {body}") from exc


def post_multipart_file(*, url: str, api_key: str, file_path: Path, purpose: str, timeout: int) -> dict:
    boundary = f"----FrontierGraphBatch{uuid.uuid4().hex}"
    crlf = b"\r\n"
    parts = []

    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(b'Content-Disposition: form-data; name="purpose"')
    parts.append(b"")
    parts.append(purpose.encode("utf-8"))

    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode("utf-8")
    )
    parts.append(b"Content-Type: application/jsonl")
    parts.append(b"")
    parts.append(file_path.read_bytes())

    parts.append(f"--{boundary}--".encode("utf-8"))
    body = crlf.join(parts) + crlf

    req = urllib.request.Request(
        url=url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed with HTTP {exc.code}: {body}") from exc


def main() -> None:
    args = parse_args()
    jsonl_path = Path(args.jsonl_path)
    api_key = load_api_key(Path(args.api_key_path))
    uploaded = post_multipart_file(
        url="https://api.openai.com/v1/files",
        api_key=api_key,
        file_path=jsonl_path,
        purpose="batch",
        timeout=args.http_timeout,
    )
    batch = post_json(
        url="https://api.openai.com/v1/batches",
        api_key=api_key,
        payload={
            "input_file_id": uploaded["id"],
            "endpoint": "/v1/responses",
            "completion_window": args.completion_window,
            "metadata": {"description": args.metadata_description},
        },
        timeout=args.http_timeout,
    )

    payload = {
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "jsonl_path": str(jsonl_path),
        "uploaded_file": uploaded,
        "batch": batch,
    }
    out_json = Path(args.out_json) if args.out_json else jsonl_path.with_suffix(".submission.json")
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote submission metadata: {out_json}")
    print(f"batch_id={batch['id']}")


if __name__ == "__main__":
    main()
