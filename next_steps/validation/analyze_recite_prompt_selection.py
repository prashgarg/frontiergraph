from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean


DEFAULT_SUMMARY_CSV = (
    "data/pilots/frontiergraph_extraction_v2/judge_runs/"
    "recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/"
    "node_alignment_summary_complete/summary.csv"
)
DEFAULT_MANIFEST_JSON = "next_steps/validation/data/reCITE/frontiergraph_alignment_pilot100_manifest.json"
DEFAULT_V1_INPUT = "next_steps/validation/judge_inputs/recite_alignment_pilot100_variable_v1_node_alignment.jsonl"
DEFAULT_V2_INPUT = "next_steps/validation/judge_inputs/recite_alignment_pilot100_variable_v2_node_alignment.jsonl"
DEFAULT_OUTPUT_CSV = (
    "data/pilots/frontiergraph_extraction_v2/judge_runs/"
    "recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/"
    "prompt_selection_analysis.csv"
)
DEFAULT_OUTPUT_JSON = (
    "data/pilots/frontiergraph_extraction_v2/judge_runs/"
    "recite_alignment_pilot100_node_alignment_gpt5nano_low_v1/"
    "prompt_selection_analysis.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze when variable_v2 helps or hurts on the ReCITE pilot100 node-alignment comparison.")
    parser.add_argument("--summary-csv", default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--manifest-json", default=DEFAULT_MANIFEST_JSON)
    parser.add_argument("--v1-input", default=DEFAULT_V1_INPUT)
    parser.add_argument("--v2-input", default=DEFAULT_V2_INPUT)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-json", default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def token_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", text))


def mean_or_none(values: list[float]) -> float | None:
    return round(mean(values), 3) if values else None


