from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select papers that should be rerun with variable_v2 as a fallback after a variable_v1 extraction.")
    parser.add_argument("--sample-jsonl", required=True, help="JSONL with title/abstract/openalex_work_id rows.")
    parser.add_argument("--v1-results-jsonl", required=True, help="Parsed variable_v1 extraction results JSONL.")
    parser.add_argument("--output-jsonl", required=True, help="Where to write the fallback candidates.")
    parser.add_argument("--max-v1-nodes", type=int, default=6)
    parser.add_argument("--max-abstract-words", type=int, default=210)
    parser.add_argument("--exclude-sustainability", action="store_true", default=False)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def token_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", text))


def work_id_short(openalex_work_id: str) -> str:
    return openalex_work_id.rstrip("/").split("/")[-1]


def contains_sustainability(text: str) -> bool:
    lowered = text.lower()
    return "sustainab" in lowered or "circular economy" in lowered


def main() -> None:
    args = parse_args()
    sample_rows = {work_id_short(str(row["openalex_work_id"])): row for row in iter_jsonl(Path(args.sample_jsonl))}
    result_rows = {str(row["work_id_short"]): row for row in iter_jsonl(Path(args.v1_results_jsonl))}

    out_path = Path(args.output_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    selected = []
    with out_path.open("w", encoding="utf-8") as handle:
        for short_id, result in sorted(result_rows.items(), key=lambda item: item[0]):
            sample = sample_rows.get(short_id)
            if sample is None:
                continue

            title = str(sample["title"])
            abstract = str(sample["abstract"])
            text = f"{title} {abstract}"
            abstract_words = token_count(abstract)
            pred_nodes = len(result.get("output", {}).get("nodes", []))

            if pred_nodes > args.max_v1_nodes:
                continue
            if abstract_words > args.max_abstract_words:
                continue
            if args.exclude_sustainability and contains_sustainability(text):
                continue

            candidate = {
                "openalex_work_id": sample["openalex_work_id"],
                "work_id_short": short_id,
                "title": title,
                "abstract_word_count": abstract_words,
                "v1_predicted_nodes": pred_nodes,
                "contains_sustainability": contains_sustainability(text),
                "fallback_rule": {
                    "max_v1_nodes": args.max_v1_nodes,
                    "max_abstract_words": args.max_abstract_words,
                    "exclude_sustainability": args.exclude_sustainability,
                },
            }
            handle.write(json.dumps(candidate, ensure_ascii=False) + "\n")
            selected.append(candidate)

    print(json.dumps({"selected": len(selected), "output_jsonl": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
