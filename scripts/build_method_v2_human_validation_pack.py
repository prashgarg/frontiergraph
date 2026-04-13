from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Iterable

import pandas as pd


MAIN_RATING_COLUMNS = [
    "plausibility_1to5",
    "usefulness_1to5",
    "specificity_1to5",
    "readability_1to5",
    "attention_worthiness_1to5",
]

WORDING_RATING_COLUMNS = [
    "plausibility_1to5",
    "mechanism_clarity_1to5",
    "actionability_1to5",
    "readability_1to5",
    "attention_worthiness_1to5",
]

EXCLUDED_HUMAN_VALIDATION_LABELS = {
    "Fit model",
    "Alternative model",
    "proposed technology",
    "Conceptual framework",
}

DESIGN_OR_EVIDENCE_TOKENS = {
    "experiment",
    "survey",
    "regression",
    "granger",
    "simulation",
    "instrumental variable",
    "event study",
    "difference-in-differences",
    "did",
    "rdd",
    "laboratory",
}

GENERIC_MEDIATOR_LABELS = {
    "Improvement",
    "Equilibrium",
    "Coordination of Information on the Environment",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build blinded human-validation materials for the refreshed method-v2 frontier."
    )
    parser.add_argument(
        "--frontier-csv",
        default="outputs/paper/78_current_reranked_frontier_path_to_direct/current_reranked_frontier.csv",
        dest="frontier_csv",
    )
    parser.add_argument(
        "--out",
        default="outputs/paper/79_method_v2_human_validation_pack",
        dest="out_dir",
    )
    parser.add_argument(
        "--note",
        default="next_steps/method_v2_human_validation_note.md",
        dest="note_path",
    )
    parser.add_argument("--horizons", default="5,10,15")
    parser.add_argument("--items-per-horizon", type=int, default=4, dest="items_per_horizon")
    parser.add_argument("--max-target-repeat", type=int, default=2, dest="max_target_repeat")
    parser.add_argument("--max-source-repeat", type=int, default=2, dest="max_source_repeat")
    parser.add_argument("--wording-items", type=int, default=12, dest="wording_items")
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


def _prompt_label(value: object) -> str:
    text = _clean_string(value)
    return text.rstrip(".").strip()


