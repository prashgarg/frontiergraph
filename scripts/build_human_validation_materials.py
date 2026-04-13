from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Turn the prepared human-validation pack into blinded rating materials.")
    parser.add_argument(
        "--input-csv",
        default="outputs/paper/41_human_validation_pack/human_validation_pack.csv",
        dest="input_csv",
    )
    parser.add_argument(
        "--out",
        default="outputs/paper/44_human_validation_materials",
        dest="out_dir",
    )
    parser.add_argument(
        "--note",
        default="next_steps/human_validation_materials_note.md",
        dest="note_path",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


RATING_COLUMNS = [
    "novelty_rating",
    "plausibility_rating",
    "usefulness_rating",
    "readability_rating",
    "attention_worthiness_rating",
]


def _interleave(groups: dict[str, pd.DataFrame], seed: int) -> pd.DataFrame:
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
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input_csv)
    if df.empty:
        raise SystemExit("Human validation pack is empty.")

    grouped = {str(name): sub.reset_index(drop=True) for name, sub in df.groupby("comparison_group", sort=True)}
    ordered = _interleave(grouped, seed=int(args.seed)).reset_index(drop=True)
    ordered["item_id"] = [f"HV{idx:03d}" for idx in range(1, len(ordered) + 1)]

    key_cols = ["item_id", "comparison_group", "pair_key", "source_label", "target_label", "graph_surface_rank", "pref_attach_score", "prompt_text"]
    key_df = ordered[key_cols].copy()
    key_df.to_csv(out_dir / "human_validation_key.csv", index=False)

    sheet_cols = ["item_id", "prompt_text"] + RATING_COLUMNS + ["notes"]
    sheet_df = ordered[sheet_cols].copy()
    for col in RATING_COLUMNS + ["notes"]:
        sheet_df[col] = pd.NA
    sheet_df.to_csv(out_dir / "human_validation_blinded_sheet.csv", index=False)

    instructions = [
        "# Human Validation Instructions",
        "",
        "Each row is a candidate research question phrased in the same neutral path-oriented style.",
        "",
        "Please rate each question on a 1 to 5 scale:",
        "",
        "- `novelty_rating`: how non-obvious or fresh the question feels",
        "- `plausibility_rating`: how plausible it seems that the question could support a real economics paper",
        "- `usefulness_rating`: how useful it would be to inspect this question under limited reading time",
        "- `readability_rating`: how easy it is to understand the question quickly",
        "- `attention_worthiness_rating`: overall, how worth your attention this question seems",
        "",
        "Use `notes` for anything that seems especially strong, weak, redundant, or confusing.",
        "",
        "The sheet is intentionally blinded: it does not reveal whether a row came from the graph-selected or preferential-attachment-selected set.",
    ]
    (out_dir / "instructions.md").write_text("\n".join(instructions) + "\n", encoding="utf-8")

    summary = {
        "rows": int(len(ordered)),
        "comparison_groups": {key: int(len(val)) for key, val in grouped.items()},
        "blinded": True,
        "interleaved": True,
        "seed": int(args.seed),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    note_lines = [
        "# Human Validation Materials Note",
        "",
        "## What changed",
        "",
        "- the original 24-row pack is now randomized and blinded",
        "- a clean rating sheet is ready for raters",
        "- the answer key is separated from the sheet",
        "- the scoring rubric is written down in one place",
        "",
        "## Pack contents",
        "",
        "- `human_validation_blinded_sheet.csv`",
        "- `human_validation_key.csv`",
        "- `instructions.md`",
        "",
        "## Use",
        "",
        "This pack is ready for next-day economist ratings without further formatting work. The only remaining task is to collect the ratings themselves.",
    ]
    Path(args.note_path).write_text("\n".join(note_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
