from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ARM_ORDER = ["adopted", "pref_attach", "transparent"]
FAMILY_ORDER = ["path_to_direct", "direct_to_path"]
ARM_LABELS = {
    "adopted": "Adopted reranker",
    "pref_attach": "Popularity",
    "transparent": "Transparent score",
}
FAMILY_LABELS = {
    "path_to_direct": "Path-to-direct",
    "direct_to_path": "Direct-to-path",
}
COLORS = {
    "adopted": "#2B6CB0",
    "pref_attach": "#C05621",
    "transparent": "#6B7280",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build paired historical usefulness comparison outputs.")
    parser.add_argument(
        "--path-to-direct-dir",
        default="outputs/paper/163_historical_appendix_usefulness_analysis_path_to_direct_async_internal",
        dest="path_to_direct_dir",
    )
    parser.add_argument(
        "--direct-to-path-dir",
        default="outputs/paper/160_historical_appendix_usefulness_analysis_direct_to_path_async_internal",
        dest="direct_to_path_dir",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/164_paired_historical_usefulness_comparison",
        dest="out_dir",
    )
    return parser.parse_args()


def _load_family_outputs(run_dir: Path, family: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    summary_by_arm = pd.read_csv(run_dir / "summary_by_arm.csv")
    artifact_counts = pd.read_csv(run_dir / "artifact_counts_by_arm.csv")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    summary_by_arm["family"] = family
    artifact_counts["family"] = family
    return summary_by_arm, artifact_counts, summary


def _build_combined_tables(path_dir: Path, direct_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p_arm, p_art, p_sum = _load_family_outputs(path_dir, "path_to_direct")
    d_arm, d_art, d_sum = _load_family_outputs(direct_dir, "direct_to_path")

    combined_arm = pd.concat([p_arm, d_arm], ignore_index=True)
    combined_arm["selection_arm"] = pd.Categorical(combined_arm["selection_arm"], ARM_ORDER, ordered=True)
    combined_arm["family"] = pd.Categorical(combined_arm["family"], FAMILY_ORDER, ordered=True)
    combined_arm = combined_arm.sort_values(["family", "selection_horizon", "selection_arm"]).reset_index(drop=True)

    artifact = pd.concat([p_art, d_art], ignore_index=True)
    pivot = (
        artifact.pivot_table(
            index=["family", "selection_arm", "selection_horizon"],
            columns="artifact_risk",
            values="n_items",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    for col in ["high", "medium", "low"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["n_items"] = pivot[["high", "medium", "low"]].sum(axis=1)
    pivot["high_artifact_share"] = pivot["high"] / pivot["n_items"]
    pivot["low_artifact_share"] = pivot["low"] / pivot["n_items"]
    pivot["selection_arm"] = pd.Categorical(pivot["selection_arm"], ARM_ORDER, ordered=True)
    pivot["family"] = pd.Categorical(pivot["family"], FAMILY_ORDER, ordered=True)
    pivot = pivot.sort_values(["family", "selection_horizon", "selection_arm"]).reset_index(drop=True)

    overall = pd.DataFrame(
        [
            {"family": "path_to_direct", **p_sum},
            {"family": "direct_to_path", **d_sum},
        ]
    )
    overall["family"] = pd.Categorical(overall["family"], FAMILY_ORDER, ordered=True)
    overall = overall.sort_values("family").reset_index(drop=True)
    return combined_arm, pivot, overall


def _plot_summary(combined_arm: pd.DataFrame, artifact_shares: pd.DataFrame, out_dir: Path) -> None:
    horizons = [5, 10, 15]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex="col")
    width = 0.22
    x = range(len(horizons))

    for col_idx, family in enumerate(FAMILY_ORDER):
        fam_scores = combined_arm[combined_arm["family"] == family]
        fam_art = artifact_shares[artifact_shares["family"] == family]

        ax_score = axes[0, col_idx]
        ax_art = axes[1, col_idx]

        for arm_idx, arm in enumerate(ARM_ORDER):
            score_rows = fam_scores[fam_scores["selection_arm"] == arm].set_index("selection_horizon")
            art_rows = fam_art[fam_art["selection_arm"] == arm].set_index("selection_horizon")
            xs = [i + (arm_idx - 1) * width for i in x]
            ax_score.bar(
                xs,
                [float(score_rows.loc[h, "mean_score"]) for h in horizons],
                width=width,
                color=COLORS[arm],
                label=ARM_LABELS[arm] if col_idx == 0 else None,
            )
            ax_art.bar(
                xs,
                [float(art_rows.loc[h, "high_artifact_share"]) for h in horizons],
                width=width,
                color=COLORS[arm],
            )

        ax_score.set_title(FAMILY_LABELS[family], fontsize=11)
        ax_score.set_ylim(3.3, 3.8)
        ax_score.grid(axis="y", alpha=0.2)
        ax_art.set_ylim(0.08, 0.26)
        ax_art.grid(axis="y", alpha=0.2)
        ax_art.set_xticks(list(x))
        ax_art.set_xticklabels([str(h) for h in horizons])
        if col_idx == 0:
            ax_score.set_ylabel("Mean usefulness score")
            ax_art.set_ylabel("High artifact share")

    axes[0, 2].axis("off")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    axes[0, 2].legend(handles, labels, loc="center left", frameon=False)
    axes[0, 2].text(
        0.0,
        0.45,
        "Top panel: average of readability,\ninterpretability, and usefulness.\n\nBottom panel: share rated\nhigh artifact risk.",
        fontsize=10,
        va="top",
    )
    axes[1, 2].axis("off")
    fig.suptitle("Historical usefulness screening by family, arm, and horizon", fontsize=13, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_dir / "paired_historical_usefulness_summary.png", dpi=220, bbox_inches="tight")
    fig.savefig(out_dir / "paired_historical_usefulness_summary.pdf", bbox_inches="tight")
    plt.close(fig)


def _write_note(combined_arm: pd.DataFrame, overall: pd.DataFrame, artifact_shares: pd.DataFrame, out_dir: Path) -> None:
    def best_arm(df: pd.DataFrame, family: str, horizon: int) -> str:
        sub = df[(df["family"] == family) & (df["selection_horizon"] == horizon)].sort_values("mean_score", ascending=False)
        return str(sub.iloc[0]["selection_arm"])

    lines: list[str] = []
    lines.append("# Paired historical usefulness comparison")
    lines.append("")
    for row in overall.itertuples(index=False):
        fam = str(row.family)
        lines.append(
            f"- {FAMILY_LABELS[fam]}: mean readability `{row.mean_readability:.3f}`, "
            f"mean interpretability `{row.mean_interpretability:.3f}`, "
            f"mean usefulness `{row.mean_usefulness:.3f}`, "
            f"estimated cost `${row.estimated_cost_usd:.2f}`."
        )
    lines.append("")
    lines.append("## Arm-by-horizon read")
    lines.append("")
    for family in FAMILY_ORDER:
        for horizon in [5, 10, 15]:
            arm = best_arm(combined_arm, family, horizon)
            score = float(
                combined_arm[
                    (combined_arm["family"] == family)
                    & (combined_arm["selection_horizon"] == horizon)
                    & (combined_arm["selection_arm"] == arm)
                ]["mean_score"].iloc[0]
            )
            high_share = float(
                artifact_shares[
                    (artifact_shares["family"] == family)
                    & (artifact_shares["selection_horizon"] == horizon)
                    & (artifact_shares["selection_arm"] == arm)
                ]["high_artifact_share"].iloc[0]
            )
            lines.append(
                f"- {FAMILY_LABELS[family]}, h={horizon}: best mean score is `{ARM_LABELS[arm]}` "
                f"at `{score:.3f}` with high-artifact share `{high_share:.3f}`."
            )
    lines.append("")
    lines.append("## Takeaway")
    lines.append("")
    lines.append(
        "- Path-to-direct now looks slightly stronger than direct-to-path on readability, interpretability, "
        "and usefulness. Within path-to-direct, the adopted reranker is best at every horizon. "
        "Within direct-to-path, the adopted reranker is best at h=5 and h=10, but not at h=15."
    )
    (out_dir / "paired_historical_usefulness_note.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    combined_arm, artifact_shares, overall = _build_combined_tables(
        Path(args.path_to_direct_dir),
        Path(args.direct_to_path_dir),
    )
    combined_arm.to_csv(out_dir / "paired_historical_usefulness_by_arm.csv", index=False)
    artifact_shares.to_csv(out_dir / "paired_historical_usefulness_artifact_shares.csv", index=False)
    overall.to_csv(out_dir / "paired_historical_usefulness_overall.csv", index=False)
    _plot_summary(combined_arm, artifact_shares, out_dir)
    _write_note(combined_arm, overall, artifact_shares, out_dir)


if __name__ == "__main__":
    main()
