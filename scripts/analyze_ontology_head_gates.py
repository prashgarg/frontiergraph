from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB = Path("data/production/frontiergraph_ontology_v3/ontology_v3.sqlite")
DEFAULT_OUTPUT_ROOT = Path("data/production/frontiergraph_ontology_v3/analysis/head_gate_selection")
DEFAULT_NOTE = Path("paper/frontiergraph_head_gate_deliberation.md")


@dataclass(frozen=True)
class GateRow:
    min_distinct_papers: int
    min_distinct_journals: int
    candidate_labels: int
    label_share: float
    candidate_instances: int
    instance_share: float
    candidate_edge_papers: int
    edge_paper_share: float
    candidate_partner5_labels: int
    candidate_partner5_share_within: float
    candidate_partner3_labels: int
    candidate_partner3_share_within: float


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def fetch_base_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        WITH node_edge_stats AS (
            WITH directed AS (
                SELECT source_normalized_label AS label, target_normalized_label AS partner, custom_id
                FROM edge_instances
                UNION ALL
                SELECT target_normalized_label AS label, source_normalized_label AS partner, custom_id
                FROM edge_instances
            )
            SELECT
                label AS normalized_label,
                COUNT(DISTINCT partner) AS distinct_partners,
                COUNT(DISTINCT custom_id) AS distinct_edge_papers
            FROM directed
            GROUP BY label
        )
        SELECT
            ns.normalized_label,
            ns.instance_count,
            ns.distinct_papers,
            ns.distinct_journals,
            COALESCE(es.distinct_partners, 0) AS distinct_partners,
            COALESCE(es.distinct_edge_papers, 0) AS distinct_edge_papers
        FROM node_strings ns
        LEFT JOIN node_edge_stats es
          ON es.normalized_label = ns.normalized_label
        """
    ).fetchall()


def compute_grid(rows: list[sqlite3.Row]) -> tuple[list[GateRow], dict[str, int | float]]:
    paper_thresholds = [3, 5, 8, 10, 15, 20]
    journal_thresholds = [1, 2, 3, 5, 8]
    total_labels = len(rows)
    total_instances = sum(int(row["instance_count"]) for row in rows)
    total_edge_papers = sum(int(row["distinct_edge_papers"]) for row in rows)
    grid: list[GateRow] = []
    for min_papers in paper_thresholds:
        for min_journals in journal_thresholds:
            passed = [
                row
                for row in rows
                if int(row["distinct_papers"]) >= min_papers and int(row["distinct_journals"]) >= min_journals
            ]
            candidate_labels = len(passed)
            candidate_instances = sum(int(row["instance_count"]) for row in passed)
            candidate_edge_papers = sum(int(row["distinct_edge_papers"]) for row in passed)
            partner5 = sum(1 for row in passed if int(row["distinct_partners"]) >= 5)
            partner3 = sum(1 for row in passed if int(row["distinct_partners"]) >= 3)
            grid.append(
                GateRow(
                    min_distinct_papers=min_papers,
                    min_distinct_journals=min_journals,
                    candidate_labels=candidate_labels,
                    label_share=(candidate_labels / total_labels) if total_labels else 0.0,
                    candidate_instances=candidate_instances,
                    instance_share=(candidate_instances / total_instances) if total_instances else 0.0,
                    candidate_edge_papers=candidate_edge_papers,
                    edge_paper_share=(candidate_edge_papers / total_edge_papers) if total_edge_papers else 0.0,
                    candidate_partner5_labels=partner5,
                    candidate_partner5_share_within=(partner5 / candidate_labels) if candidate_labels else 0.0,
                    candidate_partner3_labels=partner3,
                    candidate_partner3_share_within=(partner3 / candidate_labels) if candidate_labels else 0.0,
                )
            )
    totals = {
        "total_labels": total_labels,
        "total_instances": total_instances,
        "total_edge_papers_sum": total_edge_papers,
    }
    return grid, totals


def choose_recommendation(grid: list[GateRow]) -> GateRow:
    preferred = [
        row
        for row in grid
        if row.min_distinct_papers == 10 and row.min_distinct_journals == 3
    ]
    if preferred:
        return preferred[0]
    return sorted(
        grid,
        key=lambda row: (
            abs(row.instance_share - 0.35),
            abs(row.candidate_labels - 50000),
        ),
    )[0]


def write_csv(grid: list[GateRow], output_path: Path) -> None:
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(GateRow.__dataclass_fields__.keys()))
        writer.writeheader()
        for row in grid:
            writer.writerow(row.__dict__)


def write_json(grid: list[GateRow], totals: dict[str, int | float], recommendation: GateRow, output_path: Path) -> None:
    payload = {
        "totals": totals,
        "recommendation": recommendation.__dict__,
        "grid": [row.__dict__ for row in grid],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown(grid: list[GateRow], totals: dict[str, int | float], recommendation: GateRow, output_path: Path) -> None:
    lines = [
        "# Ontology Head Gate Selection",
        "",
        f"- total normalized labels: `{totals['total_labels']}`",
        f"- total node instances: `{totals['total_instances']}`",
        "",
        "## Recommendation",
        "",
        f"Recommended support gate: `distinct_papers >= {recommendation.min_distinct_papers}` and `distinct_journals >= {recommendation.min_distinct_journals}`.",
        "",
        f"This yields `{recommendation.candidate_labels}` head candidates ({recommendation.label_share:.2%} of normalized labels) covering `{recommendation.candidate_instances}` node instances ({recommendation.instance_share:.2%} of node-instance mass).",
        "",
        f"Within that candidate pool, `{recommendation.candidate_partner5_labels}` labels ({recommendation.candidate_partner5_share_within:.2%}) already have at least 5 distinct graph partners, which suggests the support gate is filtering toward reusable graph concepts rather than isolated local strings.",
        "",
        "## Grid",
        "",
        "| min papers | min journals | labels | % labels | instances | % instances | >=5 partners | % within pool |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(grid, key=lambda item: (item.min_distinct_papers, item.min_distinct_journals)):
        lines.append(
            f"| {row.min_distinct_papers} | {row.min_distinct_journals} | {row.candidate_labels} | {row.label_share:.2%} | {row.candidate_instances} | {row.instance_share:.2%} | {row.candidate_partner5_labels} | {row.candidate_partner5_share_within:.2%} |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_note(grid: list[GateRow], recommendation: GateRow, note_path: Path) -> None:
    lines = [
        "# FrontierGraph Head Gate Deliberation",
        "",
        "## Purpose",
        "",
        "This note records the parameter-selection process for the ontology support gate. The goal is to choose a head-candidate rule that is strong enough to remove local, context-heavy labels, but not so strict that it wipes out reusable economics concepts.",
        "",
        "## What was tested",
        "",
        "A grid was computed over support gates of the form:",
        "",
        "- `distinct_papers >= P`",
        "- `distinct_journals >= J`",
        "",
        "for:",
        "",
        "- `P in {3, 5, 8, 10, 15, 20}`",
        "- `J in {1, 2, 3, 5, 8}`",
        "",
        "For each grid point, the analysis measured:",
        "",
        "- candidate label count",
        "- candidate-label share of the full normalized-label universe",
        "- candidate node-instance coverage",
        "- a graph-reuse overlay based on distinct graph partners",
        "",
        "## Recommendation",
        "",
        f"Use `distinct_papers >= {recommendation.min_distinct_papers}` and `distinct_journals >= {recommendation.min_distinct_journals}` as the base support gate for heads.",
        "",
        "Rationale:",
        "",
        f"- It yields `{recommendation.candidate_labels}` candidates, which is materially smaller than the full normalized-label universe but still large enough to preserve breadth.",
        f"- It covers `{recommendation.instance_share:.2%}` of node-instance mass before any tail mapping, which is enough to retain the frequent conceptual core.",
        f"- `{recommendation.candidate_partner5_share_within:.2%}` of the candidate pool already has at least 5 distinct graph partners, which is a useful proxy for reusable graph participation.",
        "- It is strong enough to suppress many local labels that appear only in one journal or a small number of papers, without relying on brittle lexical heuristics alone.",
        "",
        "## Interpretation",
        "",
        "The support gate should be treated as the first filter, not the whole head definition. A later head score can still rank these candidates using graph reuse, lexical quality, and alias cohesion. But the support gate should do the coarse pruning first.",
        "",
        "## Next implication",
        "",
        "The next ontology iteration should:",
        "",
        "- use this support gate to form the head candidate set",
        "- then score that set using graph reuse and other quality signals",
        "- and only afterward decide the final head inventory",
        "",
        "This avoids the `v3` failure mode where a coverage rule alone promoted too much of the label universe into heads.",
        "",
    ]
    note_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_dir(DEFAULT_OUTPUT_ROOT)
    conn = sqlite3.connect(DEFAULT_DB)
    try:
        rows = fetch_base_rows(conn)
    finally:
        conn.close()
    grid, totals = compute_grid(rows)
    recommendation = choose_recommendation(grid)
    write_csv(grid, DEFAULT_OUTPUT_ROOT / "support_gate_grid.csv")
    write_json(grid, totals, recommendation, DEFAULT_OUTPUT_ROOT / "support_gate_grid.json")
    write_markdown(grid, totals, recommendation, DEFAULT_OUTPUT_ROOT / "support_gate_grid.md")
    write_note(grid, recommendation, DEFAULT_NOTE)


if __name__ == "__main__":
    main()
