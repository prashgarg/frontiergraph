from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.openalex.org/works"


@dataclass
class YearState:
    year: int
    query: str
    next_cursor: str | None
    pages_fetched: int
    records_fetched: int
    complete: bool
    started_at: str
    updated_at: str
    output_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download full OpenAlex work objects for recent journal-hosted economics-tagged articles.")
    parser.add_argument("--mailto", required=True)
    parser.add_argument("--api-key-path", default="../key/openalex_api_key.txt")
    parser.add_argument("--out-dir", default="data/raw/openalex/journal_field20_full_recent")
    parser.add_argument("--from-year", type=int, default=2024)
    parser.add_argument("--to-year", type=int, default=date.today().year)
    parser.add_argument("--field-id", default="20")
    parser.add_argument("--per-page", type=int, default=200)
    parser.add_argument("--max-pages-per-year", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.1)
    parser.add_argument("--parallel-years", type=int, default=1)
    parser.add_argument("--force-restart-year", action="append", default=[])
    return parser.parse_args()


def read_api_key(path_str: str) -> str:
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"OpenAlex key file not found: {path}")
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError(f"OpenAlex key file is empty: {path}")
    return key


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def year_date_window(year: int, today: date) -> tuple[str, str]:
    start = date(year, 1, 1)
    end = date(year, 12, 31) if year < today.year else today
    return start.isoformat(), end.isoformat()


def build_filter(field_id: str, year: int, today: date) -> str:
    from_date, to_date = year_date_window(year, today)
    return ",".join(
        [
            f"primary_topic.field.id:{field_id}",
            "language:en",
            "type:article",
            "primary_location.source.type:journal",
            f"from_publication_date:{from_date}",
            f"to_publication_date:{to_date}",
        ]
    )


def fetch_page(*, api_key: str, mailto: str, filter_expr: str, cursor: str, per_page: int) -> dict[str, Any]:
    params = {
        "filter": filter_expr,
        "per-page": str(per_page),
        "cursor": cursor,
        "mailto": mailto,
        "api_key": api_key,
    }
    url = f"{API_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": f"FrontierGraph OpenAlex full recent downloader ({mailto})"})

    for attempt in range(6):
        try:
            with urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            if attempt == 5:
                raise
            retry_after = max(2**attempt, 5 if "429" in str(exc) else 1)
            print(f"Request failed ({exc}); retrying in {retry_after}s", file=sys.stderr, flush=True)
            time.sleep(retry_after)
    raise RuntimeError("Unreachable retry loop")


def load_year_state(path: Path) -> YearState | None:
    if not path.exists():
        return None
    return YearState(**json.loads(path.read_text(encoding="utf-8")))


def write_year_state(path: Path, state: YearState) -> None:
    state.updated_at = now_iso()
    path.write_text(json.dumps(asdict(state), indent=2) + "\n", encoding="utf-8")


def reset_year_files(out_path: Path, state_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    if state_path.exists():
        state_path.unlink()


def run_year(
    *,
    year: int,
    api_key: str,
    mailto: str,
    field_id: str,
    out_dir: Path,
    state_dir: Path,
    per_page: int,
    max_pages_per_year: int | None,
    sleep_seconds: float,
    force_restart: bool,
) -> dict[str, Any]:
    filter_expr = build_filter(field_id, year, date.today())
    out_path = out_dir / f"openalex_field{field_id}_journal_articles_en_full_{year}.jsonl.gz"
    state_path = state_dir / f"{year}.json"

    if force_restart:
        reset_year_files(out_path, state_path)

    state = load_year_state(state_path)
    if state and state.complete:
        print(f"{year}: already complete ({state.records_fetched} records)", flush=True)
        return {"year": year, "records": state.records_fetched, "pages": state.pages_fetched, "complete": True}

    if state is None:
        state = YearState(
            year=year,
            query=filter_expr,
            next_cursor="*",
            pages_fetched=0,
            records_fetched=0,
            complete=False,
            started_at=now_iso(),
            updated_at=now_iso(),
            output_path=str(out_path),
        )
        write_year_state(state_path, state)

    pages_this_run = 0
    with gzip.open(out_path, "at", encoding="utf-8") as fh:
        while not state.complete:
            payload = fetch_page(
                api_key=api_key,
                mailto=mailto,
                filter_expr=filter_expr,
                cursor=state.next_cursor or "*",
                per_page=per_page,
            )
            results = payload.get("results", [])
            meta = payload.get("meta", {})
            next_cursor = meta.get("next_cursor")

            for row in results:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

            state.pages_fetched += 1
            pages_this_run += 1
            state.records_fetched += len(results)
            state.next_cursor = next_cursor
            state.complete = next_cursor is None or len(results) == 0
            write_year_state(state_path, state)

            print(f"{year}: page {state.pages_fetched} | fetched {len(results)} | total {state.records_fetched}", flush=True)

            if state.complete:
                break
            if max_pages_per_year is not None and pages_this_run >= max_pages_per_year:
                break
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    return {"year": year, "records": state.records_fetched, "pages": state.pages_fetched, "complete": state.complete}


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("OPENALEX_API_KEY", "").strip() or read_api_key(args.api_key_path)

    out_dir = Path(args.out_dir)
    state_dir = out_dir / "_state"
    ensure_dir(out_dir)
    ensure_dir(state_dir)

    force_years = {int(y) for y in args.force_restart_year}
    years = list(range(args.from_year, args.to_year + 1))
    worker_count = max(1, int(args.parallel_years))
    summary: list[dict[str, Any]] = []

    if worker_count == 1:
        for year in years:
            summary.append(
                run_year(
                    year=year,
                    api_key=api_key,
                    mailto=args.mailto,
                    field_id=args.field_id,
                    out_dir=out_dir,
                    state_dir=state_dir,
                    per_page=args.per_page,
                    max_pages_per_year=args.max_pages_per_year,
                    sleep_seconds=args.sleep_seconds,
                    force_restart=year in force_years,
                )
            )
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = {
                pool.submit(
                    run_year,
                    year=year,
                    api_key=api_key,
                    mailto=args.mailto,
                    field_id=args.field_id,
                    out_dir=out_dir,
                    state_dir=state_dir,
                    per_page=args.per_page,
                    max_pages_per_year=args.max_pages_per_year,
                    sleep_seconds=args.sleep_seconds,
                    force_restart=year in force_years,
                ): year
                for year in years
            }
            for future in as_completed(futures):
                summary.append(future.result())

    manifest = {
        "query_type": "openalex_journal_field_full_recent",
        "field_id": args.field_id,
        "from_year": args.from_year,
        "to_year": args.to_year,
        "query_date_utc": now_iso(),
        "output_dir": str(out_dir),
        "year_summaries": sorted(summary, key=lambda item: item["year"]),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
