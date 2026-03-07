from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.explain import build_explanation_tables
from src.features_motifs import compute_motif_features
from src.features_pairs import compute_underexplored_pairs
from src.features_paths import compute_path_features
from src.scoring import compute_candidate_scores
from src.utils import ensure_dir, ensure_parent_dir, load_config, load_corpus, pair_key


def _first_appearance_year(corpus_df: pd.DataFrame) -> dict[tuple[str, str], int]:
    grouped = corpus_df.groupby(["src_code", "dst_code"], as_index=False).agg(first_year=("year", "min"))
    return {(str(r.src_code), str(r.dst_code)): int(r.first_year) for r in grouped.itertuples(index=False)}


def _evaluate_ranking(
    ranked_df: pd.DataFrame,
    future_edges: set[tuple[str, str]],
    k_values: list[int],
) -> dict[str, float]:
    rank_map = {(str(r.u), str(r.v)): int(i + 1) for i, r in enumerate(ranked_df.itertuples(index=False))}
    total_future = max(len(future_edges), 1)
    metrics: dict[str, float] = {"n_future_edges": float(len(future_edges))}
    for k in k_values:
        hits = sum(1 for edge in future_edges if rank_map.get(edge, np.inf) <= k)
        metrics[f"recall_at_{k}"] = hits / float(total_future)
    rr = [1.0 / rank_map[e] if e in rank_map else 0.0 for e in future_edges]
    metrics["mrr"] = float(np.mean(rr)) if rr else 0.0
    return metrics


def _build_all_pairs(nodes: list[str]) -> pd.DataFrame:
    if not nodes:
        return pd.DataFrame(columns=["u", "v"])
    arr = np.array(nodes, dtype=object)
    u = np.repeat(arr, len(arr))
    v = np.tile(arr, len(arr))
    mask = u != v
    return pd.DataFrame({"u": u[mask], "v": v[mask]})


def _build_missing_pairs(train_df: pd.DataFrame, all_pairs_df: pd.DataFrame) -> pd.DataFrame:
    if all_pairs_df.empty:
        return all_pairs_df.copy()
    existing = train_df[["src_code", "dst_code"]].drop_duplicates().rename(columns={"src_code": "u", "dst_code": "v"})
    existing["u"] = existing["u"].astype(str)
    existing["v"] = existing["v"].astype(str)
    merged = all_pairs_df.merge(existing.assign(_exists=1), on=["u", "v"], how="left")
    return merged[merged["_exists"].isna()][["u", "v"]].reset_index(drop=True)


def _cooc_baseline(train_df: pd.DataFrame, tau: int, all_pairs_df: pd.DataFrame) -> pd.DataFrame:
    base = _build_missing_pairs(train_df, all_pairs_df)
    if base.empty:
        return base.assign(score=[])
    pairs = compute_underexplored_pairs(train_df, tau=tau)
    gap_map = {pair_key(str(r.u), str(r.v)): float(r.gap_bonus) for r in pairs.itertuples(index=False)}
    base["score"] = [gap_map.get(pair_key(str(r.u), str(r.v)), 1.0) for r in base.itertuples(index=False)]
    return base.sort_values("score", ascending=False).reset_index(drop=True)


def _pref_attachment_baseline(train_df: pd.DataFrame, all_pairs_df: pd.DataFrame) -> pd.DataFrame:
    base = _build_missing_pairs(train_df, all_pairs_df)
    if base.empty:
        return base.assign(score=[])
    out_deg = train_df.groupby("src_code", as_index=False).agg(out_degree=("dst_code", "nunique"))
    in_deg = train_df.groupby("dst_code", as_index=False).agg(in_degree=("src_code", "nunique"))
    out_map = {str(r.src_code): int(r.out_degree) for r in out_deg.itertuples(index=False)}
    in_map = {str(r.dst_code): int(r.in_degree) for r in in_deg.itertuples(index=False)}
    base["score"] = [float(out_map.get(str(r.u), 0) * in_map.get(str(r.v), 0)) for r in base.itertuples(index=False)]
    return base.sort_values("score", ascending=False).reset_index(drop=True)


