from __future__ import annotations

import argparse
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

from src.analysis.learned_reranker import build_candidate_feature_panel
from src.analysis.ranking_utils import candidate_cfg_from_config, evaluate_binary_ranking
from src.analysis.common import ensure_output_dir
from src.utils import load_config, load_corpus


STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand the paper benchmark with stronger transparent baselines.")
    parser.add_argument("--corpus", default="data/processed/research_allocation_v2/hybrid_corpus.parquet", dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best-config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--paper-meta", default="data/processed/research_allocation_v2/hybrid_papers_funding.parquet", dest="paper_meta_path")
    parser.add_argument("--cutoff-years", default="1990,1995,2000,2005,2010,2015", dest="cutoff_years")
    parser.add_argument("--horizons", default="5,10", dest="horizons")
    parser.add_argument("--pool-size", type=int, default=10000, dest="pool_size")
    parser.add_argument("--k-values", default="50,100,500,1000", dest="k_values")
    parser.add_argument("--panel-cache", default="outputs/paper/37_benchmark_expansion/historical_feature_panel.parquet", dest="panel_cache")
    parser.add_argument("--concepts-csv", default="site/public/data/v2/central_concepts.csv", dest="concepts_csv")
    parser.add_argument("--out", default="outputs/paper/37_benchmark_expansion", dest="out_dir")
    parser.add_argument("--note", default="next_steps/benchmark_expansion_note.md", dest="note_path")
    return parser.parse_args()


def _parse_int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in str(raw).split(",") if x.strip()]


def _load_label_map(corpus_df: pd.DataFrame, concepts_csv: str | Path) -> dict[str, str]:
    label_map: dict[str, str] = {}
    for left, right in [("src_code", "src_label"), ("dst_code", "dst_label")]:
        if left in corpus_df.columns and right in corpus_df.columns:
            tmp = corpus_df[[left, right]].drop_duplicates()
            for row in tmp.itertuples(index=False):
                code = str(getattr(row, left))
                label = str(getattr(row, right))
                if code and label and code not in label_map:
                    label_map[code] = label

    concepts_path = Path(concepts_csv)
    if concepts_path.exists():
        concepts_df = pd.read_csv(concepts_path, usecols=["concept_id", "plain_label"])
        for row in concepts_df.drop_duplicates("concept_id").itertuples(index=False):
            label_map.setdefault(str(row.concept_id), str(row.plain_label))
    return label_map


