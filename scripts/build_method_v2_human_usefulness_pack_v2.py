from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Iterable

import pandas as pd


RATING_COLUMNS = [
    "readability_1to5",
    "interpretability_1to5",
    "usefulness_1to5",
    "artifact_risk_low_medium_high",
]

EXCLUDED_LABELS = {
    "Fit model",
    "Alternative model",
    "proposed technology",
    "Conceptual framework",
}

CONSTRUCTION_NOTE = (
    "The middle node is an intervening concept from the literature graph; it may represent "
    "a mechanism, channel, condition, policy lever, or other bridge."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a human usefulness pack aligned to the appendix LLM usefulness object."
    )
    parser.add_argument(
        "--frontier-csv",
        default="outputs/paper/85_current_reranked_frontier_path_to_direct_quality_surface/current_reranked_frontier.csv",
        dest="frontier_csv",
    )
    parser.add_argument(
        "--out",
        default="outputs/paper/129_method_v2_human_usefulness_pack_v2",
        dest="out_dir",
    )
    parser.add_argument(
        "--note",
        default="next_steps/method_v2_human_usefulness_pack_v2_note.md",
        dest="note_path",
    )
    parser.add_argument("--horizons", default="5,10,15")
    parser.add_argument("--items-per-horizon", type=int, default=4, dest="items_per_horizon")
    parser.add_argument("--max-target-repeat", type=int, default=2, dest="max_target_repeat")
    parser.add_argument("--max-source-repeat", type=int, default=2, dest="max_source_repeat")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _parse_horizons(text: str) -> list[int]:
    return [int(x.strip()) for x in str(text).split(",") if x.strip()]


