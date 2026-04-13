from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ONTOLOGY_DB = ROOT / "data" / "production" / "frontiergraph_ontology_compare_v1" / "baseline" / "ontology_v3.sqlite"
DEFAULT_PROGRESS_PATH = ROOT / "data" / "processed" / "research_allocation_v2" / "tail_force_mapping" / "progress.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show current progress for unresolved-tail force mapping.")
    parser.add_argument("--ontology-db", default=str(DEFAULT_ONTOLOGY_DB))
    parser.add_argument("--progress-path", default=str(DEFAULT_PROGRESS_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    progress_path = Path(args.progress_path)
    payload: dict[str, object] = {}
    if progress_path.exists():
        payload.update(json.loads(progress_path.read_text(encoding="utf-8")))
    conn = sqlite3.connect(args.ontology_db)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "tail_force_mappings" in tables:
        payload["mapped_labels_in_db"] = conn.execute("SELECT COUNT(*) FROM tail_force_mappings").fetchone()[0]
        payload["mapped_quality_breakdown"] = {
            band: count
            for band, count in conn.execute(
                "SELECT quality_band, COUNT(*) FROM tail_force_mappings GROUP BY quality_band ORDER BY COUNT(*) DESC"
            ).fetchall()
        }
    if "soft_map_pending" in tables:
        payload["pending_labels_total"] = conn.execute("SELECT COUNT(*) FROM soft_map_pending").fetchone()[0]
    conn.close()
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
