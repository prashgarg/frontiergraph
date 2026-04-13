from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHORTLIST = ROOT / "outputs" / "paper" / "26_current_path_mediator_shortlist_patch_v2" / "current_path_mediator_shortlist.csv"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "168_mechanism_public_screen"

GENERIC_ENDPOINT_PATTERNS = (
    r"\bwillingness to pay\b",
    r"\bprice changes?\b",
    r"\bregional heterogeneity\b",
    r"\becological footprint\b",
    r"\brate of growth\b",
    r"\bmistake\b",
)

BLOCKED_MEDIATOR_PATTERNS = (
    r"\bgranger causality\b",
    r"\bhedonic model\b",
    r"\bquantile regression\b",
    r"\btest\b",
    r"\bmodel\b",
    r"\bindex\b",
    r"\bshort run\b",
)

THEME_PAIR_CAP = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a screened candidate pack for public mechanism-question curation.")
    parser.add_argument("--shortlist", default=str(DEFAULT_SHORTLIST), dest="shortlist")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    return parser.parse_args()


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_list(raw: Any) -> list[str]:
    try:
        value = ast.literal_eval(str(raw))
    except Exception:
        return []
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        text = clean_text(item)
        if not text or text.startswith("FG3C"):
            continue
        out.append(text)
    return out


def endpoint_is_generic(label: str) -> bool:
    text = normalize_text(label)
    return any(re.search(pattern, text) for pattern in GENERIC_ENDPOINT_PATTERNS)


def mediator_is_blocked(label: str) -> bool:
    text = normalize_text(label)
    return any(re.search(pattern, text) for pattern in BLOCKED_MEDIATOR_PATTERNS)


def quality_gate(row: pd.Series) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if clean_text(row.get("route_family")) not in {"path_question", "mediator_question"}:
      reasons.append("route_family_not_mechanism_like")
    if "poorly labeled" in clean_text(row.get("display_why")).lower():
      reasons.append("poorly_labeled")
    if endpoint_is_generic(clean_text(row.get("source_label"))):
      reasons.append("generic_source")
    if endpoint_is_generic(clean_text(row.get("target_label"))):
      reasons.append("generic_target")
    primary_labels = parse_list(row.get("primary_mediator_labels"))
    if len(primary_labels) < 2:
      reasons.append("too_few_channels")
    blocked_count = sum(1 for label in primary_labels if mediator_is_blocked(label))
    if blocked_count >= max(1, len(primary_labels)):
      reasons.append("channels_are_methods_or_generic")
    return (len(reasons) == 0, reasons)


def llm_prompt(row: pd.Series, primary_labels: list[str]) -> str:
    source = clean_text(row.get("source_label"))
    target = clean_text(row.get("target_label"))
    channels = ", ".join(primary_labels)
    return (
        "Rewrite this candidate into a public-facing mechanism research question.\n"
        "Keep the substantive endpoints fixed. Do not invent new concepts or claims.\n"
        "Prefer a paper-shaped title, one short reason it is worth asking, and one concrete first step.\n\n"
        f"Source topic: {source}\n"
        f"Target topic: {target}\n"
        f"Current route family: {clean_text(row.get('route_family'))}\n"
        f"Candidate channels: {channels}\n"
        f"Current title: {clean_text(row.get('display_title'))}\n"
        f"Current why: {clean_text(row.get('display_why'))}\n"
        f"Current first step: {clean_text(row.get('display_first_step'))}\n\n"
        "Return JSON with keys: question_title, short_why, first_next_step, who_its_for."
    )


def choose_candidates(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["primary_labels"] = work["primary_mediator_labels"].apply(parse_list)
    gate = work.apply(quality_gate, axis=1)
    work["passes_gate"] = [flag for flag, _ in gate]
    work["gate_reasons"] = [";".join(reasons) for _, reasons in gate]
    screened = work[work["passes_gate"]].copy()
    screened = screened.sort_values(["shortlist_rank", "surface_rank"]).reset_index(drop=True)

    kept_rows = []
    seen_pairs: set[str] = set()
    theme_counts: dict[str, int] = {}
    for row in screened.itertuples(index=False):
        pair_key = clean_text(getattr(row, "pair_key"))
        theme_pair_key = clean_text(getattr(row, "theme_pair_key", ""))
        if pair_key in seen_pairs:
            continue
        if theme_pair_key:
            count = theme_counts.get(theme_pair_key, 0)
            if count >= THEME_PAIR_CAP:
                continue
            theme_counts[theme_pair_key] = count + 1
        seen_pairs.add(pair_key)
        kept_rows.append(row._asdict())
    return pd.DataFrame(kept_rows)


def write_outputs(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    export = df.copy()
    export["primary_labels"] = export["primary_labels"].apply(json.dumps)
    export.to_csv(out_dir / "screened_candidates.csv", index=False)

    prompt_rows = []
    seed_template: dict[str, dict[str, Any]] = {}
    note_lines = [
        "# Mechanism Public Screen",
        "",
        "These rows passed the public mechanism-question quality gates and are ready for LLM/editorial rewriting.",
        "",
    ]
    for row in df.itertuples(index=False):
        primary_labels = list(getattr(row, "primary_labels"))
        prompt_rows.append(
            {
                "pair_key": row.pair_key,
                "prompt": llm_prompt(pd.Series(row._asdict()), primary_labels),
            }
        )
        seed_template[row.pair_key] = {
            "pair_key": row.pair_key,
            "question_title": clean_text(row.display_title),
            "short_why": clean_text(row.display_why),
            "first_next_step": clean_text(row.display_first_step),
            "who_its_for": "",
            "display_order": 0,
            "field_shelves": [],
            "collection_tags": [],
            "question_family": "",
            "graph_query": clean_text(row.source_label),
            "graph_family": "mechanism",
            "source_label": clean_text(row.source_label),
            "target_label": clean_text(row.target_label),
            "channel_labels": primary_labels,
            "route_family": clean_text(row.route_family),
        }
        note_lines.append(f"## {row.source_label} -> {row.target_label}")
        note_lines.append(f"- shortlist rank: {int(row.shortlist_rank)}")
        note_lines.append(f"- title seed: {clean_text(row.display_title)}")
        note_lines.append(f"- why seed: {clean_text(row.display_why)}")
        note_lines.append(f"- channels: {', '.join(primary_labels)}")
        note_lines.append("")

    with (out_dir / "screening_prompts.jsonl").open("w", encoding="utf-8") as handle:
        for row in prompt_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out_dir / "editorial_seed_template.json").write_text(json.dumps(seed_template, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "screening_note.md").write_text("\n".join(note_lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    shortlist_path = Path(args.shortlist)
    out_dir = Path(args.out_dir)
    df = pd.read_csv(shortlist_path)
    candidates = choose_candidates(df)
    write_outputs(candidates, out_dir)
    print(f"Wrote {out_dir / 'screened_candidates.csv'}")
    print(f"Wrote {out_dir / 'screening_prompts.jsonl'}")
    print(f"Wrote {out_dir / 'editorial_seed_template.json'}")


if __name__ == "__main__":
    main()