def _tokenize_label(value: str) -> tuple[str, ...]:
    text = str(value or "").lower()
    text = re.sub(r"\s*\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    tokens = [tok for tok in text.split() if tok and tok not in STOPWORDS]
    return tuple(tokens)


def _jaccard(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 0.0
    denom = len(left_set | right_set)
    return float(len(left_set & right_set) / denom) if denom else 0.0


def _containment(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return float(len(left_set & right_set) / min(len(left_set), len(right_set)))


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)


def _build_or_load_panel(args: argparse.Namespace) -> pd.DataFrame:
    panel_path = Path(args.panel_cache)
    if panel_path.exists():
        return pd.read_parquet(panel_path)

    out_dir = ensure_output_dir(Path(args.out_dir))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_df = load_corpus(args.corpus_path)
    config = load_config(args.config_path)
    cfg = candidate_cfg_from_config(config, best_config_path=args.best_config_path)
    paper_meta_path = Path(args.paper_meta_path)
    paper_meta_df = pd.read_parquet(paper_meta_path) if paper_meta_path.exists() else None

    panel_df = build_candidate_feature_panel(
        corpus_df=corpus_df,
        cfg=cfg,
        cutoff_years=_parse_int_list(args.cutoff_years),
        horizons=_parse_int_list(args.horizons),
        pool_sizes=[int(args.pool_size)],
        paper_meta_df=paper_meta_df,
    )
    panel_df.to_parquet(panel_path, index=False)
    panel_df.to_csv(out_dir / "historical_feature_panel.csv", index=False)
    return panel_df


def _add_baseline_scores(panel_df: pd.DataFrame, label_map: dict[str, str]) -> pd.DataFrame:
    out = panel_df.copy()
    pool_col = f"in_pool_{int(args.pool_size)}"  # type: ignore[name-defined]
    if pool_col in out.columns:
        out = out[out[pool_col].astype(bool)].copy()

    out["u_label"] = out["u"].astype(str).map(label_map).fillna(out["u"].astype(str))
    out["v_label"] = out["v"].astype(str).map(label_map).fillna(out["v"].astype(str))

    token_map = {code: _tokenize_label(label) for code, label in label_map.items()}
    out["u_tokens"] = out["u"].astype(str).map(token_map).apply(lambda x: x if isinstance(x, tuple) else tuple())
    out["v_tokens"] = out["v"].astype(str).map(token_map).apply(lambda x: x if isinstance(x, tuple) else tuple())
    out["lexical_jaccard"] = [
        _jaccard(left, right) for left, right in zip(out["u_tokens"].tolist(), out["v_tokens"].tolist())
    ]
    out["lexical_containment"] = [
        _containment(left, right) for left, right in zip(out["u_tokens"].tolist(), out["v_tokens"].tolist())
    ]

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

    out["graph_score"] = _safe_numeric(out["transparent_score"] if "transparent_score" in out.columns else out["score"])
    out["pref_attach_score"] = support_degree
    out["degree_recency_score"] = np.log1p(support_degree) + 0.5 * np.log1p(recent_degree)
    out["directed_closure_score"] = closure_core
    out["lexical_similarity_score"] = _safe_numeric(out["lexical_jaccard"]) + 0.25 * _safe_numeric(out["lexical_containment"])
    out["cooc_gap_score"] = _safe_numeric(out["gap_bonus"])
    return out


def _evaluate_models(panel_df: pd.DataFrame, k_values: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    model_cols = {
        "graph_score": "graph_score",
        "pref_attach": "pref_attach_score",
        "degree_recency": "degree_recency_score",
        "directed_closure": "directed_closure_score",
        "lexical_similarity": "lexical_similarity_score",
        "cooc_gap": "cooc_gap_score",
    }

    metric_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []

    for (cutoff_year_t, horizon), group in panel_df.groupby(["cutoff_year_t", "horizon"], sort=True):
        positives_df = group[group["appears_within_h"].astype(bool)]
        positives = {(str(row.u), str(row.v)) for row in positives_df[["u", "v"]].itertuples(index=False)}
        if not positives:
            continue

        ranking_maps: dict[str, pd.DataFrame] = {}
        for model_name, score_col in model_cols.items():
            ranked = (
                group[["u", "v", score_col]]
                .rename(columns={score_col: "score"})
                .sort_values(["score", "u", "v"], ascending=[False, True, True])
                .reset_index(drop=True)
            )
            ranked["rank"] = ranked.index + 1
            ranking_maps[model_name] = ranked
            metrics = evaluate_binary_ranking(ranked[["u", "v", "score", "rank"]], positives=positives, k_values=k_values)
            row = {
                "model": model_name,
                "cutoff_year_t": int(cutoff_year_t),
                "horizon": int(horizon),
                "n_eval_rows": int(len(group)),
                "n_positives": int(len(positives)),
                "mrr": float(metrics.get("mrr", 0.0)),
            }
            for k in k_values:
                row[f"hits_at_{k}"] = int(metrics.get(f"hits_at_{k}", 0.0))
                row[f"precision_at_{k}"] = float(metrics.get(f"precision_at_{k}", 0.0))
                row[f"recall_at_{k}"] = float(metrics.get(f"recall_at_{k}", 0.0))
            metric_rows.append(row)

        graph_top = {
            (str(row.u), str(row.v))
            for row in ranking_maps["graph_score"].head(100)[["u", "v"]].itertuples(index=False)
        }
        for model_name, ranked in ranking_maps.items():
            if model_name == "graph_score":
                continue
            other_top = {(str(row.u), str(row.v)) for row in ranked.head(100)[["u", "v"]].itertuples(index=False)}
            inter = graph_top & other_top
            union = graph_top | other_top
            overlap_rows.append(
                {
                    "model": model_name,
                    "cutoff_year_t": int(cutoff_year_t),
                    "horizon": int(horizon),
                    "top_100_overlap_count": int(len(inter)),
                    "top_100_jaccard": float(len(inter) / len(union)) if union else 0.0,
                    "graph_top100_covered_share": float(len(inter) / len(graph_top)) if graph_top else 0.0,
                }
            )

    metric_df = pd.DataFrame(metric_rows)
    overlap_df = pd.DataFrame(overlap_rows)
    return metric_df, overlap_df


def _summaries(metric_df: pd.DataFrame, overlap_df: pd.DataFrame, k_values: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = (
        metric_df.groupby(["model", "horizon"], as_index=False)
        .agg(
            mean_mrr=("mrr", "mean"),
            mean_precision_at_50=("precision_at_50", "mean") if 50 in k_values else ("mrr", "mean"),
            mean_precision_at_100=("precision_at_100", "mean") if 100 in k_values else ("mrr", "mean"),
            mean_recall_at_100=("recall_at_100", "mean") if 100 in k_values else ("mrr", "mean"),
            n_cutoffs=("cutoff_year_t", "nunique"),
        )
        .sort_values(["horizon", "mean_precision_at_100", "mean_mrr"], ascending=[True, False, False])
    )

    if not overlap_df.empty:
        overlap_summary = (
            overlap_df.groupby(["model", "horizon"], as_index=False)
            .agg(
                mean_top100_overlap=("top_100_overlap_count", "mean"),
                mean_top100_jaccard=("top_100_jaccard", "mean"),
                mean_graph_top100_covered_share=("graph_top100_covered_share", "mean"),
            )
            .sort_values(["horizon", "mean_graph_top100_covered_share"], ascending=[True, False])
        )
    else:
        overlap_summary = pd.DataFrame()
    return summary, overlap_summary


def _write_markdown(metric_df: pd.DataFrame, summary_df: pd.DataFrame, overlap_summary: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Benchmark Expansion Review",
        "",
        "This pass compares the current graph score with stronger transparent baselines on the same historical candidate panel.",
        "",
        "## Baselines added",
        "",
        "- `degree_recency`: endpoint support prominence plus recent support prominence",
        "- `directed_closure`: path support, mediator count, and local closure density",
        "- `lexical_similarity`: endpoint-label token overlap",
        "- `pref_attach`: existing preferential-attachment baseline retained for reference",
        "- `cooc_gap`: existing co-occurrence gap baseline retained for reference",
        "",
    ]

    for horizon in sorted(summary_df["horizon"].unique()):
        lines.append(f"## Horizon {int(horizon)}")
        block = summary_df[summary_df["horizon"] == horizon].copy()
        for row in block.itertuples(index=False):
            lines.append(
                f"- `{row.model}`: precision@100={float(row.mean_precision_at_100):.6f}, "
                f"recall@100={float(row.mean_recall_at_100):.6f}, MRR={float(row.mean_mrr):.6f}"
            )
        lines.append("")

        graph_row = block[block["model"] == "graph_score"]
        if not graph_row.empty:
            graph_precision = float(graph_row["mean_precision_at_100"].iloc[0])
            wins = []
            for row in block.itertuples(index=False):
                if row.model == "graph_score":
                    continue
                if graph_precision > float(row.mean_precision_at_100):
                    wins.append(row.model)
            if wins:
                lines.append(f"- Graph score beats these baselines on mean precision@100: {', '.join(wins)}.")
                lines.append("")

        if not overlap_summary.empty:
            overlap_block = overlap_summary[overlap_summary["horizon"] == horizon]
            if not overlap_block.empty:
                lines.append("### Overlap with graph top-100")
                for row in overlap_block.itertuples(index=False):
                    lines.append(
                        f"- `{row.model}`: mean overlap={float(row.mean_top100_overlap):.1f}, "
                        f"jaccard={float(row.mean_top100_jaccard):.3f}, "
                        f"graph coverage={float(row.mean_graph_top100_covered_share):.3f}"
                    )
                lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_note(summary_df: pd.DataFrame, overlap_summary: pd.DataFrame, note_path: Path) -> None:
    lines = [
        "# Benchmark Expansion Note",
        "",
        "## Scope",
        "",
        "- stronger transparent baselines on the historical candidate panel",
        "- same graph candidate universe used by the current benchmark path",
        "",
        "## Main read",
        "",
        "This pass asks whether the graph score is only beating preferential attachment because that benchmark is too weak.",
        "",
    ]

    for horizon in sorted(summary_df["horizon"].unique()):
        block = summary_df[summary_df["horizon"] == horizon].copy()
        graph = block[block["model"] == "graph_score"]
        if graph.empty:
            continue
        graph_prec = float(graph["mean_precision_at_100"].iloc[0])
        better_than = [
            row.model
            for row in block.itertuples(index=False)
            if row.model != "graph_score" and graph_prec > float(row.mean_precision_at_100)
        ]
        lines.append(f"### Horizon {int(horizon)}")
        if better_than:
            lines.append(f"- Graph score beats `{', '.join(better_than)}` on mean precision@100.")
        else:
            lines.append("- Graph score does not uniformly dominate the added baselines on mean precision@100.")
        strongest_alt = (
            block[block["model"] != "graph_score"]
            .sort_values(["mean_precision_at_100", "mean_mrr"], ascending=[False, False])
            .head(1)
        )
        if not strongest_alt.empty:
            row = strongest_alt.iloc[0]
            lines.append(
                f"- Strongest transparent alternative here is `{row['model']}` "
                f"with precision@100={float(row['mean_precision_at_100']):.6f}."
            )
        if not overlap_summary.empty:
            oblock = overlap_summary[overlap_summary["horizon"] == horizon].sort_values(
                "mean_graph_top100_covered_share", ascending=False
            )
            if not oblock.empty:
                top = oblock.iloc[0]
                lines.append(
                    f"- The closest top-100 alternative is `{top['model']}` "
                    f"with graph coverage={float(top['mean_graph_top100_covered_share']):.3f}."
                )
        lines.append("")

    lines.extend(
        [
            "## Recommendation",
            "",
            "Do:",
            "",
            "1. treat this as the next benchmark-strengthening layer for the paper",
            "2. use the strongest transparent alternative as the main robustness benchmark after preferential attachment",
            "3. keep the benchmark family small and interpretable",
            "",
            "Do not:",
            "",
            "- turn this into a broad benchmark zoo",
            "- add opaque semantic or embedding baselines before the transparent layer is interpreted",
        ]
    )
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    global args
    args = parse_args()
    out_dir = ensure_output_dir(Path(args.out_dir))
    note_path = Path(args.note_path)

    corpus_df = load_corpus(args.corpus_path)
    label_map = _load_label_map(corpus_df, args.concepts_csv)
    panel_df = _build_or_load_panel(args)
    panel_df = _add_baseline_scores(panel_df, label_map)

    metric_df, overlap_df = _evaluate_models(panel_df, k_values=_parse_int_list(args.k_values))
    summary_df, overlap_summary = _summaries(metric_df, overlap_df, _parse_int_list(args.k_values))

    metric_df.to_csv(out_dir / "benchmark_expansion_panel.csv", index=False)
    metric_df.to_parquet(out_dir / "benchmark_expansion_panel.parquet", index=False)
    summary_df.to_csv(out_dir / "benchmark_expansion_summary.csv", index=False)
    if not overlap_df.empty:
        overlap_df.to_csv(out_dir / "benchmark_expansion_overlap_by_cutoff.csv", index=False)
    if not overlap_summary.empty:
        overlap_summary.to_csv(out_dir / "benchmark_expansion_overlap_summary.csv", index=False)

    summary_payload = {
        "panel_rows": int(len(panel_df)),
        "cutoff_years": sorted(panel_df["cutoff_year_t"].dropna().astype(int).unique().tolist()),
        "horizons": sorted(panel_df["horizon"].dropna().astype(int).unique().tolist()),
        "models": sorted(metric_df["model"].dropna().astype(str).unique().tolist()),
        "mean_precision_at_100_by_model_horizon": {
            f"{row.model}__h{int(row.horizon)}": float(row.mean_precision_at_100)
            for row in summary_df.itertuples(index=False)
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    _write_markdown(metric_df, summary_df, overlap_summary, out_dir / "benchmark_expansion_review.md")
    _write_note(summary_df, overlap_summary, note_path)


if __name__ == "__main__":
    main()
