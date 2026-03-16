from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
CURRENT_TOP_QUESTIONS = SITE_ROOT / "public" / "data" / "v2" / "top_questions.csv"
BROAD_TOP_QUESTIONS = SITE_ROOT / "public" / "data" / "broad-v1" / "top_questions.csv"
CURRENT_SITE_DATA = SITE_ROOT / "src" / "generated" / "site-data.json"
BROAD_SITE_DATA = SITE_ROOT / "src" / "generated" / "site-data-broad.json"
OUTPUT_JSON = SITE_ROOT / "src" / "generated" / "regime-audit.json"
OUTPUT_MD = ROOT / "outputs" / "frontiergraph_regime_audit" / "current_release_vs_broad_preview.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_label(value: Any) -> str:
    text = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in str(value or "").lower())
    return " ".join(text.split())


def to_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def question_key(row: dict[str, Any]) -> str:
    source = normalize_label(row.get("source_display_label") or row.get("source_label") or "")
    target = normalize_label(row.get("target_display_label") or row.get("target_label") or "")
    if source and target:
        return " __ ".join(sorted([source, target]))
    return normalize_label(row.get("public_pair_label") or row.get("pair_key") or "")


def compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "pair_key": row.get("pair_key", ""),
        "question": row.get("public_pair_label", ""),
        "source": row.get("source_display_label") or row.get("source_label", ""),
        "target": row.get("target_display_label") or row.get("target_label", ""),
        "supporting_paths": to_int(row.get("supporting_path_count")),
        "mediators": to_int(row.get("mediator_count")),
        "specificity": round(to_float(row.get("public_specificity_score")), 3),
        "score": round(to_float(row.get("score")), 3),
        "app_link": row.get("app_link", ""),
    }


def summary_stats(rows: list[dict[str, Any]], top_n: int = 40) -> dict[str, Any]:
    sample = rows[:top_n]
    if not sample:
        return {
            "top_n": top_n,
            "mean_specificity": 0.0,
            "mean_supporting_paths": 0.0,
            "mean_mediators": 0.0,
            "mean_cross_field_share": 0.0,
            "mean_no_direct_share": 0.0,
        }
    return {
        "top_n": top_n,
        "mean_specificity": round(sum(to_float(row.get("public_specificity_score")) for row in sample) / len(sample), 3),
        "mean_supporting_paths": round(sum(to_int(row.get("supporting_path_count")) for row in sample) / len(sample), 2),
        "mean_mediators": round(sum(to_int(row.get("mediator_count")) for row in sample) / len(sample), 2),
        "mean_cross_field_share": round(sum(1 for row in sample if to_int(row.get("cross_field")) > 0) / len(sample), 3),
        "mean_no_direct_share": round(sum(1 for row in sample if to_int(row.get("cooc_count")) <= 0) / len(sample), 3),
    }


def build_payload() -> dict[str, Any]:
    current_rows = read_csv(CURRENT_TOP_QUESTIONS)
    broad_rows = read_csv(BROAD_TOP_QUESTIONS)
    current_site = json.loads(CURRENT_SITE_DATA.read_text(encoding="utf-8"))
    broad_site = json.loads(BROAD_SITE_DATA.read_text(encoding="utf-8"))

    current_keys = {question_key(row) for row in current_rows[:80]}
    broad_keys = {question_key(row) for row in broad_rows[:80]}

    broad_only = [compact_row(row) for row in broad_rows if question_key(row) not in current_keys][:24]
    current_only = [compact_row(row) for row in current_rows if question_key(row) not in broad_keys][:24]

    payload = {
        "generated_at": broad_site.get("generated_at"),
        "comparison_note": (
            "The current public site is the filtered baseline release. The broad preview is a separate broad-regime top-window preview."
        ),
        "summary": {
            "current_topics": int(current_site.get("metrics", {}).get("native_concepts", 0)),
            "broad_topics": int(broad_site.get("metrics", {}).get("native_concepts", 0)),
            "current_visible_questions": int(current_site.get("metrics", {}).get("visible_public_questions", 0)),
            "broad_visible_questions": int(broad_site.get("metrics", {}).get("visible_public_questions", 0)),
            "top80_overlap_after_mirror_dedupe": len(current_keys & broad_keys),
            "current_top": summary_stats(current_rows),
            "broad_top": summary_stats(broad_rows),
        },
        "current_top_questions": [compact_row(row) for row in current_rows[:24]],
        "broad_top_questions": [compact_row(row) for row in broad_rows[:24]],
        "broad_only_examples": broad_only,
        "current_only_examples": current_only,
    }
    return payload


def write_markdown(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Current release vs broad preview audit",
        "",
        payload["comparison_note"],
        "",
        f"- Current release topics: `{summary['current_topics']:,}`",
        f"- Broad preview topics: `{summary['broad_topics']:,}`",
        f"- Current visible public questions: `{summary['current_visible_questions']:,}`",
        f"- Broad preview visible public questions: `{summary['broad_visible_questions']:,}`",
        f"- Top-80 overlap after mirror dedupe: `{summary['top80_overlap_after_mirror_dedupe']}`",
        "",
        "## Broad-only examples",
    ]
    for row in payload["broad_only_examples"][:12]:
        lines.append(f"- {row['question']} | paths `{row['supporting_paths']}` | mediators `{row['mediators']}`")
    lines.extend(["", "## Current-release-only examples"])
    for row in payload["current_only_examples"][:12]:
        lines.append(f"- {row['question']} | paths `{row['supporting_paths']}` | mediators `{row['mediators']}`")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload)


if __name__ == "__main__":
    main()