def _main_model_ranking(
    train_df: pd.DataFrame,
    tau: int,
    max_len: int,
    max_neighbors_per_mediator: int,
    scoring_cfg: dict[str, float],
) -> pd.DataFrame:
    pairs = compute_underexplored_pairs(train_df, tau=tau)
    paths = compute_path_features(train_df, max_len=max_len, max_neighbors_per_mediator=max_neighbors_per_mediator)
    motifs = compute_motif_features(train_df, max_neighbors_per_mediator=max_neighbors_per_mediator)
    ranked = compute_candidate_scores(
        pairs_df=pairs,
        paths_df=paths,
        motifs_df=motifs,
        alpha=float(scoring_cfg.get("alpha", 0.5)),
        beta=float(scoring_cfg.get("beta", 0.2)),
        gamma=float(scoring_cfg.get("gamma", 0.3)),
        delta=float(scoring_cfg.get("delta", 0.2)),
    )
    if "score" not in ranked.columns:
        ranked["score"] = 0.0
    return ranked[["u", "v", "score"]].copy()


def run_backtest(
    corpus_df: pd.DataFrame,
    config: dict,
    existing_metrics_df: pd.DataFrame | None = None,
    checkpoint_path: Path | None = None,
    verbose: bool = False,
) -> pd.DataFrame:
    backtest_cfg = config.get("backtest", {})
    features_cfg = config.get("features", {})
    scoring_cfg = config.get("scoring", {})
    horizons = [int(x) for x in backtest_cfg.get("horizons", [1, 3, 5])]
    k_values = [int(x) for x in backtest_cfg.get("k_values", [50, 100, 500, 1000])]
    tau = int(features_cfg.get("tau", 2))
    max_len = int(features_cfg.get("max_path_len", 2))
    max_neighbors_per_mediator = int(features_cfg.get("max_neighbors_per_mediator", 120))

    min_year = int(corpus_df["year"].min())
    max_year = int(corpus_df["year"].max())
    first_year_map = _first_appearance_year(corpus_df)
    edges_by_first_year: dict[int, set[tuple[str, str]]] = {}
    for edge, first_year in first_year_map.items():
        edges_by_first_year.setdefault(int(first_year), set()).add(edge)
    all_nodes = sorted(set(corpus_df["src_code"].astype(str)) | set(corpus_df["dst_code"].astype(str)))
    all_pairs_df = _build_all_pairs(all_nodes)

    rows: list[dict] = []
    done_keys: set[tuple[str, int, int]] = set()
    if existing_metrics_df is not None and not existing_metrics_df.empty:
        rows.extend(existing_metrics_df.to_dict(orient="records"))
        done_keys = {
            (str(r.model), int(r.horizon), int(r.cutoff_year_t))
            for r in existing_metrics_df[["model", "horizon", "cutoff_year_t"]].itertuples(index=False)
        }
    total_needed = sum(max(0, (max_year - h) - (min_year + 1) + 1) for h in horizons) * 3
    if verbose:
        print(f"Backtest total target rows (models*horizons*cutoffs): {total_needed}")
        print(f"Already completed rows: {len(done_keys)}")

    max_h = max(horizons) if horizons else 1
    for t in range(min_year + 1, max_year):
        if verbose:
            print(f"Processing cutoff year t={t}...")
        train_df = corpus_df[corpus_df["year"] <= (t - 1)]
        if train_df.empty:
            continue

        model_rankings = {
            "main": _main_model_ranking(
                train_df,
                tau=tau,
                max_len=max_len,
                max_neighbors_per_mediator=max_neighbors_per_mediator,
                scoring_cfg=scoring_cfg,
            ),
            "cooc_gap": _cooc_baseline(train_df, tau=tau, all_pairs_df=all_pairs_df),
            "pref_attach": _pref_attachment_baseline(train_df, all_pairs_df=all_pairs_df),
        }

        for h in horizons:
            if t > (max_year - h):
                continue
            future_edges: set[tuple[str, str]] = set()
            for year in range(t, t + h + 1):
                future_edges.update(edges_by_first_year.get(year, set()))
            if not future_edges:
                continue

            for model_name, ranking_df in model_rankings.items():
                key = (model_name, int(h), int(t))
                if key in done_keys:
                    continue
                metrics = _evaluate_ranking(ranking_df, future_edges=future_edges, k_values=k_values)
                row = {
                    "model": model_name,
                    "horizon": h,
                    "cutoff_year_t": t,
                    **metrics,
                }
                rows.append(row)
                done_keys.add(key)
        if checkpoint_path is not None:
            pd.DataFrame(rows).to_parquet(checkpoint_path, index=False)
            if verbose:
                print(f"Checkpoint written: {checkpoint_path} ({len(rows)} rows)")
    return pd.DataFrame(rows)


