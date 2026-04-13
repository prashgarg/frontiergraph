from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.common import CandidateBuildConfig, ensure_output_dir, first_appearance_map, restrict_positive_set_for_family
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    comparison_rankings_for_cutoff,
    evaluate_binary_ranking,
    parse_cutoff_years,
    parse_horizons,
)
from src.utils import load_config, load_corpus


def _future_set(
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> set[tuple[str, str]]:
    return {
        edge
        for edge, year in first_year_map.items()
        if int(cutoff_t) <= int(year) <= int(cutoff_t + horizon_h)
    }


def _default_cutoffs(min_year: int, max_year: int, max_h: int) -> list[int]:
    requested = [1990, 2000, 2010, 2015]
    keep = [y for y in requested if (min_year + 1) <= int(y) <= (max_year - max_h)]
    if keep:
        return keep
    return parse_cutoff_years(requested=None, min_year=min_year, max_year=max_year, max_h=max_h, step=10)


def build_family_comparison(
    corpus_df: pd.DataFrame,
    base_cfg: CandidateBuildConfig,
    cutoff_years: list[int],
    horizons: list[int],
    candidate_kind: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tau = int(base_cfg.tau)
    row_rows: list[dict] = []
    status_rows: list[dict] = []
    subfamily_rows: list[dict] = []
    model_rows: list[dict] = []
    subfamily_model_rows: list[dict] = []

    for family_mode in ["path_to_direct", "direct_to_path"]:
        cfg = CandidateBuildConfig(**asdict(base_cfg))
        cfg.candidate_kind = str(candidate_kind)
        cfg.candidate_family_mode = str(family_mode)
        first_year = first_appearance_map(
            corpus_df,
            candidate_kind=cfg.candidate_kind,
            candidate_family_mode=cfg.candidate_family_mode,
        )
        for cutoff_t in cutoff_years:
            train = corpus_df[corpus_df["year"] <= (int(cutoff_t) - 1)].copy()
            if train.empty:
                continue
            rankings = comparison_rankings_for_cutoff(train, cutoff_t=int(cutoff_t), cfg=cfg, tau=tau)
            main = rankings.get("main", pd.DataFrame())
            if main.empty:
                continue

            candidate_count = int(len(main))
            universe_pairs = {
                (str(r.u), str(r.v))
                for r in main[["u", "v"]].drop_duplicates().itertuples(index=False)
            }
            row_rows.append(
                {
                    "family_mode": family_mode,
                    "cutoff_year_t": int(cutoff_t),
                    "candidate_kind": str(candidate_kind),
                    "n_candidates": candidate_count,
                    "mean_score": float(pd.to_numeric(main["score"], errors="coerce").fillna(0.0).mean()),
                    "median_score": float(pd.to_numeric(main["score"], errors="coerce").fillna(0.0).median()),
                    "mean_path_support_norm": float(pd.to_numeric(main.get("path_support_norm", 0.0), errors="coerce").fillna(0.0).mean()),
                    "mean_mediator_count": float(pd.to_numeric(main.get("mediator_count", 0.0), errors="coerce").fillna(0.0).mean()),
                }
            )

            if "candidate_status_at_t" in main.columns:
                status_block = (
                    main.groupby("candidate_status_at_t", as_index=False)
                    .agg(n_candidates=("u", "size"))
                    .sort_values("n_candidates", ascending=False)
                )
                for row in status_block.itertuples(index=False):
                    status_rows.append(
                        {
                            "family_mode": family_mode,
                            "cutoff_year_t": int(cutoff_t),
                            "candidate_status_at_t": str(row.candidate_status_at_t),
                            "n_candidates": int(row.n_candidates),
                            "share_candidates": float(row.n_candidates) / float(max(candidate_count, 1)),
                        }
                    )

            if "candidate_subfamily" in main.columns:
                subfamily_block = (
                    main.groupby(["candidate_family", "candidate_subfamily", "candidate_scope_bucket"], as_index=False)
                    .agg(n_candidates=("u", "size"))
                    .sort_values("n_candidates", ascending=False)
                )
                for row in subfamily_block.itertuples(index=False):
                    subfamily_rows.append(
                        {
                            "family_mode": family_mode,
                            "cutoff_year_t": int(cutoff_t),
                            "candidate_family": str(row.candidate_family),
                            "candidate_subfamily": str(row.candidate_subfamily),
                            "candidate_scope_bucket": str(row.candidate_scope_bucket),
                            "n_candidates": int(row.n_candidates),
                            "share_candidates": float(row.n_candidates) / float(max(candidate_count, 1)),
                        }
                    )

            for horizon_h in horizons:
                positives_global = _future_set(first_year, cutoff_t=int(cutoff_t), horizon_h=int(horizon_h))
                positives = set(positives_global).intersection(universe_pairs)
                positives = restrict_positive_set_for_family(
                    positives,
                    candidate_pairs_df=main,
                    candidate_family_mode=cfg.candidate_family_mode,
                )
                positive_rate = float(len(positives)) / float(max(candidate_count, 1))
                future_coverage = float(len(positives)) / float(max(len(positives_global), 1))
                for model_name, ranking_df in rankings.items():
                    metrics = evaluate_binary_ranking(ranking_df, positives=positives, k_values=[50, 100, 500, 1000])
                    model_rows.append(
                        {
                            "family_mode": family_mode,
                            "candidate_kind": str(candidate_kind),
                            "model": str(model_name),
                            "cutoff_year_t": int(cutoff_t),
                            "horizon": int(horizon_h),
                            "n_candidates": candidate_count,
                            "n_future_edges_global": int(len(positives_global)),
                            "n_future_edges_in_universe": int(len(positives)),
                            "future_coverage": future_coverage,
                            "positive_rate": positive_rate,
                            "recall_at_50": float(metrics.get("recall_at_50", 0.0)),
                            "recall_at_100": float(metrics.get("recall_at_100", 0.0)),
                            "recall_at_500": float(metrics.get("recall_at_500", 0.0)),
                            "recall_at_1000": float(metrics.get("recall_at_1000", 0.0)),
                            "mrr": float(metrics.get("mrr", 0.0)),
                        }
                    )
                if {"candidate_subfamily", "candidate_scope_bucket", "candidate_family"}.issubset(main.columns):
                    pair_to_subfamily = {
                        (str(r.u), str(r.v)): (
                            str(r.candidate_family),
                            str(r.candidate_subfamily),
                            str(r.candidate_scope_bucket),
                        )
                        for r in main[["u", "v", "candidate_family", "candidate_subfamily", "candidate_scope_bucket"]]
                        .drop_duplicates()
                        .itertuples(index=False)
                    }
                    groups: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
                    for pair, triple in pair_to_subfamily.items():
                        groups.setdefault(triple, set()).add(pair)
                    for (candidate_family, candidate_subfamily, candidate_scope_bucket), pair_set in groups.items():
                        positives_sub = set(positives).intersection(pair_set)
                        for model_name, ranking_df in rankings.items():
                            subset = ranking_df[
                                ranking_df.apply(lambda r: (str(r["u"]), str(r["v"])) in pair_set, axis=1)
                            ].copy()
                            metrics = evaluate_binary_ranking(subset, positives=positives_sub, k_values=[50, 100, 500, 1000])
                            subfamily_model_rows.append(
                                {
                                    "family_mode": family_mode,
                                    "candidate_kind": str(candidate_kind),
                                    "candidate_family": candidate_family,
                                    "candidate_subfamily": candidate_subfamily,
                                    "candidate_scope_bucket": candidate_scope_bucket,
                                    "model": str(model_name),
                                    "cutoff_year_t": int(cutoff_t),
                                    "horizon": int(horizon_h),
                                    "n_candidates": int(len(subset)),
                                    "n_future_edges_in_subfamily": int(len(positives_sub)),
                                    "positive_rate": float(len(positives_sub)) / float(max(len(subset), 1)),
                                    "recall_at_50": float(metrics.get("recall_at_50", 0.0)),
                                    "recall_at_100": float(metrics.get("recall_at_100", 0.0)),
                                    "recall_at_500": float(metrics.get("recall_at_500", 0.0)),
                                    "recall_at_1000": float(metrics.get("recall_at_1000", 0.0)),
                                    "mrr": float(metrics.get("mrr", 0.0)),
                                }
                            )
    return (
        pd.DataFrame(row_rows),
        pd.DataFrame(status_rows),
        pd.DataFrame(subfamily_rows),
        pd.DataFrame(model_rows),
        pd.DataFrame(subfamily_model_rows),
    )


def write_markdown_summary(
    out_path: Path,
    corpus_path: Path,
    candidate_kind: str,
    cutoff_years: list[int],
    horizons: list[int],
    row_df: pd.DataFrame,
    status_df: pd.DataFrame,
    subfamily_df: pd.DataFrame,
    model_df: pd.DataFrame,
    subfamily_model_df: pd.DataFrame,
) -> None:
    lines = [
        "# Method v2 Family Comparison",
        "",
        f"- corpus: `{corpus_path}`",
        f"- candidate_kind: `{candidate_kind}`",
        f"- cutoff_years: `{','.join(str(x) for x in cutoff_years)}`",
        f"- horizons: `{','.join(str(x) for x in horizons)}`",
        "",
    ]

    if row_df.empty or model_df.empty:
        lines.extend(["No rows produced.", ""])
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return

    family_summary = (
        row_df.groupby("family_mode", as_index=False)
        .agg(
            mean_candidates=("n_candidates", "mean"),
            min_candidates=("n_candidates", "min"),
            max_candidates=("n_candidates", "max"),
            mean_path_support_norm=("mean_path_support_norm", "mean"),
            mean_mediator_count=("mean_mediator_count", "mean"),
        )
        .sort_values("family_mode")
    )
    lines.extend(["## Candidate Universe", ""])
    for row in family_summary.itertuples(index=False):
        lines.append(
            f"- {row.family_mode}: mean_candidates={float(row.mean_candidates):,.1f}, "
            f"range=[{int(row.min_candidates):,}, {int(row.max_candidates):,}], "
            f"mean_path_support_norm={float(row.mean_path_support_norm):.4f}, "
            f"mean_mediator_count={float(row.mean_mediator_count):.2f}"
        )

    perf_summary = (
        model_df.groupby(["family_mode", "horizon", "model"], as_index=False)
        .agg(
            mean_candidates=("n_candidates", "mean"),
            mean_future_edges_global=("n_future_edges_global", "mean"),
            mean_future_edges_in_universe=("n_future_edges_in_universe", "mean"),
            mean_future_coverage=("future_coverage", "mean"),
            mean_positive_rate=("positive_rate", "mean"),
            mean_recall_at_100=("recall_at_100", "mean"),
            mean_mrr=("mrr", "mean"),
        )
        .sort_values(["family_mode", "horizon", "model"])
    )
    lines.extend(["", "## Model Performance", ""])
    for family_mode in sorted(perf_summary["family_mode"].unique()):
        lines.append(f"### {family_mode}")
        lines.append("")
        block = perf_summary[perf_summary["family_mode"] == family_mode]
        for row in block.itertuples(index=False):
            lines.append(
                f"- h={int(row.horizon)}, {row.model}: mean_candidates={float(row.mean_candidates):,.1f}, "
                f"future_edges_in_universe={float(row.mean_future_edges_in_universe):.1f}, "
                f"future_edges_global={float(row.mean_future_edges_global):.1f}, "
                f"future_coverage={float(row.mean_future_coverage):.4f}, "
                f"positive_rate={float(row.mean_positive_rate):.6f}, "
                f"recall@100={float(row.mean_recall_at_100):.4f}, "
                f"mrr={float(row.mean_mrr):.4f}"
            )
        lines.append("")

    if not status_df.empty:
        top_status = (
            status_df.groupby(["family_mode", "candidate_status_at_t"], as_index=False)
            .agg(
                mean_candidates=("n_candidates", "mean"),
                mean_share=("share_candidates", "mean"),
            )
            .sort_values(["family_mode", "mean_candidates"], ascending=[True, False])
        )
        lines.extend(["## Status Mix", ""])
        for family_mode in sorted(top_status["family_mode"].unique()):
            lines.append(f"### {family_mode}")
            lines.append("")
            block = top_status[top_status["family_mode"] == family_mode].head(8)
            for row in block.itertuples(index=False):
                lines.append(
                    f"- {row.candidate_status_at_t}: mean_candidates={float(row.mean_candidates):,.1f}, "
                    f"mean_share={float(row.mean_share):.4f}"
                )
            lines.append("")

    if not subfamily_df.empty:
        top_subfamily = (
            subfamily_df.groupby(
                ["family_mode", "candidate_family", "candidate_subfamily", "candidate_scope_bucket"],
                as_index=False,
            )
            .agg(
                mean_candidates=("n_candidates", "mean"),
                mean_share=("share_candidates", "mean"),
            )
            .sort_values(["family_mode", "mean_candidates"], ascending=[True, False])
        )
        lines.extend(["## Subfamily Mix", ""])
        for family_mode in sorted(top_subfamily["family_mode"].unique()):
            lines.append(f"### {family_mode}")
            lines.append("")
            block = top_subfamily[top_subfamily["family_mode"] == family_mode].head(8)
            for row in block.itertuples(index=False):
                lines.append(
                    f"- family={row.candidate_family}, subfamily={row.candidate_subfamily}, "
                    f"scope={row.candidate_scope_bucket}: mean_candidates={float(row.mean_candidates):,.1f}, "
                    f"mean_share={float(row.mean_share):.4f}"
                )
            lines.append("")

    if not subfamily_model_df.empty:
        lines.extend(["## Subfamily Performance", ""])
        top_subfamily_perf = (
            subfamily_model_df.groupby(
                ["family_mode", "candidate_subfamily", "model", "horizon"],
                as_index=False,
            )
            .agg(
                mean_candidates=("n_candidates", "mean"),
                mean_future_edges_in_subfamily=("n_future_edges_in_subfamily", "mean"),
                mean_positive_rate=("positive_rate", "mean"),
                mean_recall_at_100=("recall_at_100", "mean"),
                mean_mrr=("mrr", "mean"),
            )
            .sort_values(["family_mode", "candidate_subfamily", "horizon", "mean_mrr"], ascending=[True, True, True, False])
        )
        for family_mode in sorted(top_subfamily_perf["family_mode"].unique()):
            lines.append(f"### {family_mode}")
            lines.append("")
            block = top_subfamily_perf[top_subfamily_perf["family_mode"] == family_mode]
            for subfamily in sorted(block["candidate_subfamily"].unique()):
                sub_block = block[block["candidate_subfamily"] == subfamily].head(6)
                lines.append(f"- subfamily={subfamily}")
                for row in sub_block.itertuples(index=False):
                    lines.append(
                        f"  h={int(row.horizon)}, {row.model}: "
                        f"candidates={float(row.mean_candidates):,.1f}, "
                        f"future_edges={float(row.mean_future_edges_in_subfamily):.1f}, "
                        f"positive_rate={float(row.mean_positive_rate):.6f}, "
                        f"recall@100={float(row.mean_recall_at_100):.4f}, "
                        f"mrr={float(row.mean_mrr):.4f}"
                    )
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare path_to_direct and direct_to_path on the real corpus.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--out", required=True, dest="out_dir")
    parser.add_argument("--candidate-kind", default="causal_claim")
    parser.add_argument("--years", type=int, nargs="*", default=None)
    parser.add_argument("--horizons", default="3,5,10")
    parser.add_argument("--tau", type=int, default=None)
    parser.add_argument("--max-path-len", type=int, default=None)
    parser.add_argument("--max-neighbors-per-mediator", type=int, default=None)
    parser.add_argument("--path-to-direct-scope", default=None)
    parser.add_argument("--paper-sample-frac", type=float, default=None)
    parser.add_argument("--sample-seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus_path = Path(args.corpus_path)
    config = load_config(args.config_path)
    base_cfg = candidate_cfg_from_config(config)
    base_cfg.candidate_kind = str(args.candidate_kind)
    if args.tau is not None:
        base_cfg.tau = int(args.tau)
    if args.max_path_len is not None:
        base_cfg.max_path_len = int(args.max_path_len)
    if args.max_neighbors_per_mediator is not None:
        base_cfg.max_neighbors_per_mediator = int(args.max_neighbors_per_mediator)
    if args.path_to_direct_scope is not None:
        base_cfg.path_to_direct_scope = str(args.path_to_direct_scope)
    corpus_df = load_corpus(corpus_path)
    if args.paper_sample_frac is not None:
        frac = float(args.paper_sample_frac)
        if not (0.0 < frac <= 1.0):
            raise ValueError("--paper-sample-frac must be in (0, 1].")
        paper_ids = pd.Index(corpus_df["paper_id"].astype(str).dropna().unique())
        rng = np.random.default_rng(int(args.sample_seed))
        sample_n = max(1, int(round(len(paper_ids) * frac)))
        sampled_ids = set(rng.choice(paper_ids.to_numpy(), size=sample_n, replace=False).tolist())
        corpus_df = corpus_df[corpus_df["paper_id"].astype(str).isin(sampled_ids)].copy()

    horizons = parse_horizons(args.horizons, default=[3, 5, 10])
    min_year = int(corpus_df["year"].min())
    max_year = int(corpus_df["year"].max())
    cutoff_years = [int(x) for x in args.years] if args.years else _default_cutoffs(min_year=min_year, max_year=max_year, max_h=max(horizons))

    row_df, status_df, subfamily_df, model_df, subfamily_model_df = build_family_comparison(
        corpus_df=corpus_df,
        base_cfg=base_cfg,
        cutoff_years=cutoff_years,
        horizons=horizons,
        candidate_kind=str(args.candidate_kind),
    )

    row_df.to_csv(out_dir / "family_candidate_counts.csv", index=False)
    status_df.to_csv(out_dir / "family_status_mix.csv", index=False)
    subfamily_df.to_csv(out_dir / "family_subfamily_mix.csv", index=False)
    model_df.to_csv(out_dir / "family_model_metrics.csv", index=False)
    subfamily_model_df.to_csv(out_dir / "family_subfamily_model_metrics.csv", index=False)

    meta = {
        "corpus_path": str(corpus_path),
        "config_path": str(args.config_path),
        "candidate_kind": str(args.candidate_kind),
        "cutoff_years": [int(x) for x in cutoff_years],
        "horizons": [int(x) for x in horizons],
        "tau": int(base_cfg.tau),
        "max_path_len": int(base_cfg.max_path_len),
        "max_neighbors_per_mediator": int(base_cfg.max_neighbors_per_mediator),
        "path_to_direct_scope": str(base_cfg.path_to_direct_scope),
        "paper_sample_frac": float(args.paper_sample_frac) if args.paper_sample_frac is not None else None,
        "sample_seed": int(args.sample_seed),
        "sampled_rows": int(len(corpus_df)),
        "sampled_papers": int(corpus_df["paper_id"].astype(str).nunique()),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(meta, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    write_markdown_summary(
        out_path=out_dir / "summary.md",
        corpus_path=corpus_path,
        candidate_kind=str(args.candidate_kind),
        cutoff_years=cutoff_years,
        horizons=horizons,
        row_df=row_df,
        status_df=status_df,
        subfamily_df=subfamily_df,
        model_df=model_df,
        subfamily_model_df=subfamily_model_df,
    )
    print(f"Wrote: {out_dir / 'family_candidate_counts.csv'}")
    print(f"Wrote: {out_dir / 'family_status_mix.csv'}")
    print(f"Wrote: {out_dir / 'family_subfamily_mix.csv'}")
    print(f"Wrote: {out_dir / 'family_model_metrics.csv'}")
    print(f"Wrote: {out_dir / 'family_subfamily_model_metrics.csv'}")
    print(f"Wrote: {out_dir / 'summary.md'}")
    print(f"Wrote: {out_dir / 'run_manifest.json'}")


if __name__ == "__main__":
    main()
