from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKETS = ROOT / "outputs" / "paper" / "174_wide_mechanism_mini_triage_pack" / "candidate_packets.csv"
DEFAULT_RUN = ROOT / "outputs" / "paper" / "175_wide_mechanism_mini_triage_run"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "176_wide_mechanism_mini_triage_analysis"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze full wide-pool mechanism mini-model triage outputs.")
    parser.add_argument("--packets", default=str(DEFAULT_PACKETS), dest="packets")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN), dest="run_dir")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    return parser.parse_args()


def extract_text_payload(response: dict[str, Any]) -> str | None:
    for output in response.get("output", []):
        if output.get("type") != "message":
            continue
        for item in output.get("content", []):
            if item.get("type") == "output_text":
                return item.get("text")
    return None


def parse_json_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    text = str(raw).strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def normalize_pair_key(value: Any) -> str:
    text = str(value or "")
    text = (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2012", "-")
        .replace("\u2011", "-")
        .replace("\u2010", "-")
        .replace("\x13", "-")
        .replace("\x19", "-")
        .replace("_", "-")
    )
    parts = []
    for part in text.split("__"):
        norm = part.strip().lower().replace(" ", "-")
        norm = re.sub(r"-+", "-", norm)
        parts.append(norm)
    return "__".join(parts)


def repair_truncated_json(text_payload: str) -> tuple[dict[str, Any] | None, str | None]:
    reason_marker = ',"reason":"'
    if reason_marker not in text_payload:
        return None, None
    prefix, reason_tail = text_payload.split(reason_marker, 1)
    sanitized_reason = reason_tail.replace("\\", "\\\\").replace('"', '\\"')
    if sanitized_reason.endswith("}"):
        sanitized_reason = sanitized_reason[:-1]
    repaired = f'{prefix},"reason":"{sanitized_reason}"}}'
    try:
        return json.loads(repaired), "repaired_truncated_reason"
    except json.JSONDecodeError:
        try:
            repaired_empty = f'{prefix},"reason":""}}'
            return json.loads(repaired_empty), "repaired_empty_reason"
        except json.JSONDecodeError:
            return None, None


def parse_responses(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    parsed_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            payload = json.loads(line)
            custom_id = str(payload.get("custom_id") or "")
            response = payload.get("response") or {}
            text = extract_text_payload(response)
            if not text:
                failures.append({"custom_id": custom_id, "error": "missing_output_text"})
                continue
            try:
                parsed = json.loads(text)
                parse_mode = "direct"
            except json.JSONDecodeError as exc:
                repaired, parse_mode = repair_truncated_json(text)
                if repaired is None:
                    failures.append({"custom_id": custom_id, "error": f"json_decode_error: {exc}", "raw_text": text[:1000]})
                    continue
                parsed = repaired
            parsed_rows.append(
                {
                    "custom_id": custom_id,
                    "pair_key": str(parsed.get("pair_key") or custom_id.split("-", 3)[-1]),
                    "model": response.get("model"),
                    "parse_mode": parse_mode,
                    **parsed,
                }
            )
    return pd.DataFrame(parsed_rows), pd.DataFrame(failures)


def main() -> None:
    args = parse_args()
    packets = pd.read_csv(Path(args.packets), low_memory=False)
    parsed_df, failures_df = parse_responses(Path(args.run_dir) / "responses.jsonl")
    packets["pair_key_norm"] = packets["pair_key"].apply(normalize_pair_key)
    parsed_df["pair_key_norm"] = parsed_df["pair_key"].apply(normalize_pair_key)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    merged = packets.merge(parsed_df, on="pair_key_norm", how="left", suffixes=("_packet", "_mini"))
    if "pair_key_packet" in merged.columns:
        merged["pair_key"] = merged["pair_key_packet"]
    if "pair_key_mini" in merged.columns:
        merged["pair_key_response"] = merged["pair_key_mini"]
    merged["field_shelves"] = merged["field_shelves"].fillna("[]")
    merged["collection_tags"] = merged["collection_tags"].fillna("[]")
    merged["has_model_response"] = merged["pair_key_norm"].isin(set(parsed_df["pair_key_norm"].astype(str)))
    merged["keep_for_public_site"] = merged["keep_for_public_site"].fillna(False).astype(bool)
    merged["field_shelf_count_mini"] = merged["field_shelves"].apply(lambda raw: len(parse_json_list(raw)))
    merged["collection_tag_count_mini"] = merged["collection_tags"].apply(lambda raw: len(parse_json_list(raw)))

    responded = merged[merged["has_model_response"]].copy()
    missing = merged[~merged["has_model_response"]].copy()
    kept = responded[responded["keep_for_public_site"]].copy().sort_values(
        ["suggested_priority", "mechanism_plausibility", "question_object_clarity", "packet_rank"],
        ascending=[True, False, False, True],
    )
    dropped = responded[~responded["keep_for_public_site"]].copy()

    merged.to_csv(out_dir / "triage_all_candidates.csv", index=False)
    kept.to_csv(out_dir / "triage_kept_candidates.csv", index=False)
    dropped.to_csv(out_dir / "triage_dropped_candidates.csv", index=False)
    missing.to_csv(out_dir / "triage_missing_responses.csv", index=False)
    failures_df.to_csv(out_dir / "triage_failures.csv", index=False)

    lines = [
        "# Wide Mechanism Mini Triage",
        "",
        f"- parsed responses: {len(parsed_df):,}",
        f"- failed parses: {len(failures_df):,}",
        f"- missing responses: {len(missing):,}",
        f"- kept for public site: {len(kept):,}",
        f"- dropped: {len(dropped):,}",
        "",
        "## Primary issues",
        "",
    ]
    for issue, count in merged["primary_issue"].fillna("missing").value_counts().items():
        lines.append(f"- {issue}: {int(count):,}")

    lines.extend(["", "## Field shelf counts among kept", ""])
    field_counter: dict[str, int] = {}
    for raw in kept["field_shelves"]:
        for field in parse_json_list(raw):
            field_counter[field] = field_counter.get(field, 0) + 1
    for field, count in sorted(field_counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {field}: {count:,}")

    lines.extend(["", "## Use-case counts among kept", ""])
    tag_counter: dict[str, int] = {}
    for raw in kept["collection_tags"]:
        for tag in parse_json_list(raw):
            tag_counter[tag] = tag_counter.get(tag, 0) + 1
    for tag, count in sorted(tag_counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {tag}: {count:,}")

    lines.extend(["", "## Top kept candidates", ""])
    for row in kept.head(30).itertuples(index=False):
        lines.append(
            f"- {row.display_title} | priority={row.suggested_priority} | plausibility={int(row.mechanism_plausibility)} | clarity={int(row.question_object_clarity)} | fields={row.field_shelves}"
        )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_dir}")


if __name__ == "__main__":
    main()