def quantile_edges(values: list[float]) -> list[float]:
    values = sorted(values)
    return [values[len(values) * i // 4] for i in range(1, 4)]


def quartile_bucket(value: float, edges: list[float]) -> str:
    if value <= edges[0]:
        return "Q1"
    if value <= edges[1]:
        return "Q2"
    if value <= edges[2]:
        return "Q3"
    return "Q4"


def main() -> None:
    args = parse_args()
    summary_rows = list(csv.DictReader(Path(args.summary_csv).open(encoding="utf-8")))
    manifest = json.loads(Path(args.manifest_json).read_text(encoding="utf-8"))
    comparability = {str(k): v for k, v in manifest["comparability_classes"].items()}

    metrics: dict[str, dict[str, dict[str, str]]] = {}
    for row in summary_rows:
        metrics.setdefault(str(row["benchmark_id"]), {})[row["prompt_family"]] = row

    v1_inputs = {str(row["benchmark_id"]): row for row in iter_jsonl(Path(args.v1_input))}
    v2_inputs = {str(row["benchmark_id"]): row for row in iter_jsonl(Path(args.v2_input))}

    analysis_rows: list[dict[str, object]] = []
    for bid in sorted(metrics, key=int):
        if bid not in v1_inputs or bid not in v2_inputs:
            continue
        v1_metric = metrics[bid]["variable_v1"]
        v2_metric = metrics[bid]["variable_v2"]
        v1_row = v1_inputs[bid]
        v2_row = v2_inputs[bid]
        gold_nodes = v1_row["gold_nodes"]
        text = (str(v1_row["title"]) + " " + str(v1_row["abstract"])).lower()

        gold_label_word_counts = [token_count(label) for label in gold_nodes]
        row = {
            "benchmark_id": bid,
            "title": v1_row["title"],
            "comparability_class": comparability[bid],
            "v1_f1": float(v1_metric["node_f1"]),
            "v2_f1": float(v2_metric["node_f1"]),
            "delta_f1": float(v2_metric["node_f1"]) - float(v1_metric["node_f1"]),
            "v1_precision": float(v1_metric["node_precision"]),
            "v2_precision": float(v2_metric["node_precision"]),
            "v1_recall": float(v1_metric["node_recall"]),
            "v2_recall": float(v2_metric["node_recall"]),
            "abstract_words": token_count(v1_row["abstract"]),
            "title_words": token_count(v1_row["title"]),
            "gold_nodes_n": len(gold_nodes),
            "gold_avg_label_words": (sum(gold_label_word_counts) / len(gold_label_word_counts)) if gold_label_word_counts else 0.0,
            "gold_share_short": (sum(v <= 2 for v in gold_label_word_counts) / len(gold_label_word_counts)) if gold_label_word_counts else 0.0,
            "v1_pred_nodes_n": len(v1_row["pred_nodes"]),
            "v2_pred_nodes_n": len(v2_row["pred_nodes"]),
            "contains_system_dynamics": int("system dynamics" in text or "systems dynamics" in text),
            "contains_systems_thinking": int(
                "systems thinking" in text or "systems approach" in text or "systems perspective" in text
            ),
            "contains_sustainability": int("sustainab" in text or "circular economy" in text),
            "contains_policy_or_management": int(
                any(token in text for token in ["policy", "policies", "management", "strategy", "strategies", "governance", "planning"])
            ),
            "contains_case_study": int("case study" in text),
        }
        analysis_rows.append(row)

    quartile_features = ["gold_nodes_n", "gold_avg_label_words", "gold_share_short", "abstract_words", "v1_pred_nodes_n", "v1_f1"]
    quartile_edges_map = {key: quantile_edges([float(row[key]) for row in analysis_rows]) for key in quartile_features}
    for row in analysis_rows:
        for key in quartile_features:
            row[f"{key}_quartile"] = quartile_bucket(float(row[key]), quartile_edges_map[key])

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(analysis_rows[0].keys()))
        writer.writeheader()
        writer.writerows(analysis_rows)

    aggregates: dict[str, object] = {
        "rows": len(analysis_rows),
        "overall_mean_delta_f1": mean_or_none([float(row["delta_f1"]) for row in analysis_rows]),
        "by_group": {},
        "rule_checks": {},
    }

    group_keys = [
        "comparability_class",
        "contains_system_dynamics",
        "contains_systems_thinking",
        "contains_sustainability",
        "contains_policy_or_management",
        "contains_case_study",
        "gold_nodes_n_quartile",
        "gold_avg_label_words_quartile",
        "gold_share_short_quartile",
        "abstract_words_quartile",
        "v1_pred_nodes_n_quartile",
        "v1_f1_quartile",
    ]

    for key in group_keys:
        grouped: dict[str, list[float]] = defaultdict(list)
        for row in analysis_rows:
            grouped[str(row[key])].append(float(row["delta_f1"]))
        aggregates["by_group"][key] = {
            group: {
                "rows": len(values),
                "mean_delta_f1": mean_or_none(values),
                "positive_share": round(sum(v > 0 for v in values) / len(values), 3) if values else None,
            }
            for group, values in grouped.items()
        }

    rule_defs = {
        "fallback_pred_le_6": lambda row: int(row["v1_pred_nodes_n"]) <= 6,
        "fallback_pred_le_6_and_abs_le_210": lambda row: int(row["v1_pred_nodes_n"]) <= 6 and int(row["abstract_words"]) <= 210,
        "fallback_pred_le_6_and_abs_le_210_and_not_sustainability": lambda row: (
            int(row["v1_pred_nodes_n"]) <= 6
            and int(row["abstract_words"]) <= 210
            and int(row["contains_sustainability"]) == 0
        ),
    }

    for name, rule in rule_defs.items():
        hit = [float(row["delta_f1"]) for row in analysis_rows if rule(row)]
        miss = [float(row["delta_f1"]) for row in analysis_rows if not rule(row)]
        aggregates["rule_checks"][name] = {
            "rows": len(hit),
            "mean_delta_f1": mean_or_none(hit),
            "positive_share": round(sum(v > 0 for v in hit) / len(hit), 3) if hit else None,
            "else_mean_delta_f1": mean_or_none(miss),
        }

    top_improvements = sorted(analysis_rows, key=lambda row: float(row["delta_f1"]), reverse=True)[:12]
    top_declines = sorted(analysis_rows, key=lambda row: float(row["delta_f1"]))[:12]
    aggregates["top_improvements"] = [
        {
            "benchmark_id": row["benchmark_id"],
            "title": row["title"],
            "delta_f1": round(float(row["delta_f1"]), 3),
            "v1_f1": round(float(row["v1_f1"]), 3),
            "v2_f1": round(float(row["v2_f1"]), 3),
        }
        for row in top_improvements
    ]
    aggregates["top_declines"] = [
        {
            "benchmark_id": row["benchmark_id"],
            "title": row["title"],
            "delta_f1": round(float(row["delta_f1"]), 3),
            "v1_f1": round(float(row["v1_f1"]), 3),
            "v2_f1": round(float(row["v2_f1"]), 3),
        }
        for row in top_declines
    ]

    Path(args.output_json).write_text(json.dumps(aggregates, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