def _prepare_frontier(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
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
    bad = df["source_label"].isin(EXCLUDED_HUMAN_VALIDATION_LABELS) | df["target_label"].isin(EXCLUDED_HUMAN_VALIDATION_LABELS)
    df = df[~bad].copy()
    return df


def _dedupe_within_horizon(df: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "surface_rank",
        "reranker_rank",
        "transparent_rank",
        "support_degree_product",
    ]
    sort_cols = [c for c in keep_cols if c in df.columns]
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


def _neutral_prompt(source: str, target: str, mediator: str) -> str:
    source = _prompt_label(source)
    target = _prompt_label(target)
    mediator = _prompt_label(mediator)
    mediator_kind = _mediator_kind(mediator)
    if mediator:
        if mediator_kind == "design":
            return f"Would {mediator} be a useful way to study how {source} relates to {target}?"
        if mediator_kind == "generic":
            return f"What mechanism might link {source} to {target}?"
        return f"Could {mediator} be one mechanism linking {source} to {target}?"
    return f"What nearby mechanism might link {source} to {target}?"


def _raw_anchor_prompt(source: str, target: str) -> str:
    source = _prompt_label(source)
    target = _prompt_label(target)
    return f"Should researchers study how {source} relates to {target}?"


def _mechanism_prompt(source: str, target: str, mediator: str) -> str:
    source = _prompt_label(source)
    target = _prompt_label(target)
    mediator = _prompt_label(mediator)
    mediator_kind = _mediator_kind(mediator)
    if mediator:
        if mediator_kind == "design":
            return f"Would {mediator} be a useful design for studying how {source} relates to {target}?"
        if mediator_kind == "generic":
            return f"What mechanism might link {source} to {target}?"
        return f"Could {mediator} be one mechanism linking {source} to {target}?"
    return f"What mechanism might link {source} to {target}?"


def _mediator_kind(mediator: str) -> str:
    text = _clean_string(mediator)
    if not text:
        return "none"
    if text in GENERIC_MEDIATOR_LABELS:
        return "generic"
    lowered = text.lower()
    if any(tok in lowered for tok in DESIGN_OR_EVIDENCE_TOKENS):
        return "design"
    return "mechanism"


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


def _build_main_pack(
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

    def _rows(df: pd.DataFrame, group_name: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row in df.itertuples(index=False):
            source = str(row.source_label)
            target = str(row.target_label)
            mediator = _clean_string(getattr(row, "focal_mediator_label", ""))
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
                    "prompt_text": _neutral_prompt(source, target, mediator),
                }
            )
        return rows

    return pd.DataFrame(_rows(graph_sel, "graph_selected") + _rows(pref_sel, "pref_attach_selected"))


def _build_wording_pack(main_pack: pd.DataFrame, wording_items: int) -> pd.DataFrame:
    graph_only = main_pack[main_pack["comparison_group"] == "graph_selected"].copy().head(wording_items)
    rows: list[dict[str, object]] = []
    for row in graph_only.itertuples(index=False):
        source = str(row.source_label)
        target = str(row.target_label)
        mediator = _clean_string(getattr(row, "focal_mediator_label", ""))
        common = {
            "selection_horizon": int(row.selection_horizon),
            "pair_key": str(row.pair_key),
            "source_label": source,
            "target_label": target,
            "focal_mediator_label": mediator,
        }
        rows.append(
            {
                **common,
                "comparison_group": "raw_anchor_wording",
                "prompt_text": _raw_anchor_prompt(source, target),
            }
        )
        rows.append(
            {
                **common,
                "comparison_group": "mechanism_wording",
                "prompt_text": _mechanism_prompt(source, target, mediator),
            }
        )
    return pd.DataFrame(rows)


def _write_blinded_materials(
    pack_df: pd.DataFrame,
    out_dir: Path,
    key_filename: str,
    blinded_filename: str,
    instructions_filename: str,
    rating_columns: list[str],
    seed: int,
    intro_lines: list[str],
) -> dict[str, int]:
    grouped = {str(name): sub.reset_index(drop=True) for name, sub in pack_df.groupby("comparison_group", sort=True)}
    ordered = _interleave_groups(grouped, seed=seed).reset_index(drop=True)
    ordered["item_id"] = [f"HV{idx:03d}" for idx in range(1, len(ordered) + 1)]

    key_cols = [c for c in ordered.columns if c != "prompt_text"] + ["prompt_text"]
    ordered[key_cols].to_csv(out_dir / key_filename, index=False)

    sheet_cols = ["item_id", "prompt_text"] + rating_columns + ["notes"]
    sheet_df = ordered[["item_id", "prompt_text"]].copy()
    for col in rating_columns + ["notes"]:
        sheet_df[col] = pd.NA
    sheet_df.to_csv(out_dir / blinded_filename, index=False)

    (out_dir / instructions_filename).write_text("\n".join(intro_lines) + "\n", encoding="utf-8")
    return {k: int(len(v)) for k, v in grouped.items()}


def main() -> None:
    args = parse_args()
    out_dir = _ensure_dir(args.out_dir)
    horizons = _parse_horizons(args.horizons)
    frontier = _prepare_frontier(args.frontier_csv)

    main_pack = _build_main_pack(
        frontier,
        horizons=horizons,
        items_per_horizon=int(args.items_per_horizon),
        max_target_repeat=int(args.max_target_repeat),
        max_source_repeat=int(args.max_source_repeat),
    )
    if main_pack.empty:
        raise SystemExit("Human-validation pack is empty after selection.")
    main_pack.to_csv(out_dir / "human_validation_pack.csv", index=False)

    wording_pack = _build_wording_pack(main_pack, wording_items=int(args.wording_items))
    wording_pack.to_csv(out_dir / "wording_validation_pack.csv", index=False)

    main_counts = _write_blinded_materials(
        main_pack,
        out_dir=out_dir,
        key_filename="human_validation_key.csv",
        blinded_filename="human_validation_blinded_sheet.csv",
        instructions_filename="instructions.md",
        rating_columns=MAIN_RATING_COLUMNS,
        seed=int(args.seed),
        intro_lines=[
            "# Human Validation Instructions",
            "",
            "Each row is a candidate research question drawn from the refreshed method-v2 frontier.",
            "",
            "Please rate each question on a 1 to 5 scale:",
            "",
            "- `plausibility_1to5`: could this support a real economics paper?",
            "- `usefulness_1to5`: how useful would it be to inspect under limited reading time?",
            "- `specificity_1to5`: does the question feel concrete rather than generic?",
            "- `readability_1to5`: how easy is it to understand quickly?",
            "- `attention_worthiness_1to5`: overall, how worth your attention does it seem?",
            "",
            "Use `notes` for anything especially strong, weak, redundant, or confusing.",
            "",
            "The sheet is intentionally blinded: it does not reveal whether a row came from the graph-selected or preferential-attachment-selected set.",
        ],
    )
    wording_counts = _write_blinded_materials(
        wording_pack,
        out_dir=out_dir,
        key_filename="wording_validation_key.csv",
        blinded_filename="wording_validation_blinded_sheet.csv",
        instructions_filename="wording_instructions.md",
        rating_columns=WORDING_RATING_COLUMNS,
        seed=int(args.seed) + 17,
        intro_lines=[
            "# Wording Validation Instructions",
            "",
            "Each row is one wording of the same underlying candidate relation.",
            "",
            "Please rate each wording on a 1 to 5 scale:",
            "",
            "- `plausibility_1to5`: does the wording still describe a plausible paper question?",
            "- `mechanism_clarity_1to5`: does the wording make the mechanism or path intuition clear?",
            "- `actionability_1to5`: does the wording make it easier to imagine a next empirical step?",
            "- `readability_1to5`: how easy is it to understand quickly?",
            "- `attention_worthiness_1to5`: overall, how worth your attention does it seem?",
            "",
            "Use `notes` for anything especially strong, weak, awkward, or repetitive.",
            "",
            "This sheet is also blinded: it does not reveal whether an item uses raw-anchor wording or mechanism wording.",
        ],
    )

    summary = {
        "main_pack_rows": int(len(main_pack)),
        "main_pack_groups": main_counts,
        "wording_pack_rows": int(len(wording_pack)),
        "wording_pack_groups": wording_counts,
        "horizons": horizons,
        "items_per_horizon": int(args.items_per_horizon),
        "max_target_repeat": int(args.max_target_repeat),
        "max_source_repeat": int(args.max_source_repeat),
        "seed": int(args.seed),
        "frontier_csv": str(args.frontier_csv),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    note_lines = [
        "# Method-v2 Human Validation Note",
        "",
        "## Status",
        "",
        "This pass prepares the refreshed next-day rating materials. It does not claim completed ratings.",
        "",
        "## Main blinded pack",
        "",
        f"- total rows: `{len(main_pack)}`",
        f"- graph-selected rows: `{main_counts.get('graph_selected', 0)}`",
        f"- preferential-attachment-selected rows: `{main_counts.get('pref_attach_selected', 0)}`",
        f"- horizons covered: `{', '.join(str(h) for h in horizons)}`",
        f"- target repeat cap per arm: `{args.max_target_repeat}`",
        f"- source repeat cap per arm: `{args.max_source_repeat}`",
        "",
        "The main pack is balanced across horizons and de-duplicated across pairs so the comparison does not collapse into one crowded endpoint neighborhood.",
        "",
        "Obvious paper-facing label artifacts such as `Fit model`, `Alternative model`, and `proposed technology` are excluded so raters are judging candidate quality rather than ontology cleanup.",
        "",
        "## Wording comparison pack",
        "",
        f"- total rows: `{len(wording_pack)}`",
        f"- underlying graph-selected items: `{len(wording_pack) // 2}`",
        "",
        "This smaller pack compares raw-anchor wording against mechanism/path wording on the same underlying candidate pairs.",
        "",
        "## Files",
        "",
        "- `human_validation_pack.csv`",
        "- `human_validation_blinded_sheet.csv`",
        "- `human_validation_key.csv`",
        "- `instructions.md`",
        "- `wording_validation_pack.csv`",
        "- `wording_validation_blinded_sheet.csv`",
        "- `wording_validation_key.csv`",
        "- `wording_instructions.md`",
        "",
        "## Intended paper use",
        "",
        "The paper can describe this as a prepared blinded validation protocol comparing graph-selected items with preferential-attachment-selected items, plus a smaller wording audit that tests whether mechanism-rich phrasing improves readability and actionability.",
    ]
    Path(args.note_path).write_text("\n".join(note_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
