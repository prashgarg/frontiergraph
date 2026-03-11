from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable


DEFAULT_DB = "data/processed/openalex/published_enriched/openalex_published_enriched.sqlite"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_extraction_v2/fwci_core150_adj150"
DEFAULT_COST_PER_PAPER = 0.0065145161290322585
DEFAULT_MIN_READY_PAPERS = 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a ranked source-cut sample and manifests for production extraction.")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--core-cut", type=int, default=150)
    parser.add_argument("--adjacent-cut", type=int, default=150)
    parser.add_argument("--min-ready-papers", type=int, default=DEFAULT_MIN_READY_PAPERS)
    parser.add_argument("--cost-per-paper", type=float, default=DEFAULT_COST_PER_PAPER)
    parser.add_argument("--min-year", type=int, default=1976)
    parser.add_argument("--max-year", type=int, default=2026)
    return parser.parse_args()


def zscore_map(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    nums = list(values.values())
    mu = mean(nums)
    sigma = pstdev(nums)
    if sigma == 0:
        return {k: 0.0 for k in values}
    return {k: (v - mu) / sigma for k, v in values.items()}


def short_work_id(work_id: str) -> str:
    return work_id.rstrip("/").split("/")[-1]


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def iter_batch_output_rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_source_stats(conn: sqlite3.Connection, *, min_ready_papers: int) -> list[dict[str, object]]:
    query = """
        SELECT
            wb.source_id,
            wb.source_display_name,
            wb.frontiergraph_bucket,
            COUNT(*) AS ready_papers,
            AVG(COALESCE(wb.fwci, 0.0)) AS mean_fwci,
            AVG(COALESCE(wb.cited_by_count, 0.0)) AS mean_citations
        FROM works_base wb
        JOIN works_abstracts wa ON wa.work_id = wb.work_id
        WHERE wb.frontiergraph_bucket IN ('core', 'adjacent')
          AND wa.abstract_ready_for_extraction = 1
        GROUP BY 1, 2, 3
        HAVING COUNT(*) >= ?
    """
    rows = []
    cur = conn.execute(query, (min_ready_papers,))
    for source_id, source_name, bucket, ready_papers, mean_fwci, mean_citations in cur:
        rows.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "bucket": bucket,
                "ready_papers": int(ready_papers),
                "mean_fwci": float(mean_fwci or 0.0),
                "mean_citations": float(mean_citations or 0.0),
            }
        )
    return rows