def _plot_backtest(metrics_df: pd.DataFrame, figdir: Path) -> list[Path]:
    ensure_dir(figdir)
    out_paths: list[Path] = []
    if metrics_df.empty:
        return out_paths

    # Recall@100 by horizon
    recall_col = "recall_at_100" if "recall_at_100" in metrics_df.columns else None
    if recall_col:
        g = metrics_df.groupby(["model", "horizon"], as_index=False)[recall_col].mean()
        plt.figure(figsize=(8, 5))
        for model, sub in g.groupby("model"):
            plt.plot(sub["horizon"], sub[recall_col], marker="o", label=model)
        plt.xlabel("Horizon (years)")
        plt.ylabel("Mean Recall@100")
        plt.title("Backtest Recall@100 by Horizon")
        plt.legend()
        plt.tight_layout()
        path = figdir / "backtest_recall_at_100.png"
        plt.savefig(path, dpi=150)
        plt.close()
        out_paths.append(path)

    # MRR by horizon
    g2 = metrics_df.groupby(["model", "horizon"], as_index=False)["mrr"].mean()
    plt.figure(figsize=(8, 5))
    for model, sub in g2.groupby("model"):
        plt.plot(sub["horizon"], sub["mrr"], marker="o", label=model)
    plt.xlabel("Horizon (years)")
    plt.ylabel("Mean MRR")
    plt.title("Backtest MRR by Horizon")
    plt.legend()
    plt.tight_layout()
    path2 = figdir / "backtest_mrr.png"
    plt.savefig(path2, dpi=150)
    plt.close()
    out_paths.append(path2)
    return out_paths


def _build_top_examples(corpus_df: pd.DataFrame, config: dict, top_n: int = 8) -> pd.DataFrame:
    tau = int(config.get("features", {}).get("tau", 2))
    max_len = int(config.get("features", {}).get("max_path_len", 2))
    scoring_cfg = config.get("scoring", {})
    pairs = compute_underexplored_pairs(corpus_df, tau=tau)
    paths = compute_path_features(corpus_df, max_len=max_len)
    motifs = compute_motif_features(corpus_df)
    cands = compute_candidate_scores(
        pairs_df=pairs,
        paths_df=paths,
        motifs_df=motifs,
        alpha=float(scoring_cfg.get("alpha", 0.5)),
        beta=float(scoring_cfg.get("beta", 0.2)),
        gamma=float(scoring_cfg.get("gamma", 0.3)),
        delta=float(scoring_cfg.get("delta", 0.2)),
    )
    return cands.head(top_n)


