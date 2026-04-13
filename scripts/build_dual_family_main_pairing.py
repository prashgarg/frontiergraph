from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs/paper/149_dual_family_main_pairing"

PATH_TO_DIRECT_DIR = ROOT / "outputs/paper/123_effective_benchmark_widened_1990_2015"
DIRECT_TO_PATH_DIR = ROOT / "outputs/paper/148_effective_benchmark_direct_to_path_tuned"

PATH_TO_DIRECT_TUNING = ROOT / "outputs/paper/70_v2_2_effective_learned_reranker_tuning/tuning_best_configs.csv"
DIRECT_TO_PATH_TUNING = ROOT / "outputs/paper/147_direct_to_path_reranker_tuning_full/tuning_best_configs.csv"


FAMILY_LABELS = {
    "path_to_direct": "Path-to-direct",
    "direct_to_path": "Direct-to-path",
}

MODEL_ORDER = ["pref_attach", "transparent", "adopted"]
MODEL_LABELS = {
    "pref_attach": "Preferential attachment",
    "transparent": "Structural score",
    "adopted": "Learned reranker",
}
MODEL_COLORS = {
    "pref_attach": "#8c8c8c",
    "transparent": "#2f6db2",
    "adopted": "#b24b3d",
}
MODEL_MARKERS = {
    "pref_attach": "o",
    "transparent": "s",
    "adopted": "^",
}


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def _model_group(model_name: str) -> str:
    text = str(model_name)
    if text == "pref_attach":
        return "pref_attach"
    if text == "transparent":
        return "transparent"
    if text.startswith("adopted_"):
        return "adopted"
    raise ValueError(f"Unexpected model name: {model_name}")


def load_overall(path: Path, family_key: str) -> pd.DataFrame:
    df = pd.read_csv(path / "widened_overall_summary.csv")
    df["family_key"] = family_key
    df["family"] = FAMILY_LABELS[family_key]
    df["model_group"] = df["model"].map(_model_group)
    df["model_label"] = df["model_group"].map(MODEL_LABELS)
    df["future_links_per_100"] = 100.0 * pd.to_numeric(df["mean_top_share_realized"], errors="coerce")
    df["recall_at_100_pct"] = 100.0 * pd.to_numeric(df["mean_recall_at_100"], errors="coerce")
    return df


