from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = "https://api.openalex.org/works"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch specific OpenAlex work IDs with high concurrency and resume support.")
    parser.add_argument("--id-jsonl", required=True)
    parser.add_argument("--mailto", required=True)
    parser.add_argument("--api-key-path", required=True)
    parser.add_argument("--out-path", required=True)
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--concurrency", type=int, default=64)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--progress-every", type=int, default=500)
    return parser.parse_args()


def read_api_key(path_str: str) -> str:
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"OpenAlex key file not found: {path}")
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError(f"OpenAlex key file is empty: {path}")
    return key


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def iter_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def short_work_id(openalex_id: str) -> str:
    return openalex_id.rstrip("/").split("/")[-1]


def build_url(work_id: str, mailto: str, api_key: str) -> str:
    params = urlencode({"mailto": mailto, "api_key": api_key})
    return f"{API_BASE}/{short_work_id(work_id)}?{params}"


def fetch_one(*, work_row: dict[str, Any], mailto: str, api_key: str) -> dict[str, Any]:
    url = build_url(work_row["id"], mailto, api_key)
    request = Request(url, headers={"User-Agent": f"FrontierGraph OpenAlex ID fetcher ({mailto})"})
    for attempt in range(6):
        try:
            with urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
                payload["frontiergraph_bucket"] = work_row.get("frontiergraph_bucket")
                payload["frontiergraph_source_id"] = work_row.get("frontiergraph_source_id")
                payload["frontiergraph_source_name"] = work_row.get("frontiergraph_source_name")
                payload["frontiergraph_source_type"] = work_row.get("frontiergraph_source_type")
                payload["frontiergraph_decision_source"] = work_row.get("frontiergraph_decision_source")
                payload["frontiergraph_decision_reason"] = work_row.get("frontiergraph_decision_reason")
                payload["frontiergraph_manual_notes"] = work_row.get("frontiergraph_manual_notes")
                payload["frontiergraph_snapshot_origin"] = "openalex_api_recovered_by_id"
                return payload
        except Exception as exc:  # noqa: BLE001
            if attempt == 5:
                raise
            retry_after = max(2**attempt, 5 if "429" in str(exc) else 1)
            print(f"Fetch failed for {work_row['id']} ({exc}); retrying in {retry_after}s", file=sys.stderr, flush=True)
            time.sleep(retry_after)
    raise RuntimeError(f"Unreachable retry loop for {work_row['id']}")


def load_existing_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    return {row["id"] for row in iter_jsonl_gz(out_path)}


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("OPENALEX_API_KEY", "").strip() or read_api_key(args.api_key_path)
    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest_path)

    rows = list(iter_jsonl(Path(args.id_jsonl)))
    existing_ids = load_existing_ids(out_path)
    pending = [row for row in rows if row["id"] not in existing_ids]

    completed = 0
    failures: list[dict[str, str]] = []
    started_at = time.time()

    with gzip.open(out_path, "at", encoding="utf-8", compresslevel=1) as handle:
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
            futures = set()
            iterator = iter(pending)

            def submit_next() -> bool:
                try:
                    row = next(iterator)
                except StopIteration:
                    return False
                futures.add(pool.submit(fetch_one, work_row=row, mailto=args.mailto, api_key=api_key))
                return True

            for _ in range(max(1, args.concurrency)):
                if not submit_next():
                    break

            while futures:
                done, futures = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    try:
                        payload = future.result()
                        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                        completed += 1
                        if completed % args.progress_every == 0:
                            print(f"wrote {completed} rows", flush=True)
                    except Exception as exc:  # noqa: BLE001
                        failures.append({"error": str(exc)})
                        print(f"worker failed: {exc}", file=sys.stderr, flush=True)
                    submit_next()
                    if args.sleep_seconds > 0:
                        time.sleep(args.sleep_seconds)

    manifest = {
        "id_jsonl": args.id_jsonl,
        "mailto": args.mailto,
        "api_key_path": args.api_key_path,
        "requested_rows": len(rows),
        "already_present": len(existing_ids),
        "pending_rows": len(pending),
        "written_this_run": completed,
        "failure_count": len(failures),
        "elapsed_seconds": round(time.time() - started_at, 2),
        "out_path": str(out_path),
        "failures": failures[:50],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
