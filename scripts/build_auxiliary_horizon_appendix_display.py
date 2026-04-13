from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_SUMMARY_PATH = ROOT / "outputs/paper/90_retrieval_budget_eval_path_to_direct_h3_h20/retrieval_budget_summary.csv"
OUT_DIR = ROOT / "outputs/paper/143_auxiliary_horizon_appendix_refresh"
NOTE_PATH = ROOT / "next_steps/auxiliary_horizon_appendix_refresh_note.md"
POOL_SIZE = 5000


def _load_summary() -> pd.DataFrame:
    df = pd.read_csv(RETRIEVAL_SUMMARY_PATH)
    keep = df[df["pool_size"] == POOL_SIZE].copy()
    keep = keep.sort_values("horizon").reset_index(drop=True)
    keep["top100_hit_rate"] = keep["mean_precision_at_100"]
    keep["top100_recall"] = keep["mean_recall_at_100"]
    keep["pool_recall_ceiling"] = keep["mean_pool_recall_ceiling"]
    return keep[
        [
            "horizon",
            "n_cutoffs",
            "n_candidates_total",
            "n_future_positives_total",
            "top100_hit_rate",
            "top100_recall",
            "pool_recall_ceiling",
        ]
    ]


def _make_figure(summary: pd.DataFrame, out_path: Path) -> None:
    horizons = summary["horizon"].to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))

    axes[0].plot(horizons, summary["top100_hit_rate"], marker="o", linewidth=2.0, color="#1f77b4")
    axes[0].set_title("Transparent top-100 hit rate")
    axes[0].set_xlabel("Horizon")
    axes[0].set_ylabel("Precision@100")
    axes[0].set_xticks(horizons)
    axes[0].set_xticklabels([f"h={int(h)}" for h in horizons])
    axes[0].grid(alpha=0.25)

    axes[1].plot(horizons, summary["pool_recall_ceiling"], marker="o", linewidth=2.0, color="#d62728")
    axes[1].set_title("Transparent pool recall ceiling")
    axes[1].set_xlabel("Horizon")
    axes[1].set_ylabel(f"Recall in top {POOL_SIZE:,}")
    axes[1].set_xticks(horizons)
    axes[1].set_xticklabels([f"h={int(h)}" for h in horizons])
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_note(summary: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# Auxiliary Horizon Appendix Refresh",
        "",
        "This appendix display extends the current transparent benchmark to auxiliary horizons using the",
        "already-refreshed retrieval-budget run on the effective corpus.",
        "",
        f"- Pool size: {POOL_SIZE}",
        "- Horizons: 3, 5, 10, 15, 20",
        "",
        "## Mean outcomes",
        "",
        "| Horizon | Cutoffs | Mean candidates | Mean future positives | Precision@100 | Recall@100 | Pool recall ceiling |",
        "|---------|---------|-----------------|-----------------------|---------------|------------|---------------------|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {int(row.horizon)} | {int(row.n_cutoffs)} | {float(row.n_candidates_total):,.0f} "
            f"| {float(row.n_future_positives_total):,.0f} | {float(row.top100_hit_rate):.4f} "
            f"| {float(row.top100_recall):.4f} | {float(row.pool_recall_ceiling):.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "As the horizon lengthens, the transparent score's top-100 hit rate rises because many more future",
            "links become eligible realizations. But the top-100 recall remains tiny throughout, which is why the",
            "paper treats the transparent score as a retrieval layer rather than a full shortlist solution.",
            "The pool recall ceiling rises much faster than the visible top-100 hit rate, which is exactly what",
            "motivates the paper's later reranking and budget-allocation layers.",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = _load_summary()
    summary.to_csv(OUT_DIR / "auxiliary_horizon_summary.csv", index=False)
    _make_figure(summary, OUT_DIR / "auxiliary_horizon_comparison_refreshed.png")
    _write_note(summary, NOTE_PATH)
    manifest = {
        "source": str(RETRIEVAL_SUMMARY_PATH.relative_to(ROOT)),
        "pool_size": POOL_SIZE,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote auxiliary-horizon refresh to {OUT_DIR}")


if __name__ == "__main__":
    main()