def _ensure_dir(path: str | Path) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _clean_string(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def _prepare_frontier(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if "surface_flagged" in df.columns:
        df = df[df["surface_flagged"].fillna(0).astype(int) == 0].copy()
    df["pair_key"] = df["u"].astype(str) + "__" + df["v"].astype(str)
    df["source_label"] = df["source_label"].fillna(df["u"].astype(str)).astype(str)
    df["target_label"] = df["target_label"].fillna(df["v"].astype(str)).astype(str)
    df["focal_mediator_label"] = df["focal_mediator_label"].map(_clean_string)
    df["candidate_subfamily"] = df["candidate_subfamily"].fillna("").astype(str)
    df["candidate_scope_bucket"] = df["candidate_scope_bucket"].fillna("").astype(str)
    df["local_topology_class"] = df["local_topology_class"].fillna("").astype(str)
    df["surface_rank"] = pd.to_numeric(df["surface_rank"], errors="coerce")
    df["support_degree_product"] = pd.to_numeric(df["support_degree_product"], errors="coerce").fillna(0.0)
    bad = df["source_label"].isin(EXCLUDED_LABELS) | df["target_label"].isin(EXCLUDED_LABELS)
    return df.loc[~bad].copy()


def _dedupe_within_horizon(df: pd.DataFrame) -> pd.DataFrame:
    sort_cols = [c for c in ["surface_rank", "reranker_rank", "transparent_rank", "support_degree_product"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, ascending=[True] * len(sort_cols))
    return df.drop_duplicates(subset=["horizon", "pair_key"], keep="first").copy()


def _select_rows(
    df: pd.DataFrame,
    horizons: Iterable[int],
    items_per_horizon: int,
    sort_cols: list[str],
    ascending: list[bool],
    excluded_pairs: set[str] | None = None,
    max_target_repeat: int = 2,
    max_source_repeat: int = 2,
) -> pd.DataFrame:
    excluded_pairs = excluded_pairs or set()
    selected_rows: list[pd.Series] = []
    target_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    seen_pairs: set[str] = set(excluded_pairs)

    for horizon in horizons:
        sub = df[df["horizon"] == horizon].sort_values(sort_cols, ascending=ascending).copy()
        picks = 0
        for row in sub.itertuples(index=False):
            pair_key = str(row.pair_key)
            source = str(row.source_label)
            target = str(row.target_label)
            if pair_key in seen_pairs:
                continue
            if target_counts.get(target, 0) >= max_target_repeat:
                continue
            if source_counts.get(source, 0) >= max_source_repeat:
                continue
            selected_rows.append(pd.Series(row._asdict()))
            seen_pairs.add(pair_key)
            target_counts[target] = target_counts.get(target, 0) + 1
            source_counts[source] = source_counts.get(source, 0) + 1
            picks += 1
            if picks >= items_per_horizon:
                break

    if not selected_rows:
        return pd.DataFrame(columns=df.columns)
    return pd.DataFrame(selected_rows).reset_index(drop=True)


def _triplet_text(source: str, mediator: str, target: str) -> str:
    source = _clean_string(source)
    mediator = _clean_string(mediator)
    target = _clean_string(target)
    if mediator:
        return f"{source} -> {mediator} -> {target}"
    return f"{source} -> {target}"


def _rows(df: pd.DataFrame, group_name: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in df.itertuples(index=False):
        source = str(row.source_label)
        target = str(row.target_label)
        mediator = _clean_string(getattr(row, "focal_mediator_label", ""))
        triplet = _triplet_text(source, mediator, target)
        rows.append(
            {
                "comparison_group": group_name,
                "selection_horizon": int(row.horizon),
                "pair_key": str(row.pair_key),
                "source_label": source,
                "target_label": target,
                "focal_mediator_label": mediator,
                "candidate_subfamily": str(getattr(row, "candidate_subfamily", "")),
                "candidate_scope_bucket": str(getattr(row, "candidate_scope_bucket", "")),
                "local_topology_class": str(getattr(row, "local_topology_class", "")),
                "graph_surface_rank": int(getattr(row, "surface_rank", 0) or 0),
                "pref_attach_score": float(getattr(row, "support_degree_product", 0.0) or 0.0),
                "candidate_triplet": triplet,
                "construction_note": CONSTRUCTION_NOTE,
            }
        )
    return rows


def _build_pack(
    frontier: pd.DataFrame,
    horizons: list[int],
    items_per_horizon: int,
    max_target_repeat: int,
    max_source_repeat: int,
) -> pd.DataFrame:
    deduped = _dedupe_within_horizon(frontier)
    graph_sel = _select_rows(
        deduped,
        horizons=horizons,
        items_per_horizon=items_per_horizon,
        sort_cols=["surface_rank", "reranker_rank", "transparent_rank"],
        ascending=[True, True, True],
        max_target_repeat=max_target_repeat,
        max_source_repeat=max_source_repeat,
    )
    pref_sel = _select_rows(
        deduped,
        horizons=horizons,
        items_per_horizon=items_per_horizon,
        sort_cols=["support_degree_product", "surface_rank"],
        ascending=[False, True],
        excluded_pairs=set(graph_sel["pair_key"].astype(str).tolist()),
        max_target_repeat=max_target_repeat,
        max_source_repeat=max_source_repeat,
    )
    return pd.DataFrame(_rows(graph_sel, "graph_selected") + _rows(pref_sel, "pref_attach_selected"))


def _interleave_groups(groups: dict[str, pd.DataFrame], seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    ordered_groups = sorted(groups)
    stacks: dict[str, list[dict[str, object]]] = {}
    for group in ordered_groups:
        rows = groups[group].to_dict("records")
        rng.shuffle(rows)
        stacks[group] = rows

    output: list[dict[str, object]] = []
    while any(stacks.values()):
        for group in ordered_groups:
            if stacks[group]:
                output.append(stacks[group].pop())
    return pd.DataFrame(output)


def main() -> None:
    args = parse_args()
    out_dir = _ensure_dir(args.out_dir)
    horizons = _parse_horizons(args.horizons)
    frontier = _prepare_frontier(args.frontier_csv)
    pack_df = _build_pack(
        frontier=frontier,
        horizons=horizons,
        items_per_horizon=int(args.items_per_horizon),
        max_target_repeat=int(args.max_target_repeat),
        max_source_repeat=int(args.max_source_repeat),
    )
    if pack_df.empty:
        raise SystemExit("Human usefulness pack is empty after selection.")

    grouped = {str(name): sub.reset_index(drop=True) for name, sub in pack_df.groupby("comparison_group", sort=True)}
    ordered = _interleave_groups(grouped, seed=int(args.seed)).reset_index(drop=True)
    ordered["item_id"] = [f"HUV{idx:03d}" for idx in range(1, len(ordered) + 1)]

    pack_df.to_csv(out_dir / "human_usefulness_pack.csv", index=False)
    key_cols = [c for c in ordered.columns if c not in {"candidate_triplet", "construction_note"}] + ["candidate_triplet", "construction_note"]
    ordered[key_cols].to_csv(out_dir / "human_usefulness_key.csv", index=False)

    sheet_df = ordered[["item_id", "candidate_triplet", "construction_note"]].copy()
    sheet_df = sheet_df.rename(columns={"candidate_triplet": "triplet"})
    for col in RATING_COLUMNS + ["notes"]:
        sheet_df[col] = pd.NA
    sheet_df.to_csv(out_dir / "human_usefulness_blinded_sheet.csv", index=False)

    instructions = [
        "# Human Usefulness Instructions",
        "",
        "Each row is a candidate research-question object from the refreshed method-v2 frontier.",
        "",
        "You should judge only the current usefulness of the displayed object.",
        "Do not try to judge novelty at the cutoff year, publication success, or whether the topic was later pursued.",
        "",
        "Displayed object:",
        "- `triplet`: the raw `A -> B -> C` relation from the literature graph",
        "- `construction_note`: the middle term is an intervening concept, not necessarily a proven mechanism",
        "",
        "Please rate:",
        "- `readability_1to5`: how easy is this object to read quickly?",
        "- `interpretability_1to5`: can you tell what relationship or bridge is being proposed?",
        "- `usefulness_1to5`: is this a usable research-question object, even if it still needs revision?",
        "- `artifact_risk_low_medium_high`: does it read like a graph artifact rather than a real research question?",
        "",
        "Use `notes` for anything especially strong, weak, awkward, or confusing.",
        "",
        "The sheet is blinded: it does not reveal whether a row came from the graph-selected or preferential-attachment-selected set.",
    ]
    (out_dir / "instructions.md").write_text("\n".join(instructions) + "\n", encoding="utf-8")

    summary = {
        "rows_total": int(len(ordered)),
        "graph_selected_rows": int((ordered["comparison_group"] == "graph_selected").sum()),
        "pref_attach_selected_rows": int((ordered["comparison_group"] == "pref_attach_selected").sum()),
        "horizons": horizons,
        "items_per_horizon": int(args.items_per_horizon),
        "max_target_repeat": int(args.max_target_repeat),
        "max_source_repeat": int(args.max_source_repeat),
        "seed": int(args.seed),
        "frontier_csv": str(args.frontier_csv),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    note_lines = [
        "# Method-v2 Human Usefulness Pack v2",
        "",
        "## Status",
        "",
        "This pass prepares a refreshed human-usefulness pack aligned to the appendix LLM usefulness object. It does not claim completed ratings.",
        "",
        "## Main blinded pack",
        "",
        f"- total rows: `{len(ordered)}`",
        f"- graph-selected rows: `{summary['graph_selected_rows']}`",
        f"- preferential-attachment-selected rows: `{summary['pref_attach_selected_rows']}`",
        f"- horizons covered: `{', '.join(str(h) for h in horizons)}`",
        f"- target repeat cap per arm: `{args.max_target_repeat}`",
        f"- source repeat cap per arm: `{args.max_source_repeat}`",
        "",
        "The rating object is now the same as in the appendix LLM usefulness pass:",
        "",
        "- raw triplet `A -> B -> C`",
        "- short construction note",
        "- ratings on readability, interpretability, usefulness, and artifact risk",
        "",
        "## Files",
        "",
        "- `human_usefulness_pack.csv`",
        "- `human_usefulness_blinded_sheet.csv`",
        "- `human_usefulness_key.csv`",
        "- `instructions.md`",
        "",
        "## Intended paper use",
        "",
        "This pack provides the external human usefulness check that matches the appendix LLM usefulness object. The comparison is graph-selected versus preferential-attachment-selected items under the same current-usefulness rubric.",
    ]
    Path(args.note_path).write_text("\n".join(note_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
