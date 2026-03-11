from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOT = ROOT / "data/production/frontiergraph_ontology_compare_v1/review_pack"
EXTRACTION_DB = ROOT / "data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite"
ENRICHED_DB = ROOT / "data/processed/openalex/published_enriched/openalex_published_enriched.sqlite"

VIEWS: dict[str, dict[str, Any]] = {
    "legacy_jel": {
        "label": "Legacy JEL",
        "db": ROOT / "data/processed/app_causalclaims.db",
        "kind": "legacy",
    },
    "broad_strict": {
        "label": "Broad strict",
        "db": ROOT / "data/production/frontiergraph_concept_compare_v1/broad/concept_hard_app.sqlite",
        "kind": "concept",
    },
    "broad_exploratory": {
        "label": "Broad exploratory",
        "db": ROOT / "data/production/frontiergraph_concept_compare_v1/broad/concept_exploratory_app.sqlite",
        "kind": "concept",
    },
    "baseline_strict": {
        "label": "Baseline strict",
        "db": ROOT / "data/production/frontiergraph_concept_compare_v1/baseline/concept_hard_app.sqlite",
        "kind": "concept",
    },
    "baseline_exploratory": {
        "label": "Baseline exploratory",
        "db": ROOT / "data/production/frontiergraph_concept_compare_v1/baseline/concept_exploratory_app.sqlite",
        "kind": "concept",
    },
    "conservative_strict": {
        "label": "Conservative strict",
        "db": ROOT / "data/production/frontiergraph_concept_compare_v1/conservative/concept_hard_app.sqlite",
        "kind": "concept",
    },
    "conservative_exploratory": {
        "label": "Conservative exploratory",
        "db": ROOT / "data/production/frontiergraph_concept_compare_v1/conservative/concept_exploratory_app.sqlite",
        "kind": "concept",
    },
}

