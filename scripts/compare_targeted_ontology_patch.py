from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


NOISY_PATTERNS = [
    r"carbon emissions \(co2 emissions\)",
    r"co2 emissions \(carbon emissions\)",
    r"environmental quality \(co2 emissions\)",
    r"willingness to pay \(wtp\)",
    r"ecological footprints",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare baseline and patched current-frontier artifacts.")
    parser.add_argument("--baseline-frontier", required=True)
    parser.add_argument("--patched-frontier", required=True)
    parser.add_argument("--baseline-shortlist", required=True)
    parser.add_argument("--patched-shortlist", required=True)
    parser.add_argument("--baseline-concentration", required=True)
    parser.add_argument("--patched-concentration", required=True)
    parser.add_argument("--baseline-tuning-best")
    parser.add_argument("--patched-tuning-best")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _load_env_share(summary_path: Path) -> dict[str, float]:
    df = pd.read_csv(summary_path)
    out: dict[str, float] = {}
    for stage in sorted(df["stage"].unique()):
        sub = df[(df["stage"] == stage) & (df["group"] == "environment_climate")]
        out[stage] = float(sub["share"].iloc[0]) if not sub.empty else 0.0
    return out


def _count_noisy_strings(shortlist: pd.DataFrame) -> int:
    text = (
        shortlist["display_title"].fillna("").astype(str)
        + " || "
        + shortlist["display_why"].fillna("").astype(str)
    )
    total = 0
    for pattern in NOISY_PATTERNS:
        total += int(text.str.contains(pattern, case=False, regex=True).sum())
    return total


def _count_poorly_labeled(shortlist: pd.DataFrame) -> dict[int, int]:
    out: dict[int, int] = {}
    why = shortlist["display_why"].fillna("").astype(str)
    for horizon in sorted(shortlist["horizon"].dropna().unique()):
        mask = shortlist["horizon"].eq(int(horizon)) & why.str.contains("poorly labeled", case=False, regex=False)
        out[int(horizon)] = int(mask.sum())
    return out


def _top20_container_hits(shortlist: pd.DataFrame) -> dict[int, int]:
    container_patterns = [
        r"\bpolicy variables\b",
        r"\bmodels\b",
        r"\bmodel parameters\b",
        r"\bparameters\b",
    ]
    title = shortlist["display_title"].fillna("").astype(str)
    out: dict[int, int] = {}
    for horizon in sorted(shortlist["horizon"].dropna().unique()):
        sub = shortlist[shortlist["horizon"] == int(horizon)].sort_values("shortlist_rank").head(20)
        count = 0
        for pattern in container_patterns:
            count += int(sub["display_title"].fillna("").astype(str).str.contains(pattern, case=False, regex=True).sum())
        out[int(horizon)] = int(count)
    return out


def _top_target_share(frontier: pd.DataFrame) -> dict[int, float]:
    out: dict[int, float] = {}
    for horizon in sorted(frontier["horizon"].dropna().unique()):
        sub = frontier[(frontier["horizon"] == int(horizon)) & (frontier["surface_rank"] <= 100)].copy()
        if sub.empty:
            out[int(horizon)] = 0.0
            continue
        labels = sub["v_label"].fillna(sub["v"]).astype(str)
        top_share = float(labels.value_counts(normalize=True).iloc[0]) if not labels.empty else 0.0
        out[int(horizon)] = top_share
    return out


def _recall_at_100(best_path: str | None, horizon: int) -> float | None:
    if not best_path:
        return None
    path = Path(best_path)
    if not path.exists():
        return None
    df = pd.read_csv(path)
    sub = df[df["horizon"] == int(horizon)]
    if sub.empty:
        return None
    return float(sub.iloc[0]["mean_recall_at_100"])


def _top_titles(df: pd.DataFrame, horizon: int, top_n: int = 10) -> list[str]:
    sub = df[df["horizon"] == horizon].sort_values("shortlist_rank").head(top_n)
    return sub["display_title"].fillna("").astype(str).tolist()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline_frontier = pd.read_csv(args.baseline_frontier)
    patched_frontier = pd.read_csv(args.patched_frontier)
    baseline_shortlist = pd.read_csv(args.baseline_shortlist)
    patched_shortlist = pd.read_csv(args.patched_shortlist)

    baseline_env = _load_env_share(Path(args.baseline_concentration))
    patched_env = _load_env_share(Path(args.patched_concentration))
    baseline_poor = _count_poorly_labeled(baseline_shortlist)
    patched_poor = _count_poorly_labeled(patched_shortlist)
    baseline_containers = _top20_container_hits(baseline_shortlist)
    patched_containers = _top20_container_hits(patched_shortlist)
    baseline_target_share = _top_target_share(baseline_frontier)
    patched_target_share = _top_target_share(patched_frontier)
    baseline_recall_h10 = _recall_at_100(args.baseline_tuning_best, horizon=10)
    patched_recall_h10 = _recall_at_100(args.patched_tuning_best, horizon=10)

    summary = {
        "baseline_frontier_flagged_top100_h5": float((baseline_frontier[(baseline_frontier["horizon"] == 5) & (baseline_frontier["surface_rank"] <= 100)]["surface_flagged"] > 0).mean()),
        "patched_frontier_flagged_top100_h5": float((patched_frontier[(patched_frontier["horizon"] == 5) & (patched_frontier["surface_rank"] <= 100)]["surface_flagged"] > 0).mean()),
        "baseline_frontier_flagged_top100_h10": float((baseline_frontier[(baseline_frontier["horizon"] == 10) & (baseline_frontier["surface_rank"] <= 100)]["surface_flagged"] > 0).mean()),
        "patched_frontier_flagged_top100_h10": float((patched_frontier[(patched_frontier["horizon"] == 10) & (patched_frontier["surface_rank"] <= 100)]["surface_flagged"] > 0).mean()),
        "baseline_noisy_string_hits": _count_noisy_strings(baseline_shortlist),
        "patched_noisy_string_hits": _count_noisy_strings(patched_shortlist),
        "baseline_env_share_h5_shortlist": float(baseline_env.get("h5_shortlist_top100", 0.0)),
        "patched_env_share_h5_shortlist": float(patched_env.get("h5_shortlist_top100", 0.0)),
        "baseline_env_share_h10_shortlist": float(baseline_env.get("h10_shortlist_top100", 0.0)),
        "patched_env_share_h10_shortlist": float(patched_env.get("h10_shortlist_top100", 0.0)),
        "baseline_poorly_labeled_h5": int(baseline_poor.get(5, 0)),
        "patched_poorly_labeled_h5": int(patched_poor.get(5, 0)),
        "baseline_poorly_labeled_h10": int(baseline_poor.get(10, 0)),
        "patched_poorly_labeled_h10": int(patched_poor.get(10, 0)),
        "baseline_container_hits_top20_h5": int(baseline_containers.get(5, 0)),
        "patched_container_hits_top20_h5": int(patched_containers.get(5, 0)),
        "baseline_container_hits_top20_h10": int(baseline_containers.get(10, 0)),
        "patched_container_hits_top20_h10": int(patched_containers.get(10, 0)),
        "baseline_top_target_share_h5": float(baseline_target_share.get(5, 0.0)),
        "patched_top_target_share_h5": float(patched_target_share.get(5, 0.0)),
        "baseline_top_target_share_h10": float(baseline_target_share.get(10, 0.0)),
        "patched_top_target_share_h10": float(patched_target_share.get(10, 0.0)),
        "baseline_recall_at_100_h10": baseline_recall_h10,
        "patched_recall_at_100_h10": patched_recall_h10,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    acceptance_checks = [
        (
            "no new container endpoints in top-20 current shortlist",
            int(summary["patched_container_hits_top20_h5"]) == 0 and int(summary["patched_container_hits_top20_h10"]) == 0,
        ),
        (
            "poorly labeled fallback rows stay <= 2 per horizon",
            int(summary["patched_poorly_labeled_h5"]) <= 2 and int(summary["patched_poorly_labeled_h10"]) <= 2,
        ),
        (
            "noisy targeted label hits stay at 0",
            int(summary["patched_noisy_string_hits"]) == 0,
        ),
    ]
    if baseline_recall_h10 is not None and patched_recall_h10 is not None:
        acceptance_checks.append(
            (
                "Recall@100 at h=10 does not fall by more than 0.002 absolute",
                float(patched_recall_h10) >= float(baseline_recall_h10) - 0.002,
            )
        )
    acceptance_checks.append(
        (
            "top-endpoint share does not increase by more than 0.02 absolute at h=5",
            float(summary["patched_top_target_share_h5"]) <= float(summary["baseline_top_target_share_h5"]) + 0.02,
        )
    )
    acceptance_checks.append(
        (
            "top-endpoint share does not increase by more than 0.02 absolute at h=10",
            float(summary["patched_top_target_share_h10"]) <= float(summary["baseline_top_target_share_h10"]) + 0.02,
        )
    )

    lines = [
        "# Targeted Ontology Patch Comparison",
        "",
        "This note compares the baseline current-frontier artifacts against the narrow local ontology patch.",
        "",
        "## Readability / label cleanup",
        f"- Noisy targeted label hits in shortlist text: `{summary['baseline_noisy_string_hits']}` -> `{summary['patched_noisy_string_hits']}`",
        f"- Flagged share in h=5 surfaced frontier top 100: `{summary['baseline_frontier_flagged_top100_h5']:.3f}` -> `{summary['patched_frontier_flagged_top100_h5']:.3f}`",
        f"- Flagged share in h=10 surfaced frontier top 100: `{summary['baseline_frontier_flagged_top100_h10']:.3f}` -> `{summary['patched_frontier_flagged_top100_h10']:.3f}`",
        "",
        "## Concentration",
        f"- Environment/climate share in h=5 cleaned shortlist top 100: `{summary['baseline_env_share_h5_shortlist']:.3f}` -> `{summary['patched_env_share_h5_shortlist']:.3f}`",
        f"- Environment/climate share in h=10 cleaned shortlist top 100: `{summary['baseline_env_share_h10_shortlist']:.3f}` -> `{summary['patched_env_share_h10_shortlist']:.3f}`",
        "",
        "## Acceptance gate",
    ]
    for label, passed in acceptance_checks:
        lines.append(f"- {'PASS' if passed else 'FAIL'} | {label}")
    lines.extend(
        [
            "",
            "## Additional diagnostics",
            f"- Poorly labeled rows h=5: `{summary['baseline_poorly_labeled_h5']}` -> `{summary['patched_poorly_labeled_h5']}`",
            f"- Poorly labeled rows h=10: `{summary['baseline_poorly_labeled_h10']}` -> `{summary['patched_poorly_labeled_h10']}`",
            f"- Container hits in top-20 h=5: `{summary['baseline_container_hits_top20_h5']}` -> `{summary['patched_container_hits_top20_h5']}`",
            f"- Container hits in top-20 h=10: `{summary['baseline_container_hits_top20_h10']}` -> `{summary['patched_container_hits_top20_h10']}`",
            f"- Top target share in surfaced frontier top 100 h=5: `{summary['baseline_top_target_share_h5']:.3f}` -> `{summary['patched_top_target_share_h5']:.3f}`",
            f"- Top target share in surfaced frontier top 100 h=10: `{summary['baseline_top_target_share_h10']:.3f}` -> `{summary['patched_top_target_share_h10']:.3f}`",
        ]
    )
    if baseline_recall_h10 is not None and patched_recall_h10 is not None:
        lines.append(f"- Recall@100 at h=10: `{baseline_recall_h10:.4f}` -> `{patched_recall_h10:.4f}`")
    lines.extend(
        [
            "",
        "## Top h=5 shortlist titles after patch",
        ]
    )
    for title in _top_titles(patched_shortlist, horizon=5, top_n=10):
        lines.append(f"- {title}")
    lines.extend(["", "## Top h=10 shortlist titles after patch"])
    for title in _top_titles(patched_shortlist, horizon=10, top_n=10):
        lines.append(f"- {title}")
    (out_dir / "targeted_ontology_patch_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote: {out_dir / 'targeted_ontology_patch_comparison.md'}")


if __name__ == "__main__":
    main()
