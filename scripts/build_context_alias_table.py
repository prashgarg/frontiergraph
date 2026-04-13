from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.context_normalization import normalize_context_value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic context alias table from current shortlist and broader ontology context usage.")
    parser.add_argument(
        "--routed-shortlist",
        default="outputs/paper/30_vnext_routed_shortlist/routed_shortlist.csv",
        dest="routed_shortlist",
    )
    parser.add_argument(
        "--concept-db",
        default="data/production/frontiergraph_concept_public/concept_hard_app.sqlite",
        dest="concept_db",
    )
    parser.add_argument(
        "--out-csv",
        default="data/processed/ontology_vnext_proto_v1/context_alias_table.csv",
        dest="out_csv",
    )
    parser.add_argument(
        "--out-note",
        default="next_steps/context_normalization_working_note.md",
        dest="out_note",
    )
    return parser.parse_args()


def _count_json_values(counter: Counter[str], raw: str) -> None:
    if not raw:
        return
    try:
        items = json.loads(raw)
    except Exception:
        return
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                value = str(item.get("value", "")).strip()
            else:
                value = str(item).strip()
            if value:
                counter[value] += 1


def _collect_counts(routed_path: Path, concept_db: Path) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    routed = pd.read_csv(routed_path)
    for col in ["source_top_geographies_json", "target_top_geographies_json", "dominant_countries_json"]:
        if col in routed.columns:
            for raw in routed[col].dropna():
                _count_json_values(counter, str(raw))

    conn = sqlite3.connect(f"file:{concept_db}?mode=ro", uri=True)
    try:
        cur = conn.cursor()
        for table, col in [("node_details", "top_countries"), ("concept_edge_contexts", "dominant_countries_json")]:
            for (raw,) in cur.execute(f"SELECT {col} FROM {table}"):
                if raw:
                    _count_json_values(counter, str(raw))
    finally:
        conn.close()

    rows = []
    for raw_value, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].lower())):
        normalized = normalize_context_value(raw_value)
        rows.append(
            {
                "raw_value": raw_value,
                "normalized_display": normalized["normalized_display"],
                "context_type": normalized["context_type"],
                "granularity": normalized["granularity"],
                "canonical_context_id": normalized["canonical_context_id"],
                "status": normalized["status"],
                "observed_count": int(count),
            }
        )
    return pd.DataFrame(rows)


def _write_note(alias_df: pd.DataFrame, out_path: Path) -> None:
    top_rows = alias_df.head(40)
    lines = [
        "# Context Normalization Working Note",
        "",
        "## Design choice",
        "",
        "Blocs and groups stay as blocs and groups in the canonical normalized field.",
        "",
        "We do not collapse `OECD`, `EU-15`, `BRICS`, or `G7` into constituent countries by default because that would blur evidence provenance.",
        "A relation observed at the bloc level is not the same thing as direct country-level evidence.",
        "",
        "If we later want bloc membership reasoning, it should be added as separate metadata rather than replacing the observed context label.",
        "",
        "## Table schema",
        "",
        "- `raw_value`",
        "- `normalized_display`",
        "- `context_type`",
        "- `granularity`",
        "- `canonical_context_id`",
        "- `status`",
        "- `observed_count`",
        "",
        "## Early normalization policy",
        "",
        "- normalize obvious aliases: `CHN -> China`, `USA -> United States`, `GBR -> United Kingdom`, `KOR -> South Korea`, etc.",
        "- keep blocs distinct: `OECD countries`, `BRICS countries`, `G7 countries`, `EU-15 countries`, `Euro Area countries`",
        "- treat ambiguous `NA` as `unknown context` for now",
        "- keep study-defined groups as groups rather than forcing them into countries",
        "",
        "## Top normalized values",
        "",
    ]
    for row in top_rows.itertuples(index=False):
        lines.append(
            f"- `{row.raw_value}` -> `{row.normalized_display}` | type `{row.context_type}` | granularity `{row.granularity}` | status `{row.status}` | count `{int(row.observed_count)}`"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_csv = Path(args.out_csv)
    out_note = Path(args.out_note)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_note.parent.mkdir(parents=True, exist_ok=True)

    alias_df = _collect_counts(Path(args.routed_shortlist), Path(args.concept_db))
    alias_df.to_csv(out_csv, index=False)
    _write_note(alias_df, out_note)
    print(f"Wrote context alias table to {out_csv}")
    print(f"Wrote context normalization note to {out_note}")


if __name__ == "__main__":
    main()