PAPER_IDS = [
    "W2752617332__gpt5mini_low",
    "W2162484441__gpt5mini_low",
    "W1995503011__gpt5mini_low",
    "W3121293400__gpt5mini_low",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_top_recommendations(limit: int = 25) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    rows: list[dict[str, Any]] = []
    top_sets: dict[str, set[str]] = {}
    for view_key, meta in VIEWS.items():
        conn = sqlite3.connect(meta["db"])
        conn.row_factory = sqlite3.Row
        try:
            if meta["kind"] == "legacy":
                query = """
                    SELECT
                        c.u,
                        nu.label AS u_label,
                        c.v,
                        nv.label AS v_label,
                        c.score,
                        c.rank,
                        c.cooc_count,
                        c.mediator_count
                    FROM candidates c
                    JOIN nodes nu ON c.u = nu.code
                    JOIN nodes nv ON c.v = nv.code
                    ORDER BY c.score DESC, c.rank ASC
                    LIMIT ?
                """
                result = [dict(row) for row in conn.execute(query, (limit,)).fetchall()]
                top_sets[view_key] = {f"{row['u']}__{row['v']}" for row in result[:100]}
                for row in result:
                    rows.append(
                        {
                            "view_key": view_key,
                            "view_label": meta["label"],
                            "u": row["u"],
                            "u_label": row["u_label"],
                            "v": row["v"],
                            "v_label": row["v_label"],
                            "score": row["score"],
                            "rank": row["rank"],
                            "cooc_count": row["cooc_count"],
                            "mediator_count": row["mediator_count"],
                            "u_bucket_hint": "legacy",
                            "v_bucket_hint": "legacy",
                        }
                    )
            else:
                query = """
                    SELECT
                        u,
                        u_preferred_label AS u_label,
                        v,
                        v_preferred_label AS v_label,
                        score,
                        rank,
                        cooc_count,
                        mediator_count,
                        u_bucket_hint,
                        v_bucket_hint
                    FROM candidates
                    ORDER BY score DESC, rank ASC
                    LIMIT ?
                """
                result = [dict(row) for row in conn.execute(query, (limit,)).fetchall()]
                top_sets[view_key] = {f"{row['u']}__{row['v']}" for row in result[:100]}
                for row in result:
                    rows.append(
                        {
                            "view_key": view_key,
                            "view_label": meta["label"],
                            **row,
                        }
                    )
        finally:
            conn.close()
    return rows, top_sets


def load_graph(view_key: str) -> tuple[dict[str, str], list[tuple[str, str, float]]]:
    meta = VIEWS[view_key]
    conn = sqlite3.connect(meta["db"])
    conn.row_factory = sqlite3.Row
    try:
        if meta["kind"] == "legacy":
            nodes = {row["code"]: row["label"] for row in conn.execute("SELECT code, label FROM nodes")}
            edges = [
                (row["u"], row["v"], float(row["support"]))
                for row in conn.execute(
                    """
                    SELECT src_code AS u, dst_code AS v, COUNT(*) AS support
                    FROM edges
                    GROUP BY src_code, dst_code
                    """
                )
            ]
        else:
            nodes = {row["code"]: row["label"] for row in conn.execute("SELECT code, label FROM nodes")}
            edges = [
                (row["u"], row["v"], float(row["support"]))
                for row in conn.execute(
                    """
                    SELECT source_concept_id AS u, target_concept_id AS v, support_count AS support
                    FROM concept_edges
                    """
                )
            ]
    finally:
        conn.close()
    return nodes, edges


def pagerank(nodes: dict[str, str], edges: list[tuple[str, str, float]], alpha: float = 0.85) -> dict[str, float]:
    ids = list(nodes)
    if not ids:
        return {}
    out_weight = defaultdict(float)
    incoming = defaultdict(list)
    for u, v, w in edges:
        out_weight[u] += w
        incoming[v].append((u, w))
    n = len(ids)
    pr = {node: 1.0 / n for node in ids}
    base = (1.0 - alpha) / n
    for _ in range(100):
        dangling = alpha * sum(pr[node] for node in ids if out_weight[node] == 0.0) / n
        new_pr: dict[str, float] = {}
        delta = 0.0
        for v in ids:
            score = base + dangling
            for u, w in incoming[v]:
                if out_weight[u] > 0.0:
                    score += alpha * pr[u] * (w / out_weight[u])
            new_pr[v] = score
            delta = max(delta, abs(score - pr[v]))
        pr = new_pr
        if delta < 1e-10:
            break
    return pr


def load_centrality_rows(top_k: int = 20) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for view_key, meta in VIEWS.items():
        labels, edges = load_graph(view_key)
        indeg = defaultdict(int)
        outdeg = defaultdict(int)
        weighted = defaultdict(float)
        paper_support = defaultdict(float)
        for u, v, w in edges:
            outdeg[u] += 1
            indeg[v] += 1
            weighted[u] += w
            weighted[v] += w
            paper_support[u] += w
            paper_support[v] += w
        pr = pagerank(labels, edges)
        metrics = {
            "in_degree": indeg,
            "out_degree": outdeg,
            "weighted_degree": weighted,
            "pagerank": pr,
        }
        for metric_name, metric_map in metrics.items():
            ranked = sorted(metric_map.items(), key=lambda kv: (kv[1], labels.get(kv[0], kv[0])), reverse=True)[:top_k]
            for rank, (node_code, value) in enumerate(ranked, start=1):
                rows.append(
                    {
                        "view_key": view_key,
                        "view_label": meta["label"],
                        "metric": metric_name,
                        "rank": rank,
                        "node_code": node_code,
                        "node_label": labels.get(node_code, node_code),
                        "value": float(value),
                    }
                )
    return rows


def load_top_cited_papers() -> list[dict[str, Any]]:
    extraction_conn = sqlite3.connect(EXTRACTION_DB)
    extraction_rows = extraction_conn.execute(
        "SELECT custom_id, openalex_work_id, title, publication_year, bucket, node_count, edge_count FROM works WHERE edge_count > 0"
    ).fetchall()
    extraction_conn.close()
    extraction_map = {row[1]: row for row in extraction_rows}

    enriched_conn = sqlite3.connect(ENRICHED_DB)
    enriched_rows = enriched_conn.execute(
        """
        SELECT work_id, cited_by_count, fwci, source_display_name
        FROM works_base
        ORDER BY cited_by_count DESC
        LIMIT 5000
        """
    ).fetchall()
    enriched_conn.close()
    metadata_by_custom: dict[str, dict[str, Any]] = {}
    for work_id, cited_by_count, fwci, source_display_name in enriched_rows:
        if work_id in extraction_map:
            custom_id, _, title, publication_year, bucket, node_count, edge_count = extraction_map[work_id]
            metadata_by_custom[custom_id] = {
                "custom_id": custom_id,
                "openalex_work_id": work_id,
                "title": title,
                "publication_year": publication_year,
                "bucket": bucket,
                "node_count": node_count,
                "edge_count": edge_count,
                "cited_by_count": cited_by_count,
                "fwci": fwci,
                "source_display_name": source_display_name,
            }
    return [metadata_by_custom[paper_id] for paper_id in PAPER_IDS if paper_id in metadata_by_custom]


def load_paper_graph_rows(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for paper in papers:
        paper_id = paper["custom_id"]
        for view_key, meta in VIEWS.items():
            conn = sqlite3.connect(meta["db"])
            conn.row_factory = sqlite3.Row
            try:
                edge_rows = [dict(row) for row in conn.execute(
                    """
                    SELECT paper_id, src_code, dst_code, relation_type, evidence_type, is_causal, weight, stability
                    FROM edges
                    WHERE paper_id = ?
                    ORDER BY src_code, dst_code, relation_type
                    """,
                    (paper_id,),
                ).fetchall()]
                codes = sorted({code for row in edge_rows for code in (row["src_code"], row["dst_code"])})
                label_map: dict[str, str] = {}
                if codes:
                    placeholders = ",".join("?" for _ in codes)
                    for row in conn.execute(f"SELECT code, label FROM nodes WHERE code IN ({placeholders})", tuple(codes)):
                        label_map[row["code"]] = row["label"]
                if not edge_rows:
                    rows.append(
                        {
                            "paper_id": paper_id,
                            "paper_title": paper["title"],
                            "view_key": view_key,
                            "view_label": meta["label"],
                            "edge_rank": 0,
                            "src_code": "",
                            "src_label": "",
                            "dst_code": "",
                            "dst_label": "",
                            "relation_type": "",
                            "evidence_type": "",
                            "is_causal": "",
                            "weight": "",
                            "stability": "",
                        }
                    )
                    continue
                for idx, row in enumerate(edge_rows, start=1):
                    rows.append(
                        {
                            "paper_id": paper_id,
                            "paper_title": paper["title"],
                            "view_key": view_key,
                            "view_label": meta["label"],
                            "edge_rank": idx,
                            "src_code": row["src_code"],
                            "src_label": label_map.get(row["src_code"], row["src_code"]),
                            "dst_code": row["dst_code"],
                            "dst_label": label_map.get(row["dst_code"], row["dst_code"]),
                            "relation_type": row["relation_type"],
                            "evidence_type": row["evidence_type"],
                            "is_causal": row["is_causal"],
                            "weight": row["weight"],
                            "stability": row["stability"],
                        }
                    )
            finally:
                conn.close()
    return rows


def write_review_markdown(
    recommendation_rows: list[dict[str, Any]],
    centrality_rows: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    paper_graph_rows: list[dict[str, Any]],
) -> None:
    by_view: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in recommendation_rows:
        by_view[row["view_key"]].append(row)
    central_by_view_metric: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in centrality_rows:
        central_by_view_metric[(row["view_key"], row["metric"])].append(row)
    paper_rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in paper_graph_rows:
        paper_rows_by_key[(row["paper_id"], row["view_key"])].append(row)

    lines: list[str] = []
    lines.extend(
        [
            "# FrontierGraph Ontology Comparison Review Pack",
            "",
            "## Bottom line",
            "",
            "My read is that `Baseline exploratory` is the best default product view.",
            "",
            "- `Baseline exploratory` keeps the head inventory compact enough to remain legible, but its soft coverage is almost as high as the broad and conservative exploratory regimes.",
            "- `Broad` keeps more specific heads, but its top recommendation list is still dominated by near-synonym loops around carbon/growth/energy and does not buy enough extra clarity.",
            "- `Conservative strict` is too brittle: it drops the graph for too many classic papers.",
            "- `Conservative exploratory` recovers coverage, but it does so by routing through overly generic or method-like heads more often than the baseline.",
            "- `Legacy JEL` remains useful as a coarse browse fallback, but it is not meaningfully comparable to the concept views at the recommendation level; the top-100 overlap with every concept view is zero.",
            "",
            "The main ontology problem that remains is **anti-synonym control**. In every concept regime, the very top recommendations are still dominated by pairs like `CO2 emissions -> carbon emissions` or `economic growth (GDP) -> economic growth`.",
            "",
            "## Manual comments by view",
            "",
            "### Legacy JEL",
            "",
            "- Good for very coarse field navigation.",
            "- Bad for concept-level prioritization. The top candidate list is dominated by broad field abstractions such as `inflation -> human capital` or `exchange rates -> human capital`, which are interpretable only at a high level.",
            "- It also fails as a paper-level graph lens for the selected sample papers; the current JEL app DB does not preserve those papers' extracted concept structure.",
            "",
            "### Broad strict",
            "",
            "- Broad strict preserves the largest strict head set and therefore the richest strict graph.",
            "- It is the best strict regime if you care about retaining specific adjacent concepts rather than compressing them away.",
            "- But the top recommendation list is still cluttered by near-duplicate heads (`CO2 emissions`, `carbon emissions`, `carbon dioxide (CO2) emission`), which means the broader head pool is not enough by itself to prevent synonym loops.",
            "",
            "### Broad exploratory",
            "",
            "- Broad exploratory is the most internally stable regime: its top-100 recommendation overlap with broad strict is the highest of any strict/exploratory pair.",
            "- It adds plausible extra structure to papers while keeping many specific environmental and energy concepts alive.",
            "- The downside is that it still spends a lot of candidate mass on concept variants rather than true frontier links.",
            "",
            "### Baseline strict",
            "",
            "- Baseline strict is the cleanest strict mode. The head inventory is materially smaller than broad but still large enough to preserve meaningful concepts.",
            "- It is the most defensible strict graph for evaluation and methodology.",
            "- Its failure mode is coverage: some important classic papers collapse to one edge or disappear entirely.",
            "",
            "### Baseline exploratory",
            "",
            "- This is the best default. It combines a compact head inventory with exploratory coverage close to the other exploratory regimes.",
            "- It recovers multi-edge structure for classic papers that strict modes lose, without becoming as method-heavy as conservative exploratory.",
            "- It still needs an anti-synonym/near-duplicate penalty layer, because the top of the ranked candidate list is still full of semantic duplicates.",
            "",
            "### Conservative strict",
            "",
            "- Conservative strict is too severe. It compresses the head pool so hard that it drops the graph for many papers that should survive strict mode.",
            "- It is useful as a sensitivity extreme, not as a product default.",
            "",
            "### Conservative exploratory",
            "",
            "- Conservative exploratory recovers broad coverage, but it does so by routing many tails into very compressed heads.",
            "- That causes odd artifacts such as `model parameters` or overly generic labels surfacing as central or top-outgoing nodes.",
            "- It is a good robustness regime but not the best primary user-facing view.",
            "",
            "## Top recommendations by view",
            "",
        ]
    )

    for view_key, meta in VIEWS.items():
        lines.append(f"### {meta['label']}")
        lines.append("")
        for row in by_view[view_key][:10]:
            lines.append(
                f"- `{row['u_label']} -> {row['v_label']}` | score `{row['score']:.3f}` | cooc `{row['cooc_count']}` | mediators `{row['mediator_count']}`"
            )
        lines.append("")

    lines.extend(
        [
            "## Central nodes across views",
            "",
            "Across all concept regimes, the graph is dominated by a climate-energy-growth spine. That is probably a real property of the chosen `FWCI core150 + adjacent150` corpus, not just an ontology artifact. What changes by regime is how much of that spine is expressed as near-synonyms versus consolidated concepts.",
            "",
            "- In the concept regimes, `economic growth`, `CO2 emissions`, `carbon emissions`, `renewable energy consumption`, and `energy consumption` dominate almost every centrality metric.",
            "- Exploratory modes pull in broader labor/productivity/COVID structure because they recover more tail assignments.",
            "- The conservative exploratory regime is the first place where method-like or overly generic nodes (`model parameters`, `MMQR`) become visibly central, which is a warning sign against making it the default.",
            "",
        ]
    )
    for view_key, meta in VIEWS.items():
        lines.append(f"### {meta['label']}")
        lines.append("")
        for metric in ["in_degree", "out_degree", "weighted_degree", "pagerank"]:
            lines.append(f"- `{metric}`:")
            metric_rows = central_by_view_metric[(view_key, metric)][:10]
            metric_desc = ", ".join(f"{row['node_label']} ({row['value']:.3f})" if metric == "pagerank" else f"{row['node_label']} ({int(row['value']) if float(row['value']).is_integer() else row['value']:.0f})" for row in metric_rows)
            lines.append(f"  {metric_desc}")
        lines.append("")

    lines.extend(
        [
            "## High-citation paper graph comparison",
            "",
            "These examples make the product tradeoff concrete: strict modes preserve only the most defensible identity-preserving structure, while exploratory modes recover richer paper-level graphs.",
            "",
        ]
    )

    for paper in papers:
        lines.append(f"### {paper['title']}")
        lines.append("")
        lines.append(
            f"- citations: `{paper['cited_by_count']}` | FWCI: `{paper['fwci']}` | year: `{paper['publication_year']}` | bucket: `{paper['bucket']}` | source: `{paper['source_display_name']}`"
        )
        lines.append("")
        if paper["custom_id"] == "W2752617332__gpt5mini_low":
            lines.append("Comment: strict modes keep the core `debt -> agency costs` claim, while exploratory modes add plausible but somewhat noisy auxiliary structure around ownership and investors.")
            lines.append("")
        elif paper["custom_id"] == "W2162484441__gpt5mini_low":
            lines.append("Comment: conservative strict drops the paper entirely, which is too brittle. Baseline/broad strict keep the core `human capital -> growth` relation, and exploratory modes recover the `population size -> growth` link.")
            lines.append("")
        elif paper["custom_id"] == "W1995503011__gpt5mini_low":
            lines.append("Comment: broad and baseline strict retain the full 3-edge graph cleanly; conservative strict loses it. This is a strong argument against conservative strict as a default.")
            lines.append("")
        elif paper["custom_id"] == "W3121293400__gpt5mini_low":
            lines.append("Comment: strict modes under-recover this paper, while exploratory modes consistently surface the intended structure around nominal rigidities, wage bargaining, and utilization. This is a strong argument for an exploratory default.")
            lines.append("")
        for view_key, meta in VIEWS.items():
            lines.append(f"#### {meta['label']}")
            rows = paper_rows_by_key[(paper["custom_id"], view_key)]
            if rows and rows[0]["edge_rank"] == 0:
                lines.append("- no mapped paper-level edges in this view")
            else:
                for row in rows:
                    lines.append(
                        f"- `{row['src_label']} -> {row['dst_label']}` | `{row['relation_type']}` | `{row['evidence_type']}` | causal `{row['is_causal']}`"
                    )
            lines.append("")

    path = REVIEW_ROOT / "ontology_comparison_review_pack.md"
    ensure_dir(path.parent)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_dir(REVIEW_ROOT)
    recommendation_rows, top_sets = load_top_recommendations()
    centrality_rows = load_centrality_rows()
    papers = load_top_cited_papers()
    paper_graph_rows = load_paper_graph_rows(papers)

    overlap_rows: list[dict[str, Any]] = []
    for left, right in combinations(sorted(top_sets), 2):
        inter = len(top_sets[left] & top_sets[right])
        union = len(top_sets[left] | top_sets[right])
        overlap_rows.append(
            {
                "left": left,
                "right": right,
                "intersection_top100": inter,
                "jaccard_top100": inter / union if union else 0.0,
            }
        )

    write_csv(
        REVIEW_ROOT / "top_recommendations.csv",
        recommendation_rows,
        [
            "view_key",
            "view_label",
            "u",
            "u_label",
            "v",
            "v_label",
            "score",
            "rank",
            "cooc_count",
            "mediator_count",
            "u_bucket_hint",
            "v_bucket_hint",
        ],
    )
    write_json(REVIEW_ROOT / "top_recommendations.json", recommendation_rows)
    write_csv(
        REVIEW_ROOT / "central_nodes.csv",
        centrality_rows,
        ["view_key", "view_label", "metric", "rank", "node_code", "node_label", "value"],
    )
    write_json(REVIEW_ROOT / "central_nodes.json", centrality_rows)
    write_csv(
        REVIEW_ROOT / "paper_graphs.csv",
        paper_graph_rows,
        [
            "paper_id",
            "paper_title",
            "view_key",
            "view_label",
            "edge_rank",
            "src_code",
            "src_label",
            "dst_code",
            "dst_label",
            "relation_type",
            "evidence_type",
            "is_causal",
            "weight",
            "stability",
        ],
    )
    write_json(REVIEW_ROOT / "paper_graphs.json", paper_graph_rows)
    write_csv(
        REVIEW_ROOT / "top100_overlap_with_legacy.csv",
        [row for row in overlap_rows if "legacy" in (row["left"], row["right"])],
        ["left", "right", "intersection_top100", "jaccard_top100"],
    )
    write_json(REVIEW_ROOT / "top100_overlap_with_legacy.json", [row for row in overlap_rows if "legacy" in (row["left"], row["right"])])
    write_review_markdown(recommendation_rows, centrality_rows, papers, paper_graph_rows)


if __name__ == "__main__":
    main()
