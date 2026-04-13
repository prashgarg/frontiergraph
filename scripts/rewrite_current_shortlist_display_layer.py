from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_INPUT = "outputs/paper/27_ontology_vnext_proto_review/enriched_shortlist.csv"
DEFAULT_OUT = "outputs/paper/23_current_path_mediator_shortlist_patch_v1_labels_generic"
CURRENT_SHORTLIST_COLUMNS = [
    "pair_key",
    "horizon",
    "surface_rank",
    "reranker_rank",
    "transparent_rank",
    "source_label",
    "target_label",
    "source_family",
    "target_family",
    "semantic_family_key",
    "source_theme",
    "target_theme",
    "theme_pair_key",
    "route_family",
    "display_title",
    "display_why",
    "display_first_step",
    "primary_mediator_labels",
    "primary_mediator_codes",
    "baseline_direct_title",
    "surface_penalty",
    "surface_flagged",
    "rank_delta",
    "reranker_score",
    "transparent_score",
    "mediator_count",
    "supporting_path_count",
    "top_mediators_json",
    "top_paths_json",
    "shortlist_rank",
    "shortlist_penalty",
    "theme_penalty",
    "source_family_seen_before",
    "target_family_seen_before",
    "family_seen_before",
    "source_theme_seen_before",
    "target_theme_seen_before",
    "theme_pair_seen_before",
]

PATH_TITLE_TEMPLATE = "What nearby pathways could connect {source} to {target}?"
MEDIATOR_TITLE_TEMPLATE = "Which mechanisms most plausibly connect {source} to {target}?"
DIRECT_TITLE_TEMPLATE = "How might {source} change {target}?"

PROMOTE_PATH_FIRST_STEP = "Start with a short review of the nearest mediating topics, then test which pathway looks most credible."
PROMOTE_MEDIATOR_FIRST_STEP = "Start by testing which candidate mechanism carries the relation."
KEEP_DIRECT_FIRST_STEP = "A direct empirical test looks like the natural next step."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rewrite current shortlist display text without changing row composition.")
    parser.add_argument("--input-csv", default=DEFAULT_INPUT, dest="input_csv")
    parser.add_argument("--out-dir", default=DEFAULT_OUT, dest="out_dir")
    return parser.parse_args()


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text or text in {"[]", "{}", "nan", "None"}:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def _list_phrase(items: list[str]) -> str:
    items = [str(item).strip() for item in items if str(item).strip()]
    if not items:
        return "the nearest available mediators"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{items[0]}, {items[1]}, and {items[2]}"


def _rewrite_row(row: pd.Series) -> pd.Series:
    source = str(row.get("source_label", "") or "")
    target = str(row.get("target_label", "") or "")
    mediators = _as_list(row.get("primary_mediator_labels"))
    route_family = str(row.get("route_family", "") or "")
    if route_family == "path_question":
        row["display_title"] = PATH_TITLE_TEMPLATE.format(source=source, target=target)
        row["display_why"] = (
            f"Nearby work points to {_list_phrase(mediators)} as plausible connecting pathways."
            if mediators
            else "Nearby work points to several plausible connecting pathways, but the nearest mediators are still poorly labeled."
        )
        row["display_first_step"] = PROMOTE_PATH_FIRST_STEP
    elif route_family == "mediator_question":
        row["display_title"] = MEDIATOR_TITLE_TEMPLATE.format(source=source, target=target)
        row["display_why"] = (
            f"The leading candidate mechanisms are {_list_phrase(mediators)}."
            if mediators
            else "The leading candidate mechanisms are still poorly labeled."
        )
        row["display_first_step"] = PROMOTE_MEDIATOR_FIRST_STEP
    else:
        row["display_title"] = DIRECT_TITLE_TEMPLATE.format(source=source, target=target)
        row["display_first_step"] = KEEP_DIRECT_FIRST_STEP
    return row


def _write_review_note(df: pd.DataFrame, out_path: Path) -> None:
    route_counts = df["route_family"].value_counts().to_dict()
    total = max(len(df), 1)
    lines = [
        "# Current Path/Mediator Shortlist",
        "",
        "This note rewrites the active shortlist display layer while keeping the shortlist rows fixed.",
        "",
        "## Route counts",
        "",
    ]
    for route in ["path_question", "mediator_question", "direct_edge_question"]:
        count = int(route_counts.get(route, 0))
        lines.append(f"- `{route}`: {count} ({count / total:.1%})")
    for horizon in sorted(df["horizon"].dropna().astype(int).unique().tolist()):
        lines.extend(["", f"## Horizon {horizon}", ""])
        for row in df[df["horizon"].astype(int).eq(horizon)].head(15).itertuples(index=False):
            lines.append(
                f"- `#{int(row.shortlist_rank)}` `{row.route_family}` | {row.display_title}  \n"
                f"  Before: {row.baseline_direct_title}  \n"
                f"  Original surface rank: {int(row.surface_rank)}; shortlist penalty: {int(row.shortlist_penalty)}  \n"
                f"  Why: {row.display_why}  \n"
                f"  First step: {row.display_first_step}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input_csv)
    shortlist_df = df[CURRENT_SHORTLIST_COLUMNS].copy()
    shortlist_df = shortlist_df.apply(_rewrite_row, axis=1)
    shortlist_df = shortlist_df.sort_values(["horizon", "shortlist_rank"], ascending=[True, True]).reset_index(drop=True)

    shortlist_df.to_csv(out_dir / "current_path_mediator_shortlist.csv", index=False)
    with (out_dir / "current_path_mediator_shortlist.jsonl").open("w", encoding="utf-8") as handle:
        for row in shortlist_df.to_dict(orient="records"):
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    route_summary = (
        shortlist_df.groupby(["horizon", "route_family"], as_index=False)
        .agg(count=("pair_key", "size"))
        .sort_values(["horizon", "count"], ascending=[True, False])
        .reset_index(drop=True)
    )
    route_summary.to_csv(out_dir / "route_summary.csv", index=False)
    _write_review_note(shortlist_df, out_dir / "current_path_mediator_shortlist.md")
    manifest = {
        "source_input_csv": args.input_csv,
        "n_rows": int(len(shortlist_df)),
        "rewrite_only": True,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote rewritten shortlist display layer to {out_dir}")


if __name__ == "__main__":
    main()
