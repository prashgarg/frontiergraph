from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_ROUTED = "outputs/paper/30_vnext_routed_shortlist/routed_shortlist.csv"
DEFAULT_OUT = "outputs/paper/35_surfaced_shortlist_quality_review"

GENERIC_ENDPOINT_LABELS = {
    "policy",
    "distance",
    "economic growth",
    "innovation",
    "employment",
    "wages",
    "health",
    "income",
    "consumption",
    "productivity",
    "investment",
    "output",
    "rate of growth",
}
GENERIC_ENDPOINT_PATTERNS = [
    r"\bpolicy variables\b",
    r"\bmodel parameters\b",
    r"\bparameters\b",
    r"\bmodels\b",
]
BOUNDARY_LABELS = {"policy", "mitigation"}
CODE_RE = re.compile(r"^FG3C\d+$")
GENERIC_REGEX = [re.compile(pattern, flags=re.IGNORECASE) for pattern in GENERIC_ENDPOINT_PATTERNS]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a surfaced shortlist quality review pack.")
    parser.add_argument("--routed-shortlist", default=DEFAULT_ROUTED, dest="routed_shortlist")
    parser.add_argument("--out-dir", default=DEFAULT_OUT, dest="out_dir")
    return parser.parse_args()


def _normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_generic_endpoint(label: Any) -> bool:
    norm = _normalize_label(label)
    if not norm:
        return True
    if norm in GENERIC_ENDPOINT_LABELS:
        return True
    return any(pattern.search(norm) for pattern in GENERIC_REGEX)


def _active_text(row: pd.Series) -> tuple[str, str, str]:
    if bool(row.get("routed_changed", False)):
        return (
            str(row.get("routed_title", "") or ""),
            str(row.get("routed_why", "") or ""),
            str(row.get("routed_first_step", "") or ""),
        )
    return (
        str(row.get("display_title", "") or ""),
        str(row.get("display_why", "") or ""),
        str(row.get("display_first_step", "") or ""),
    )


def _rewrite_text(row: pd.Series, issue_tags: set[str]) -> tuple[str, str, str]:
    active_title, active_why, active_first_step = _active_text(row)
    source = str(row.get("source_label", "") or "")
    target = str(row.get("target_label", "") or "")
    if "awkward_path_phrase" not in issue_tags:
        if "route_back_to_baseline" in issue_tags:
            return (
                str(row.get("display_title", "") or ""),
                str(row.get("display_why", "") or ""),
                str(row.get("display_first_step", "") or ""),
            )
        return "", "", ""
    if active_title.startswith("Through which nearby pathways might "):
        return (
            f"What nearby pathways could connect {source} to {target}?",
            re.sub(r"^Nearby papers already suggest routes through ", "Nearby work points to ", active_why).rstrip(".") + " as plausible connecting pathways.",
            "Start with a short review of the nearest mediating topics, then test which pathway looks most credible.",
        )
    if active_title.startswith("Which nearby mechanisms most plausibly link "):
        return (
            f"Which mechanisms most plausibly connect {source} to {target}?",
            re.sub(r"^The main open question is which channel does the work: ", "The leading candidate mechanisms are ", active_why).rstrip(".") + ".",
            "Start by testing which candidate mechanism carries the relation.",
        )
    return "", "", ""


