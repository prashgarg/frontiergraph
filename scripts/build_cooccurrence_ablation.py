"""Co-occurrence ablation: does the directed causal graph add value over
simple undirected co-occurrence on the same benchmark?

This script reuses the cached historical feature panel from the benchmark
expansion pass and adds co-occurrence-only baselines.  The central question
is whether the directed claim structure (path support, motif counts,
mediator features, gap/boundary flags) buys screening value beyond what
raw co-occurrence frequency and co-occurrence-weighted popularity deliver.

Baselines added:
  cooc_count       – raw paper co-mention count (undirected)
  cooc_jaccard     – Jaccard-style neighbourhood overlap using support degrees
  cooc_pref_attach – co-occurrence count × support degree product
                     (popularity-weighted co-occurrence)

Compared against the existing benchmark family:
  graph_score, pref_attach, degree_recency, directed_closure
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.ranking_utils import evaluate_binary_ranking

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PANEL_CACHE = ROOT / "outputs/paper/37_benchmark_expansion/historical_feature_panel.parquet"
CONCEPTS_CSV = ROOT / "site/public/data/v2/central_concepts.csv"
OUT_DIR = ROOT / "outputs/paper/45_cooccurrence_ablation"
NOTE_PATH = ROOT / "next_steps/cooccurrence_ablation_note.md"

K_VALUES = [50, 100, 500, 1000]

STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "with",
}


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)


def _tokenize_label(value: str) -> tuple[str, ...]:
    text = str(value or "").lower()
    text = re.sub(r"\s*\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    tokens = [tok for tok in text.split() if tok and tok not in STOPWORDS]
    return tuple(tokens)


def _jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    d = len(sa | sb)
    return float(len(sa & sb) / d) if d else 0.0


def _containment(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return float(len(sa & sb) / min(len(sa), len(sb)))


# --------------------------------------------------------------------------- #
# Label map
# --------------------------------------------------------------------------- #
def _load_label_map(panel_df: pd.DataFrame) -> dict[str, str]:
    label_map: dict[str, str] = {}
    p = Path(CONCEPTS_CSV)
    if p.exists():
        df = pd.read_csv(p, usecols=["concept_id", "plain_label"])
        for row in df.drop_duplicates("concept_id").itertuples(index=False):
            label_map[str(row.concept_id)] = str(row.plain_label)
    return label_map


# --------------------------------------------------------------------------- #
# Score construction
# --------------------------------------------------------------------------- #
def _add_scores(panel_df: pd.DataFrame, label_map: dict[str, str]) -> pd.DataFrame:
    out = panel_df.copy()

    # Only keep the pool rows
    pool_col = [c for c in out.columns if c.startswith("in_pool_")]
    if pool_col:
        out = out[out[pool_col[0]].astype(bool)].copy()

    # ---- existing baselines (reproduced from benchmark expansion) ----
    support_degree = _safe_numeric(out["support_degree_product"])
    recent_degree = (
        (_safe_numeric(out["source_recent_support_out_degree"]) + 1.0)
        * (_safe_numeric(out["target_recent_support_in_degree"]) + 1.0)
    )
    closure_core = (
        np.log1p(_safe_numeric(out["path_support_raw"]))
        + 0.5 * np.log1p(_safe_numeric(out["mediator_count"]))
        + 0.5 * _safe_numeric(out["nearby_closure_density"])
    )

    out["graph_score"] = _safe_numeric(
        out["transparent_score"] if "transparent_score" in out.columns else out["score"]
    )
    out["pref_attach_score"] = support_degree
    out["degree_recency_score"] = np.log1p(support_degree) + 0.5 * np.log1p(recent_degree)
    out["directed_closure_score"] = closure_core

    # Lexical similarity
    out["u_label"] = out["u"].astype(str).map(label_map).fillna(out["u"].astype(str))
    out["v_label"] = out["v"].astype(str).map(label_map).fillna(out["v"].astype(str))
    token_map = {code: _tokenize_label(lab) for code, lab in label_map.items()}
    out["u_tokens"] = out["u"].astype(str).map(token_map).apply(lambda x: x if isinstance(x, tuple) else ())
    out["v_tokens"] = out["v"].astype(str).map(token_map).apply(lambda x: x if isinstance(x, tuple) else ())
    out["lexical_similarity_score"] = [
        _jaccard(a, b) + 0.25 * _containment(a, b)
        for a, b in zip(out["u_tokens"].tolist(), out["v_tokens"].tolist())
    ]

    # ---- NEW: co-occurrence baselines ----
    cooc = _safe_numeric(out["cooc_count"])
    src_out = _safe_numeric(out["source_support_out_degree"])
    tgt_in = _safe_numeric(out["target_support_in_degree"])

    # 1. Raw co-occurrence count
    out["cooc_count_score"] = cooc

    # 2. Co-occurrence Jaccard: cooc / (src_out + tgt_in - cooc)
    #    Neighbourhood overlap proxy: if two nodes share many co-occurrence
    #    partners relative to their combined connectivity, they score higher.
    denom = (src_out + tgt_in - cooc).clip(lower=1.0)
    out["cooc_jaccard_score"] = cooc / denom

    # 3. Co-occurrence × preferential attachment
    #    Popularity-weighted co-occurrence: rewards pairs that co-occur
    #    AND whose endpoints are popular.
    out["cooc_pref_attach_score"] = cooc * np.log1p(support_degree)

    return out


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
MODEL_COLS = {
    # existing baselines
    "graph_score": "graph_score",
    "pref_attach": "pref_attach_score",
    "degree_recency": "degree_recency_score",
    "directed_closure": "directed_closure_score",
    "lexical_similarity": "lexical_similarity_score",
    # new co-occurrence baselines
    "cooc_count": "cooc_count_score",
    "cooc_jaccard": "cooc_jaccard_score",
    "cooc_pref_attach": "cooc_pref_attach_score",
}


def _evaluate(panel_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []

    for (cutoff_year_t, horizon), group in panel_df.groupby(
        ["cutoff_year_t", "horizon"], sort=True
    ):
        pos_df = group[group["appears_within_h"].astype(bool)]
        positives = {
            (str(r.u), str(r.v)) for r in pos_df[["u", "v"]].itertuples(index=False)
        }
        if not positives:
            continue

        ranking_maps: dict[str, pd.DataFrame] = {}
        for model_name, score_col in MODEL_COLS.items():
            ranked = (
                group[["u", "v", score_col]]
                .rename(columns={score_col: "score"})
                .sort_values(["score", "u", "v"], ascending=[False, True, True])
                .reset_index(drop=True)
            )
            ranked["rank"] = ranked.index + 1
            ranking_maps[model_name] = ranked
            metrics = evaluate_binary_ranking(
                ranked[["u", "v", "score", "rank"]], positives=positives, k_values=K_VALUES
            )
            row: dict[str, Any] = {
                "model": model_name,
                "cutoff_year_t": int(cutoff_year_t),
                "horizon": int(horizon),
                "n_eval_rows": int(len(group)),
                "n_positives": int(len(positives)),
                "mrr": float(metrics.get("mrr", 0.0)),
            }
            for k in K_VALUES:
                row[f"hits_at_{k}"] = int(metrics.get(f"hits_at_{k}", 0))
                row[f"precision_at_{k}"] = float(metrics.get(f"precision_at_{k}", 0.0))
                row[f"recall_at_{k}"] = float(metrics.get(f"recall_at_{k}", 0.0))
            metric_rows.append(row)

        # Top-100 overlap between graph_score and each other model
        graph_top = {
            (str(r.u), str(r.v))
            for r in ranking_maps["graph_score"].head(100)[["u", "v"]].itertuples(index=False)
        }
        for model_name, ranked in ranking_maps.items():
            if model_name == "graph_score":
                continue
            other_top = {
                (str(r.u), str(r.v)) for r in ranked.head(100)[["u", "v"]].itertuples(index=False)
            }
            inter = graph_top & other_top
            union = graph_top | other_top
            overlap_rows.append({
                "model": model_name,
                "cutoff_year_t": int(cutoff_year_t),
                "horizon": int(horizon),
                "top_100_overlap": int(len(inter)),
                "top_100_jaccard": float(len(inter) / len(union)) if union else 0.0,
            })

    return pd.DataFrame(metric_rows), pd.DataFrame(overlap_rows)


def _summarize(metric_df: pd.DataFrame) -> pd.DataFrame:
    agg_dict: dict[str, tuple[str, str]] = {
        "mean_mrr": ("mrr", "mean"),
    }
    for k in K_VALUES:
        agg_dict[f"mean_precision_at_{k}"] = (f"precision_at_{k}", "mean")
        agg_dict[f"mean_recall_at_{k}"] = (f"recall_at_{k}", "mean")
        agg_dict[f"mean_hits_at_{k}"] = (f"hits_at_{k}", "mean")
    agg_dict["n_cutoffs"] = ("cutoff_year_t", "nunique")

    summary = (
        metric_df.groupby(["model", "horizon"], as_index=False)
        .agg(**agg_dict)
        .sort_values(["horizon", "mean_precision_at_100", "mean_mrr"], ascending=[True, False, False])
    )
    return summary


# --------------------------------------------------------------------------- #
# Markdown note
# --------------------------------------------------------------------------- #
def _write_note(summary_df: pd.DataFrame, note_path: Path) -> None:
    lines = [
        "# Co-occurrence Ablation Note",
        "",
        "## Question",
        "",
        "Does the directed causal claim graph add screening value over simple undirected co-occurrence?",
        "",
        "## Baselines",
        "",
        "- `cooc_count`: raw paper co-mention count (undirected, ignores direction and edge type)",
        "- `cooc_jaccard`: neighbourhood overlap proxy (cooc / (src_degree + tgt_degree - cooc))",
        "- `cooc_pref_attach`: co-occurrence weighted by log popularity (cooc * log1p(degree product))",
        "",
        "## Results",
        "",
    ]

    cooc_models = {"cooc_count", "cooc_jaccard", "cooc_pref_attach"}
    directed_models = {"graph_score", "directed_closure"}

    for horizon in sorted(summary_df["horizon"].unique()):
        block = summary_df[summary_df["horizon"] == horizon].copy()
        lines.append(f"### Horizon {int(horizon)}")
        lines.append("")
        lines.append("| Model | Precision@100 | Recall@100 | MRR | Hits@100 |")
        lines.append("|-------|--------------|-----------|-----|----------|")
        for row in block.itertuples(index=False):
            tag = ""
            if row.model in cooc_models:
                tag = " *"
            lines.append(
                f"| {row.model}{tag} | {row.mean_precision_at_100:.6f} "
                f"| {row.mean_recall_at_100:.6f} | {row.mean_mrr:.6f} "
                f"| {row.mean_hits_at_100:.1f} |"
            )
        lines.append("")

        # Interpretive summary
        graph_row = block[block["model"] == "graph_score"]
        best_cooc = block[block["model"].isin(cooc_models)].sort_values(
            "mean_precision_at_100", ascending=False
        )
        if not graph_row.empty and not best_cooc.empty:
            gp = float(graph_row["mean_precision_at_100"].iloc[0])
            cp = float(best_cooc["mean_precision_at_100"].iloc[0])
            cn = best_cooc["model"].iloc[0]
            if gp > cp:
                delta_pct = ((gp - cp) / cp) * 100 if cp > 0 else float("inf")
                lines.append(
                    f"Graph score beats best co-occurrence baseline (`{cn}`) "
                    f"on precision@100 by {delta_pct:.1f}%."
                )
            else:
                delta_pct = ((cp - gp) / gp) * 100 if gp > 0 else float("inf")
                lines.append(
                    f"Best co-occurrence baseline (`{cn}`) beats graph score "
                    f"on precision@100 by {delta_pct:.1f}%."
                )
        lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        "If the co-occurrence baselines perform similarly to the graph score, the directed causal",
        "structure is not buying much beyond what raw paper co-mentions deliver. If the graph score",
        "substantially outperforms co-occurrence, the directed claim structure justifies the harder",
        "extraction. If co-occurrence baselines are even weaker than preferential attachment, that",
        "confirms co-occurrence alone is a poor screen for future link appearance.",
        "",
        "## Connection to Impact4Cast (Gu and Krenn 2025)",
        "",
        "Gu and Krenn use undirected co-occurrence edges in a concept graph across all sciences.",
        "This ablation tests the co-occurrence approach on our economics-specific directed claim",
        "graph. If directed claims outperform co-occurrence here, it provides direct evidence that",
        "the richer extraction is worthwhile in this domain.",
    ])
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    print(f"Loading panel from {PANEL_CACHE} ...")
    if not PANEL_CACHE.exists():
        print(f"ERROR: Panel cache not found at {PANEL_CACHE}. Run build_benchmark_expansion_review.py first.")
        sys.exit(1)

    panel_df = pd.read_parquet(PANEL_CACHE)
    print(f"  Panel rows: {len(panel_df):,}")
    print(f"  Cutoff years: {sorted(panel_df['cutoff_year_t'].dropna().astype(int).unique().tolist())}")
    print(f"  Horizons: {sorted(panel_df['horizon'].dropna().astype(int).unique().tolist())}")

    label_map = _load_label_map(panel_df)
    panel_df = _add_scores(panel_df, label_map)
    print(f"  Panel rows after pool filter: {len(panel_df):,}")

    print("Evaluating models ...")
    metric_df, overlap_df = _evaluate(panel_df)
    summary_df = _summarize(metric_df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metric_df.to_csv(OUT_DIR / "cooccurrence_ablation_panel.csv", index=False)
    summary_df.to_csv(OUT_DIR / "cooccurrence_ablation_summary.csv", index=False)
    if not overlap_df.empty:
        overlap_df.to_csv(OUT_DIR / "cooccurrence_ablation_overlap.csv", index=False)

    payload = {
        "panel_rows": int(len(panel_df)),
        "models": sorted(metric_df["model"].unique().tolist()),
        "mean_precision_at_100": {
            f"{r.model}__h{int(r.horizon)}": float(r.mean_precision_at_100)
            for r in summary_df.itertuples(index=False)
        },
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    _write_note(summary_df, NOTE_PATH)

    print("\n=== SUMMARY ===\n")
    for horizon in sorted(summary_df["horizon"].unique()):
        print(f"--- h={int(horizon)} ---")
        block = summary_df[summary_df["horizon"] == horizon]
        for r in block.itertuples(index=False):
            print(
                f"  {r.model:25s}  P@100={r.mean_precision_at_100:.6f}  "
                f"R@100={r.mean_recall_at_100:.6f}  MRR={r.mean_mrr:.6f}  "
                f"Hits@100={r.mean_hits_at_100:.1f}"
            )
        print()

    print(f"Outputs written to {OUT_DIR}")
    print(f"Note written to {NOTE_PATH}")


if __name__ == "__main__":
    main()