def load_tuning(path: Path, family_key: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["family_key"] = family_key
    df["family"] = FAMILY_LABELS[family_key]
    return df


def write_combined_csvs(overall_df: pd.DataFrame, tuning_df: pd.DataFrame) -> None:
    overall_cols = [
        "family",
        "family_key",
        "model",
        "model_group",
        "model_label",
        "horizon",
        "mean_mrr",
        "mean_recall_at_100",
        "recall_at_100_pct",
        "mean_top_share_realized",
        "future_links_per_100",
        "mean_top_mean_endpoint_broadness_pct",
        "n_cutoffs",
    ]
    overall_df[overall_cols].sort_values(["family", "horizon", "model_group"]).to_csv(
        OUT_DIR / "dual_family_main_overall.csv", index=False
    )

    tuning_cols = [
        "family",
        "horizon",
        "alpha",
        "model_kind",
        "feature_family",
        "pool_size",
        "mean_mrr",
        "mean_recall_at_100",
        "mean_delta_mrr_vs_transparent",
        "mean_delta_recall_at_100_vs_transparent",
    ]
    tuning_df[tuning_cols].sort_values(["family", "horizon"]).to_csv(
        OUT_DIR / "dual_family_tuning_best.csv", index=False
    )


def write_latex_table(overall_df: pd.DataFrame) -> None:
    rows = []
    for family in ["Path-to-direct", "Direct-to-path"]:
        fam = overall_df[overall_df["family"] == family].copy()
        for model_group in MODEL_ORDER:
            sub = fam[fam["model_group"] == model_group].copy()
            cell_map = {}
            for horizon in [5, 10, 15]:
                row = sub[sub["horizon"].astype(int) == horizon]
                if row.empty:
                    cell_map[horizon] = "--"
                    continue
                r = row.iloc[0]
                cell_map[horizon] = (
                    f"{r['future_links_per_100']:.1f} / "
                    f"{100.0 * float(r['mean_recall_at_100']):.1f} / "
                    f"{float(r['mean_mrr']):.4f}"
                )
            rows.append(
                (
                    family,
                    MODEL_LABELS[model_group],
                    cell_map[5],
                    cell_map[10],
                    cell_map[15],
                )
            )

    lines = [
        r"\begin{tabular}{L{0.17\linewidth}L{0.22\linewidth}L{0.18\linewidth}L{0.18\linewidth}L{0.18\linewidth}}",
        r"\toprule",
        r"Family & Model & $h{=}5$ & $h{=}10$ & $h{=}15$ \\",
        r"\midrule",
    ]
    current_family = None
    for family, model_label, h5, h10, h15 in rows:
        fam_cell = family if family != current_family else ""
        current_family = family
        lines.append(f"{fam_cell} & {model_label} & {h5} & {h10} & {h15} \\\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    (OUT_DIR / "dual_family_main_benchmark_table.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_figure(overall_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(9.4, 6.8), sharex=True)
    family_order = ["Path-to-direct", "Direct-to-path"]
    metric_specs = [
        ("future_links_per_100", "Future links per 100 suggestions"),
        ("recall_at_100_pct", "Recall@100 (%)"),
    ]

    for row_idx, family in enumerate(family_order):
        fam = overall_df[overall_df["family"] == family].copy()
        for col_idx, (metric, ylabel) in enumerate(metric_specs):
            ax = axes[row_idx, col_idx]
            for model_group in MODEL_ORDER:
                sub = fam[fam["model_group"] == model_group].sort_values("horizon")
                ax.plot(
                    sub["horizon"],
                    sub[metric],
                    color=MODEL_COLORS[model_group],
                    marker=MODEL_MARKERS[model_group],
                    linewidth=2.0,
                    markersize=6,
                    label=MODEL_LABELS[model_group],
                )
            ax.set_title(family if col_idx == 0 else "", loc="left", fontsize=11, fontweight="bold")
            ax.set_ylabel(ylabel, fontsize=10)
            ax.grid(axis="y", color="#d9d9d9", linewidth=0.6)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_xticks([5, 10, 15])
            ax.set_xlim(4, 16)
            if row_idx == 1:
                ax.set_xlabel("Horizon (years)", fontsize=10)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT_DIR / "dual_family_main_benchmark.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT_DIR / "dual_family_main_benchmark.pdf", bbox_inches="tight")
    plt.close(fig)


def write_recommendation(overall_df: pd.DataFrame, tuning_df: pd.DataFrame) -> None:
    adopted = overall_df[overall_df["model_group"] == "adopted"].copy()
    lines = [
        "# Dual-Family Main Benchmark Recommendation",
        "",
        "This note uses the paired widened benchmarks and reranker choices to decide what should move into the main text first.",
        "",
        "## 1. What is now ready to pair",
        "",
        "- strict-shortlist comparison on the 1990--2015 widened benchmark",
        "- transparent score versus preferential attachment versus the family-specific adopted reranker",
        "- path-to-direct and direct-to-path shown side by side with the same metrics and horizons",
        "",
        "These are the first paired result objects that are ready for the paper because both families now have completed widened runs and completed reranker tuning.",
        "",
        "## 2. What the paired benchmark says",
        "",
    ]
    for horizon in [5, 10, 15]:
        sub = adopted[adopted["horizon"].astype(int) == horizon].sort_values("family")
        if sub.empty:
            continue
        pieces = []
        for row in sub.itertuples(index=False):
            pieces.append(
                f"{row.family}: {row.future_links_per_100:.1f} future links per 100, "
                f"Recall@100 {row.recall_at_100_pct:.1f}, MRR {row.mean_mrr:.4f}"
            )
        lines.append(f"- h={horizon}: " + "; ".join(pieces))
    lines.extend(
        [
            "",
            "## 3. What should move into the main text now",
            "",
            "- one paired benchmark figure using the side-by-side family comparison",
            "- one paired benchmark table with the three metrics by family, model, and horizon",
            "- one short paragraph early in the results section stating that the two families are different historical objects rather than mirror images",
            "",
            "## 4. What should stay out of the main text for now",
            "",
            "- early-versus-late splits by family",
            "- tuning-grid details and model-family search details",
            "- any budget or heterogeneity pairing until the matching direct-to-path runs exist",
            "",
            "## 5. Immediate implication for the paper structure",
            "",
            "The main text can now support a two-family baseline comparison. It should still avoid promising a full dual-family atlas until the budget frontier, heterogeneity, and surfaced-example layers have matching direct-to-path outputs.",
            "",
            "So the next main-text pairing step should be narrow:",
            "",
            "1. pair the main benchmark figure",
            "2. pair the main benchmark table",
            "3. rewrite the results opener around the two objects",
            "4. leave budget and heterogeneity pairing for the next run wave",
            "",
            "## 6. Files in this package",
            "",
            "- `dual_family_main_overall.csv`",
            "- `dual_family_tuning_best.csv`",
            "- `dual_family_main_benchmark.png`",
            "- `dual_family_main_benchmark.pdf`",
            "- `dual_family_main_benchmark_table.tex`",
        ]
    )
    (OUT_DIR / "dual_family_main_recommendation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_out_dir()
    overall = pd.concat(
        [
            load_overall(PATH_TO_DIRECT_DIR, "path_to_direct"),
            load_overall(DIRECT_TO_PATH_DIR, "direct_to_path"),
        ],
        ignore_index=True,
    )
    tuning = pd.concat(
        [
            load_tuning(PATH_TO_DIRECT_TUNING, "path_to_direct"),
            load_tuning(DIRECT_TO_PATH_TUNING, "direct_to_path"),
        ],
        ignore_index=True,
    )
    write_combined_csvs(overall, tuning)
    write_latex_table(overall)
    build_figure(overall)
    write_recommendation(overall, tuning)


if __name__ == "__main__":
    main()