def _write_report(
    report_path: Path,
    corpus_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    fig_paths: list[Path],
    top_examples: pd.DataFrame,
    ingest_log_path: Path | None = None,
) -> None:
    ensure_parent_dir(report_path)
    n_nodes = len(set(corpus_df["src_code"].astype(str)) | set(corpus_df["dst_code"].astype(str)))
    n_edges = len(corpus_df)
    n_papers = corpus_df["paper_id"].nunique()
    year_min = int(corpus_df["year"].min())
    year_max = int(corpus_df["year"].max())

    lines: list[str] = []
    lines.append("# FrontierGraph Backtest Report")
    lines.append("")
    lines.append("## Dataset Summary")
    lines.append(f"- nodes: {n_nodes}")
    lines.append(f"- edges: {n_edges}")
    lines.append(f"- papers: {n_papers}")
    lines.append(f"- years: {year_min} to {year_max}")
    lines.append("")
    lines.append("## Ingest / Extraction Logs")
    if ingest_log_path and ingest_log_path.exists():
        try:
            payload = json.loads(ingest_log_path.read_text(encoding="utf-8"))
            logs = payload.get("logs", [])
            if logs:
                for msg in logs[:12]:
                    lines.append(f"- {msg}")
            else:
                lines.append("- no logs captured")
        except Exception:  # noqa: BLE001
            lines.append("- failed to parse ingest log")
    else:
        lines.append("- ingest log not found")
    lines.append("")
    lines.append("## Top Missing-Claims Examples")
    if top_examples.empty:
        lines.append("- no candidate examples generated")
    else:
        expl = build_explanation_tables(corpus_df, top_examples)
        med = expl["candidate_mediators"]
        paths = expl["candidate_paths"]
        for row in top_examples.itertuples(index=False):
            lines.append(
                f"- {row.u} -> {row.v}: score={float(row.score):.4f}, "
                f"path={float(row.path_support_norm):.4f}, gap={float(row.gap_bonus):.4f}, "
                f"motif={float(row.motif_bonus_norm):.4f}, hub_penalty={float(row.hub_penalty):.4f}"
            )
            med_row = med[(med["candidate_u"] == row.u) & (med["candidate_v"] == row.v)].head(1)
            path_row = paths[(paths["candidate_u"] == row.u) & (paths["candidate_v"] == row.v)].head(1)
            if not med_row.empty:
                lines.append(f"  - top mediator: {med_row.iloc[0]['mediator']}")
            if not path_row.empty:
                lines.append(f"  - top path: {path_row.iloc[0]['path_text']}")
    lines.append("")
    lines.append("## Backtesting Metrics")
    if metrics_df.empty:
        lines.append("- backtest produced no rows")
    else:
        summary_cols = [c for c in ["recall_at_50", "recall_at_100", "recall_at_500", "recall_at_1000", "mrr"] if c in metrics_df]
        summary = metrics_df.groupby(["model", "horizon"], as_index=False)[summary_cols].mean()
        lines.append(summary.to_markdown(index=False))
    lines.append("")
    lines.append("## Backtesting Figures")
    if fig_paths:
        for p in fig_paths:
            lines.append(f"- {p.as_posix()}")
    else:
        lines.append("- no figures generated")
    lines.append("")
    lines.append("## Limitations")
    lines.append("- Graph signals are heuristic and may over-rank hub-driven associations.")
    lines.append("- Directionality quality depends on source extraction quality and schema mapping.")
    lines.append("- Backtests measure rediscovery of future observed edges, not causal truth.")
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retrospective backtesting for missing-claim ranking.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--out", required=True, dest="out_path")
    parser.add_argument("--figdir", required=True, dest="figdir")
    parser.add_argument("--config", default="config/config.yaml", dest="config_path")
    parser.add_argument("--resume", action="store_true", help="Resume from existing --out table if present")
    parser.add_argument("--verbose", action="store_true", help="Print per-cutoff progress")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config_path)
    corpus_df = load_corpus(args.corpus_path)
    out_path = Path(args.out_path)
    existing_df = None
    if args.resume and out_path.exists():
        try:
            existing_df = pd.read_parquet(out_path)
            print(f"Loaded existing backtest checkpoint: {out_path} ({len(existing_df)} rows)")
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to load checkpoint {out_path}: {exc}")
            existing_df = None
    metrics_df = run_backtest(
        corpus_df,
        config=config,
        existing_metrics_df=existing_df,
        checkpoint_path=out_path,
        verbose=args.verbose,
    )

    ensure_parent_dir(out_path)
    metrics_df.to_parquet(out_path, index=False)
    print(f"Wrote backtest table: {out_path} ({len(metrics_df)} rows)")

    figdir = Path(args.figdir)
    fig_paths = _plot_backtest(metrics_df, figdir=figdir)
    for fp in fig_paths:
        print(f"Wrote figure: {fp}")

    top_examples = _build_top_examples(corpus_df, config=config, top_n=8)
    report_path = out_path.parent.parent / "report.md"
    ingest_log_path = Path(args.corpus_path).with_name("ingest_log.json")
    _write_report(
        report_path=report_path,
        corpus_df=corpus_df,
        metrics_df=metrics_df,
        fig_paths=fig_paths,
        top_examples=top_examples,
        ingest_log_path=ingest_log_path if ingest_log_path.exists() else None,
    )
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