def add_scores(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_bucket: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_bucket[str(row["bucket"])].append(row)
    out: list[dict[str, object]] = []
    for bucket_rows in by_bucket.values():
        fwci_z = zscore_map({str(r["source_id"]): float(r["mean_fwci"]) for r in bucket_rows})
        cites_z = zscore_map({str(r["source_id"]): math.log(float(r["mean_citations"]) + 1.0) for r in bucket_rows})
        ready_z = zscore_map({str(r["source_id"]): math.log(float(r["ready_papers"])) for r in bucket_rows})
        for row in bucket_rows:
            sid = str(row["source_id"])
            row = dict(row)
            row["score_fwci"] = float(row["mean_fwci"])
            row["score_citations"] = float(row["mean_citations"])
            row["score_hybrid_a"] = fwci_z[sid] + 0.5 * ready_z[sid] + 0.5 * cites_z[sid]
            row["score_hybrid_b"] = fwci_z[sid] + 0.75 * ready_z[sid] + 0.25 * cites_z[sid]
            out.append(row)
    return out


def rank_sources(
    rows: list[dict[str, object]],
    *,
    score_key: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    core = [dict(r) for r in rows if r["bucket"] == "core"]
    adjacent = [dict(r) for r in rows if r["bucket"] == "adjacent"]
    sorter = lambda r: (-float(r[score_key]), -int(r["ready_papers"]), -float(r["mean_citations"]), str(r["source_name"]))
    core.sort(key=sorter)
    adjacent.sort(key=sorter)
    for rank, row in enumerate(core, start=1):
        row["rank"] = rank
    for rank, row in enumerate(adjacent, start=1):
        row["rank"] = rank
    return core, adjacent


def build_selected_work_rows(
    conn: sqlite3.Connection,
    *,
    selected_source_ids: set[str],
    min_year: int,
    max_year: int,
) -> list[dict[str, object]]:
    query = """
        SELECT
            wb.work_id,
            wb.title,
            wb.publication_year,
            wb.frontiergraph_bucket,
            wb.source_id,
            wb.source_display_name,
            wa.abstract_text
        FROM works_base wb
        JOIN works_abstracts wa ON wa.work_id = wb.work_id
        WHERE wa.abstract_ready_for_extraction = 1
          AND wb.source_id IN ({placeholders})
          AND wb.publication_year BETWEEN ? AND ?
        ORDER BY wb.publication_year DESC, wb.work_id ASC
    """
    placeholders = ",".join("?" for _ in selected_source_ids)
    cur = conn.execute(query.format(placeholders=placeholders), tuple(selected_source_ids) + (min_year, max_year))
    rows = []
    for work_id, title, year, bucket, source_id, source_name, abstract_text in cur:
        rows.append(
            {
                "openalex_work_id": work_id,
                "title": title or "",
                "abstract": abstract_text or "",
                "publication_year": int(year),
                "bucket": bucket,
                "source_id": source_id,
                "source_display_name": source_name or "",
            }
        )
    return rows


def collect_completed_successes(output_root: Path) -> tuple[set[str], list[dict[str, object]]]:
    done_ids: set[str] = set()
    rows: list[dict[str, object]] = []
    for path in sorted(output_root.glob("*/batch_*.output.jsonl")):
        for obj in iter_batch_output_rows(path):
            response = obj.get("response") or {}
            if response.get("status_code") != 200:
                continue
            custom_id = str(obj.get("custom_id") or "")
            if "__" not in custom_id:
                continue
            short_id = custom_id.split("__", 1)[0]
            if short_id in done_ids:
                continue
            done_ids.add(short_id)
            rows.append(
                {
                    "short_work_id": short_id,
                    "custom_id": custom_id,
                    "batch_output_path": str(path),
                }
            )
    return done_ids, rows


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    source_dir = output_root / "source_lists"
    sample_dir = output_root / "sample"
    completed_dir = output_root / "completed"
    analysis_dir = output_root / "analysis"
    completed_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(f"file:{Path(args.db)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    scored_rows = add_scores(fetch_source_stats(conn, min_ready_papers=args.min_ready_papers))
    core_fwci, adjacent_fwci = rank_sources(scored_rows, score_key="score_fwci")
    core_cites, adjacent_cites = rank_sources(scored_rows, score_key="score_citations")
    core_ha, adjacent_ha = rank_sources(scored_rows, score_key="score_hybrid_a")
    core_hb, adjacent_hb = rank_sources(scored_rows, score_key="score_hybrid_b")

    selected_core = core_fwci[: args.core_cut]
    selected_adjacent = adjacent_fwci[: args.adjacent_cut]
    selected_source_ids = {str(r["source_id"]) for r in selected_core + selected_adjacent}
    selected_work_rows = build_selected_work_rows(
        conn,
        selected_source_ids=selected_source_ids,
        min_year=args.min_year,
        max_year=args.max_year,
    )

    by_year: dict[int, int] = defaultdict(int)
    for row in selected_work_rows:
        by_year[int(row["publication_year"])] += 1

    done_short_ids, done_rows = collect_completed_successes(Path("data/production/frontiergraph_extraction_v2/batch_outputs"))
    selected_short_ids = {short_work_id(str(r["openalex_work_id"])) for r in selected_work_rows}
    selected_done_short_ids = done_short_ids & selected_short_ids
    remaining_rows = [row for row in selected_work_rows if short_work_id(str(row["openalex_work_id"])) not in selected_done_short_ids]

    completed_lookup = {row["short_work_id"]: row for row in done_rows if row["short_work_id"] in selected_done_short_ids}
    completed_selected_rows = []
    for row in selected_work_rows:
        sid = short_work_id(str(row["openalex_work_id"]))
        if sid in completed_lookup:
            enriched = dict(row)
            enriched.update(completed_lookup[sid])
            completed_selected_rows.append(enriched)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Write source lists.
    source_fields = [
        "rank",
        "source_id",
        "source_name",
        "bucket",
        "ready_papers",
        "mean_fwci",
        "mean_citations",
        "score_fwci",
        "score_citations",
        "score_hybrid_a",
        "score_hybrid_b",
    ]
    write_csv(source_dir / "core_mean_fwci_top150.csv", selected_core, source_fields)
    write_csv(source_dir / "adjacent_mean_fwci_top150.csv", selected_adjacent, source_fields)
    write_csv(source_dir / "core_mean_citations_ranked.csv", core_cites, source_fields)
    write_csv(source_dir / "adjacent_mean_citations_ranked.csv", adjacent_cites, source_fields)
    write_csv(source_dir / "core_hybrid_a_ranked.csv", core_ha, source_fields)
    write_csv(source_dir / "adjacent_hybrid_a_ranked.csv", adjacent_ha, source_fields)
    write_csv(source_dir / "core_hybrid_b_ranked.csv", core_hb, source_fields)
    write_csv(source_dir / "adjacent_hybrid_b_ranked.csv", adjacent_hb, source_fields)

    # Write sample rows.
    sample_dir.mkdir(parents=True, exist_ok=True)
    with (sample_dir / "fwci_core150_adj150_all.jsonl").open("w", encoding="utf-8") as handle:
        for row in selected_work_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (sample_dir / "fwci_core150_adj150_remaining.jsonl").open("w", encoding="utf-8") as handle:
        for row in remaining_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (completed_dir / "completed_successes.jsonl").open("w", encoding="utf-8") as handle:
        for row in completed_selected_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts_by_year = [{"year": year, "papers": by_year[year], "estimated_cost_usd": round(by_year[year] * args.cost_per_paper, 2)} for year in sorted(by_year)]
    remaining_by_year: dict[int, int] = defaultdict(int)
    for row in remaining_rows:
        remaining_by_year[int(row["publication_year"])] += 1

    analysis = {
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection": {
            "ranking": "mean_fwci",
            "core_cut": args.core_cut,
            "adjacent_cut": args.adjacent_cut,
            "min_ready_papers": args.min_ready_papers,
            "min_year": args.min_year,
            "max_year": args.max_year,
            "rationale": "Separate rankings within core and adjacent by mean work-level FWCI among extraction-ready papers, with a minimum ready-paper floor for stability. This preserves strong economics journals while retaining high-impact adjacent venues over the full 1976-2026 span.",
        },
        "totals": {
            "selected_sources_core": len(selected_core),
            "selected_sources_adjacent": len(selected_adjacent),
            "selected_papers": len(selected_work_rows),
            "selected_estimated_cost_usd": round(len(selected_work_rows) * args.cost_per_paper, 2),
            "already_completed_successes": len(completed_selected_rows),
            "remaining_papers": len(remaining_rows),
            "remaining_estimated_cost_usd": round(len(remaining_rows) * args.cost_per_paper, 2),
        },
        "counts_by_year": counts_by_year,
        "remaining_counts_by_year": [
            {"year": year, "papers": remaining_by_year[year], "estimated_cost_usd": round(remaining_by_year[year] * args.cost_per_paper, 2)}
            for year in sorted(remaining_by_year)
        ],
        "files": {
            "core_sources": str(source_dir / "core_mean_fwci_top150.csv"),
            "adjacent_sources": str(source_dir / "adjacent_mean_fwci_top150.csv"),
            "all_sample_jsonl": str(sample_dir / "fwci_core150_adj150_all.jsonl"),
            "remaining_sample_jsonl": str(sample_dir / "fwci_core150_adj150_remaining.jsonl"),
            "completed_successes_jsonl": str(completed_dir / "completed_successes.jsonl"),
        },
    }
    write_json(analysis_dir / f"fwci_core150_adj150_selection_{timestamp}.json", analysis)
    write_json(analysis_dir / "fwci_core150_adj150_selection_latest.json", analysis)
    print(json.dumps(analysis["totals"], indent=2))


if __name__ == "__main__":
    main()
