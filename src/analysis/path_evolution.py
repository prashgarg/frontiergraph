from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize

from src.analysis.common import ensure_output_dir
from src.analysis.headline_heterogeneity import _cutoff_period_label, _eligible_cutoffs, build_first_edge_metadata
from src.research_allocation_v2 import first_appearance_map_v2
from src.utils import load_corpus


def _build_state(edge_df: pd.DataFrame) -> dict[str, object]:
    direct_pairs = {(str(r.src_code), str(r.dst_code)) for r in edge_df[["src_code", "dst_code"]].drop_duplicates().itertuples(index=False)}
    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    for u, v in direct_pairs:
        outgoing[u].add(v)
        incoming[v].add(u)
    path_pairs: set[tuple[str, str]] = set()
    for w in set(incoming.keys()).intersection(outgoing.keys()):
        for u in incoming[w]:
            for v in outgoing[w]:
                if u != v:
                    path_pairs.add((u, v))
    return {"direct_pairs": direct_pairs, "path_pairs": path_pairs}


def build_path_evolution_summary(
    corpus_df: pd.DataFrame,
    edge_meta_df: pd.DataFrame,
    years: list[int],
    horizons: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    directed = corpus_df[corpus_df["edge_kind"] == "directed_causal"][["year", "src_code", "dst_code"]].copy()
    if directed.empty:
        return pd.DataFrame(), pd.DataFrame()
    first_year_map = first_appearance_map_v2(corpus_df, candidate_kind="directed_causal")
    direct_source_map = {
        (str(r.u), str(r.v)): {
            "first_source": str(r.first_source),
            "first_subfield_group": str(r.first_subfield_group),
        }
        for r in edge_meta_df[["u", "v", "first_source", "first_subfield_group"]].itertuples(index=False)
    }
    cache: dict[int, dict[str, object]] = {}

    def state_for(end_year: int) -> dict[str, object]:
        key = int(end_year)
        if key not in cache:
            cache[key] = _build_state(directed[directed["year"] <= key])
        return cache[key]

    summary_rows: list[dict] = []
    subgroup_rows: list[dict] = []
    max_year = int(pd.to_numeric(corpus_df["year"], errors="coerce").max())
    for t in years:
        train_state = state_for(int(t) - 1)
        train_direct = train_state["direct_pairs"]
        train_paths = train_state["path_pairs"]
        eligible_path_to_direct = train_paths.difference(train_direct)
        eligible_direct_to_path = train_direct.difference(train_paths)
        for h in horizons:
            if int(t + h) > max_year:
                continue
            future_state = state_for(int(t + h))
            future_direct = {edge for edge, year in first_year_map.items() if int(t) <= int(year) <= int(t + h)}
            path_to_direct = eligible_path_to_direct.intersection(future_direct)
            direct_to_path = eligible_direct_to_path.intersection(future_state["path_pairs"])
            for transition_type, eligible_set, realized_set in [
                ("path_to_direct", eligible_path_to_direct, path_to_direct),
                ("direct_to_path", eligible_direct_to_path, direct_to_path),
            ]:
                eligible_count = int(len(eligible_set))
                realized_count = int(len(realized_set))
                summary_rows.append(
                    {
                        "cutoff_year_t": int(t),
                        "cutoff_period": _cutoff_period_label(int(t)),
                        "horizon": int(h),
                        "transition_type": transition_type,
                        "eligible_pairs": eligible_count,
                        "realized_pairs": realized_count,
                        "transition_share": float(realized_count) / float(max(1, eligible_count)),
                    }
                )
                if realized_count == 0:
                    continue
                records = []
                for edge in realized_set:
                    meta = direct_source_map.get(edge, {"first_source": "Unknown", "first_subfield_group": "Unknown"})
                    records.append(meta)
                block = pd.DataFrame(records)
                for source, g in block.groupby("first_source", dropna=False):
                    subgroup_rows.append(
                        {
                            "cutoff_year_t": int(t),
                            "cutoff_period": _cutoff_period_label(int(t)),
                            "horizon": int(h),
                            "transition_type": transition_type,
                            "subgroup_type": "first_source",
                            "subgroup": str(source),
                            "positive_count": int(len(g)),
                            "positive_share_within_transition": float(len(g)) / float(realized_count),
                        }
                    )
                for subfield, g in block.groupby("first_subfield_group", dropna=False):
                    subgroup_rows.append(
                        {
                            "cutoff_year_t": int(t),
                            "cutoff_period": _cutoff_period_label(int(t)),
                            "horizon": int(h),
                            "transition_type": transition_type,
                            "subgroup_type": "first_subfield_group",
                            "subgroup": str(subfield),
                            "positive_count": int(len(g)),
                            "positive_share_within_transition": float(len(g)) / float(realized_count),
                        }
                    )
    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = (
            summary_df.groupby(["cutoff_period", "horizon", "transition_type"], as_index=False)
            .agg(
                n_cutoffs=("cutoff_year_t", "nunique"),
                eligible_pairs=("eligible_pairs", "sum"),
                realized_pairs=("realized_pairs", "sum"),
                transition_share=("transition_share", "mean"),
            )
            .sort_values(["transition_type", "horizon", "cutoff_period"])
            .reset_index(drop=True)
        )
    subgroup_df = pd.DataFrame(subgroup_rows)
    if not subgroup_df.empty:
        subgroup_df = (
            subgroup_df.groupby(["subgroup_type", "subgroup", "horizon", "transition_type"], as_index=False)
            .agg(
                n_cutoffs=("cutoff_year_t", "nunique"),
                positive_count=("positive_count", "sum"),
                positive_share_within_transition=("positive_share_within_transition", "mean"),
            )
            .sort_values(["subgroup_type", "transition_type", "horizon", "positive_count"], ascending=[True, True, True, False])
            .reset_index(drop=True)
        )
    return summary_df, subgroup_df


def plot_path_evolution(summary_df: pd.DataFrame, out_path: Path) -> None:
    if summary_df.empty:
        return
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    colors = {"path_to_direct": "#1d4ed8", "direct_to_path": "#b45309"}
    for transition_type, block in summary_df.groupby("transition_type"):
        means = (
            block.groupby("horizon", as_index=False)
            .agg(transition_share=("transition_share", "mean"))
            .sort_values("horizon")
        )
        ax.plot(
            means["horizon"],
            means["transition_share"],
            marker="o",
            linewidth=2,
            color=colors.get(str(transition_type), "#111827"),
            label=str(transition_type).replace("_", " "),
        )
    ax.set_xlabel("Horizon")
    ax.set_ylabel("Average transition share")
    ax.axhline(0.0, color="#9ca3af", linewidth=1)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_transition_mix(subgroup_df: pd.DataFrame, subgroup_type: str, min_total: int = 100) -> pd.DataFrame:
    if subgroup_df.empty:
        return pd.DataFrame()
    block = subgroup_df[subgroup_df["subgroup_type"] == subgroup_type].copy()
    if block.empty:
        return pd.DataFrame()
    wide = (
        block.pivot_table(
            index=["subgroup", "horizon"],
            columns="transition_type",
            values="positive_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    wide["path_to_direct_count"] = wide.get("path_to_direct", 0)
    wide["direct_to_path_count"] = wide.get("direct_to_path", 0)
    wide["total_realized_transitions"] = wide["path_to_direct_count"] + wide["direct_to_path_count"]
    wide = wide[wide["total_realized_transitions"] >= int(min_total)].copy()
    if wide.empty:
        return wide
    wide["path_to_direct_share_of_realized"] = wide["path_to_direct_count"] / wide["total_realized_transitions"].clip(lower=1)
    wide["path_to_direct_minus_direct_to_path"] = wide["path_to_direct_share_of_realized"] - 0.5
    return wide.sort_values(["horizon", "total_realized_transitions"], ascending=[True, False]).reset_index(drop=True)


def plot_transition_mix(mix_df: pd.DataFrame, out_path: Path, top_n: int = 8) -> None:
    if mix_df.empty:
        return
    top = (
        mix_df.groupby("subgroup", as_index=False)
        .agg(total_realized_transitions=("total_realized_transitions", "sum"))
        .sort_values("total_realized_transitions", ascending=False)
        .head(top_n)["subgroup"]
        .tolist()
    )
    heat = mix_df[mix_df["subgroup"].isin(top)].copy()
    if heat.empty:
        return
    value = heat.pivot(index="subgroup", columns="horizon", values="path_to_direct_share_of_realized")
    annot = heat.pivot(index="subgroup", columns="horizon", values="total_realized_transitions")
    fig, ax = plt.subplots(figsize=(8, max(4.2, 0.55 * len(value.index) + 1.3)))
    values = value.to_numpy(dtype=float)
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#e5e7eb")
    img = ax.imshow(np.ma.masked_invalid(values), aspect="auto", cmap=cmap, norm=Normalize(vmin=0.0, vmax=max(0.25, float(np.nanmax(values)) if np.isfinite(values).any() else 0.25)))
    ax.set_xticks(np.arange(len(value.columns)))
    ax.set_xticklabels([f"{int(c)}y" for c in value.columns], fontsize=10)
    ax.set_yticks(np.arange(len(value.index)))
    ax.set_yticklabels(value.index, fontsize=9)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if np.isfinite(values[i, j]):
                ax.text(j, i, f"{values[i, j]:.2f}\n{int(annot.iloc[i, j])}", ha="center", va="center", fontsize=8, color="#111827")
            else:
                ax.text(j, i, "sparse", ha="center", va="center", fontsize=7, color="#6b7280")
    cbar = fig.colorbar(img, ax=ax, fraction=0.025, pad=0.02)
    cbar.ax.set_ylabel("Path-to-direct share of realized transitions", rotation=270, labelpad=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_recommended_path_examples(opportunities_csv: Path, out_dir: Path) -> None:
    if not opportunities_csv.exists():
        return
    df = pd.read_csv(opportunities_csv)
    keep_cols = [
        "source_id",
        "source_label",
        "target_id",
        "target_label",
        "score",
        "supporting_path_count",
        "top_mediator_labels",
        "question_family",
        "app_link",
    ]
    keep = [c for c in keep_cols if c in df.columns]
    out = df[keep].copy().head(20)
    out.to_csv(out_dir / "current_recommended_path_examples.csv", index=False)
    lines = ["# Current Recommended Path-Based Questions", ""]
    for row in out.itertuples(index=False):
        lines.append(
            f"- {row.source_label} -> {row.target_label} | support paths={int(row.supporting_path_count)} | "
            f"family={getattr(row, 'question_family', 'Unknown')} | mediators={getattr(row, 'top_mediator_labels', '[]')}"
        )
    (out_dir / "current_recommended_path_examples.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Directed path-evolution appendix for the research-allocation atlas.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--paper_meta", required=True, dest="paper_meta_path")
    parser.add_argument("--cutoff-start", type=int, default=1980)
    parser.add_argument("--cutoff-end", type=int, default=2020)
    parser.add_argument("--cutoff-step", type=int, default=5)
    parser.add_argument("--horizons", default="3,5,10,15,20")
    parser.add_argument("--opportunities", default="site/public/data/v2/top_opportunities.csv")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    fig_dir = ensure_output_dir(Path(out_dir) / "figures")
    corpus_df = load_corpus(args.corpus_path)
    paper_meta_df = pd.read_parquet(args.paper_meta_path)
    horizons = [int(x.strip()) for x in str(args.horizons).split(",") if x.strip()]
    max_year = int(pd.to_numeric(corpus_df["year"], errors="coerce").max())
    years = _eligible_cutoffs(
        start_year=int(args.cutoff_start),
        end_year=int(args.cutoff_end),
        step=int(args.cutoff_step),
        max_observed_year=max_year,
        horizons=horizons,
    )
    edge_meta_df = build_first_edge_metadata(corpus_df, paper_meta_df, candidate_kind="directed_causal")
    summary_df, subgroup_df = build_path_evolution_summary(corpus_df=corpus_df, edge_meta_df=edge_meta_df, years=years, horizons=horizons)
    summary_df.to_parquet(Path(out_dir) / "path_evolution_summary.parquet", index=False)
    summary_df.to_csv(Path(out_dir) / "path_evolution_summary.csv", index=False)
    subgroup_df.to_parquet(Path(out_dir) / "path_evolution_subgroups.parquet", index=False)
    subgroup_df.to_csv(Path(out_dir) / "path_evolution_subgroups.csv", index=False)
    plot_path_evolution(summary_df, fig_dir / "path_evolution_comparison.png")
    source_mix = build_transition_mix(subgroup_df, subgroup_type="first_source", min_total=100)
    source_mix.to_csv(Path(out_dir) / "path_transition_mix_by_source.csv", index=False)
    plot_transition_mix(source_mix, fig_dir / "path_transition_mix_by_source.png", top_n=6)
    subfield_mix = build_transition_mix(subgroup_df, subgroup_type="first_subfield_group", min_total=80)
    subfield_mix.to_csv(Path(out_dir) / "path_transition_mix_by_subfield.csv", index=False)
    plot_transition_mix(subfield_mix, fig_dir / "path_transition_mix_by_subfield.png", top_n=8)
    write_recommended_path_examples(Path(args.opportunities), Path(out_dir))
    print(f"Wrote: {Path(out_dir) / 'path_evolution_summary.parquet'}")


if __name__ == "__main__":
    main()
