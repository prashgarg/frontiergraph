from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_SHORTLIST_REVIEW = "outputs/paper/35_surfaced_shortlist_quality_review/top50_unique_shortlist_quality_review.csv"
DEFAULT_FAMILY_PROTOTYPES = "outputs/paper/28_vnext_frontier_question_prototypes/frontier_question_prototypes.csv"
DEFAULT_OUT = "outputs/paper/36_paper_curated_examples"

EXAMPLE_SPECS = [
    {
        "example_role": "baseline_surfaced_object",
        "source_label": "price changes",
        "target_label": "CO2 emissions",
        "selection_note": "Readable baseline path-rich object that survives the top-50 quality pass without needing a routed overlay.",
    },
    {
        "example_role": "context_transfer_overlay",
        "source_label": "financial development",
        "target_label": "green innovation",
        "selection_note": "Best current context-transfer example because the routed wording clearly improves the question.",
    },
    {
        "example_role": "evidence_type_expansion_overlay",
        "source_label": "willingness to pay",
        "target_label": "CO2 emissions",
        "selection_note": "Best current evidence-type-expansion example even though it sits in a crowded CO2-centered region.",
    },
    {
        "example_role": "family_aware_extension",
        "source_label": "state of the business cycle",
        "target_label": "house prices",
        "selection_note": "Strongest compact family-aware comparison example; keep it as an extension object rather than the main surfaced object.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the paper-facing curated example pack.")
    parser.add_argument("--shortlist-review", default=DEFAULT_SHORTLIST_REVIEW, dest="shortlist_review")
    parser.add_argument("--family-prototypes", default=DEFAULT_FAMILY_PROTOTYPES, dest="family_prototypes")
    parser.add_argument("--out-dir", default=DEFAULT_OUT, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    shortlist_df = pd.read_csv(args.shortlist_review)
    family_df = pd.read_csv(args.family_prototypes)
    family_df = family_df[family_df["prototype_family"].astype(str).eq("family_aware")].drop_duplicates("pair_key", keep="first")

    rows = []
    for spec in EXAMPLE_SPECS:
        source = spec["source_label"]
        target = spec["target_label"]
        if spec["example_role"] == "family_aware_extension":
            sub = family_df[(family_df["source_label"] == source) & (family_df["target_label"] == target)].copy()
            if sub.empty:
                continue
            row = sub.iloc[0]
            rows.append(
                {
                    "example_role": spec["example_role"],
                    "pair_key": row["pair_key"],
                    "source_label": source,
                    "target_label": target,
                    "surface_family": "family_aware_extension",
                    "display_title": row["prototype_title"],
                    "display_why": row["prototype_why"],
                    "display_first_step": row["prototype_first_step"],
                    "quality_action": "extension_only",
                    "selection_note": spec["selection_note"],
                }
            )
            continue
        sub = shortlist_df[(shortlist_df["source_label"] == source) & (shortlist_df["target_label"] == target)].copy()
        if sub.empty:
            continue
        row = sub.iloc[0]
        rows.append(
            {
                "example_role": spec["example_role"],
                "pair_key": row["pair_key"],
                "source_label": source,
                "target_label": target,
                "surface_family": row["active_route_family"],
                "display_title": row["active_title"],
                "display_why": row["active_why"],
                "display_first_step": row["active_first_step"],
                "quality_action": row["quality_action"],
                "selection_note": spec["selection_note"],
            }
        )

    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_dir / "curated_examples.csv", index=False)

    lines = ["# Paper Curated Example Pack", ""]
    for row in out_df.itertuples(index=False):
        lines.append(f"## `{row.example_role}`")
        lines.append("")
        lines.append(f"- Pair: `{row.source_label} -> {row.target_label}`")
        lines.append(f"- Surface family: `{row.surface_family}`")
        lines.append(f"- Current display: `{row.display_title}`")
        lines.append(f"- Why: {row.display_why}")
        lines.append(f"- First step: {row.display_first_step}")
        lines.append(f"- Review status: `{row.quality_action}`")
        lines.append(f"- Selection note: {row.selection_note}")
        lines.append("")
    (out_dir / "curated_examples.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    summary = {
        "example_count": int(len(out_df)),
        "roles": out_df["example_role"].tolist(),
        "surface_families": out_df["surface_family"].value_counts().sort_index().to_dict(),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote paper curated example pack to {out_dir}")


if __name__ == "__main__":
    main()