def _markdown_grouped(df: pd.DataFrame) -> str:
    lines = ["# Surfaced Shortlist Quality Review", ""]
    for action, sub in df.groupby("quality_action", sort=False):
        lines.append(f"## `{action}`")
        lines.append("")
        for row in sub.itertuples(index=False):
            lines.append(
                f"- `#{int(row.review_rank)}` `{row.source_label} -> {row.target_label}` | route `{row.active_route_family}` | tags `{row.issue_tags or 'none'}`"
            )
            lines.append(f"  Current: {row.active_title}")
            if row.rewritten_display_title:
                lines.append(f"  Rewrite: {row.rewritten_display_title}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    routed_df = pd.read_csv(args.routed_shortlist)
    routed_df = routed_df.sort_values(["surface_rank", "horizon", "reranker_rank"], ascending=[True, True, True]).reset_index(drop=True)
    unique_df = routed_df.drop_duplicates("pair_key", keep="first").head(50).reset_index(drop=True)
    unique_df["review_rank"] = range(1, len(unique_df) + 1)
    active_text = unique_df.apply(_active_text, axis=1)
    unique_df["active_title"] = active_text.map(lambda item: item[0])
    unique_df["active_why"] = active_text.map(lambda item: item[1])
    unique_df["active_first_step"] = active_text.map(lambda item: item[2])
    unique_df["active_route_family"] = unique_df["routed_object_family"].fillna("baseline").astype(str)

    semantic_counts = unique_df["semantic_family_key"].astype(str).value_counts().to_dict()
    source_counts = unique_df["source_label"].astype(str).value_counts().to_dict()
    target_counts = unique_df["target_label"].astype(str).value_counts().to_dict()
    seen_semantic: dict[str, int] = {}

    issue_tags_all: list[list[str]] = []
    actions: list[str] = []
    rewritten_titles: list[str] = []
    rewritten_whys: list[str] = []
    rewritten_first_steps: list[str] = []

    for row in unique_df.itertuples(index=False):
        tags: set[str] = set()
        source_norm = _normalize_label(row.source_label)
        target_norm = _normalize_label(row.target_label)
        active_title = str(row.active_title)
        active_why = str(row.active_why)
        semantic_key = str(row.semantic_family_key)

        if _is_generic_endpoint(row.source_label) or _is_generic_endpoint(row.target_label):
            tags.add("generic_endpoint")
        if (
            active_title.startswith("Through which nearby pathways might ")
            or active_title.startswith("Which nearby mechanisms most plausibly link ")
            or active_why.startswith("Nearby papers already suggest routes through ")
            or active_why.startswith("The main open question is which channel does the work: ")
        ):
            tags.add("awkward_path_phrase")
        if semantic_counts.get(semantic_key, 0) > 1:
            tags.add("family_repetition")
        if seen_semantic.get(semantic_key, 0) > 0 or (
            source_counts.get(str(row.source_label), 0) > 1 and target_counts.get(str(row.target_label), 0) > 1
        ):
            tags.add("redundant_pair")
        if (
            int(row.surface_flagged) > 0
            or CODE_RE.match(str(row.source_label))
            or CODE_RE.match(str(row.target_label))
            or source_norm in BOUNDARY_LABELS
            or target_norm in BOUNDARY_LABELS
            or any(term in str(row.route_suppression_reason) for term in ["generic", "boundary"])
        ):
            tags.add("boundary_leak")
        seen_semantic[semantic_key] = seen_semantic.get(semantic_key, 0) + 1

        if "boundary_leak" in tags or "redundant_pair" in tags:
            action = "drop_or_merge"
        elif "generic_endpoint" in tags and bool(row.routed_changed):
            action = "route_back_to_baseline"
            tags.add("route_back_to_baseline")
        elif "awkward_path_phrase" in tags:
            action = "light_rewrite"
        else:
            action = "keep"

        rewritten_title, rewritten_why, rewritten_first_step = _rewrite_text(pd.Series(row._asdict()), tags)
        issue_tags_all.append(sorted(tags))
        actions.append(action)
        rewritten_titles.append(rewritten_title)
        rewritten_whys.append(rewritten_why)
        rewritten_first_steps.append(rewritten_first_step)

    unique_df["quality_action"] = actions
    unique_df["issue_tags"] = [",".join(tags) for tags in issue_tags_all]
    unique_df["rewritten_display_title"] = rewritten_titles
    unique_df["rewritten_display_why"] = rewritten_whys
    unique_df["rewritten_display_first_step"] = rewritten_first_steps

    issue_counts: dict[str, int] = {}
    kept_issue_counts: dict[str, int] = {}
    for action, tags in zip(actions, issue_tags_all):
        for tag in tags:
            issue_counts[tag] = issue_counts.get(tag, 0) + 1
            if action in {"keep", "light_rewrite"}:
                kept_issue_counts[tag] = kept_issue_counts.get(tag, 0) + 1

    out_csv = out_dir / "top50_unique_shortlist_quality_review.csv"
    out_md = out_dir / "top50_unique_shortlist_quality_review.md"
    summary_json = out_dir / "summary.json"

    unique_df.to_csv(out_csv, index=False)
    out_md.write_text(_markdown_grouped(unique_df), encoding="utf-8")
    summary = {
        "top_unique_rows": int(len(unique_df)),
        "quality_action_counts": unique_df["quality_action"].value_counts().sort_index().to_dict(),
        "issue_tag_counts": issue_counts,
        "kept_issue_tag_counts": kept_issue_counts,
        "systematic_display_issue_tags": sorted(
            tag
            for tag, count in kept_issue_counts.items()
            if tag == "awkward_path_phrase" and count >= 3
        ),
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote surfaced shortlist quality review outputs to {out_dir}")


if __name__ == "__main__":
    main()
