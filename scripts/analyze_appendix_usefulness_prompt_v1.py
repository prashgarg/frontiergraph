from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

INPUT_PRICE_PER_MTOK = 0.75
OUTPUT_PRICE_PER_MTOK = 4.50


def _extract_json(response: dict) -> dict:
    for output in response.get("output", []):
        if output.get("type") != "message":
            continue
        for item in output.get("content", []):
            if item.get("type") == "output_text" and item.get("text"):
                return json.loads(item["text"])
            if item.get("type") == "refusal":
                return {"refusal": item.get("refusal")}
    raise ValueError("No parseable message content found")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", required=True)
    parser.add_argument("--pilot-csv", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    responses_path = Path(args.responses)
    pilot_path = Path(args.pilot_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    usage_rows: list[dict] = []
    with responses_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            payload = json.loads(line)
            response = payload["response"]
            parsed = _extract_json(response)
            rows.append({"item_id": payload["custom_id"], **parsed})

            usage = response.get("usage", {})
            usage_rows.append(
                {
                    "item_id": payload["custom_id"],
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "reasoning_tokens": (
                        usage.get("output_tokens_details", {}) or {}
                    ).get("reasoning_tokens", 0),
                }
            )

    pilot = pd.read_csv(pilot_path)
    parsed_df = pd.DataFrame(rows)
    usage_df = pd.DataFrame(usage_rows)
    merged = pilot.merge(parsed_df, on="item_id", how="left").merge(
        usage_df, on="item_id", how="left"
    )

    merged.to_csv(out_dir / "pilot10_outputs.csv", index=False)

    input_tokens_total = int(merged["input_tokens"].sum())
    output_tokens_total = int(merged["output_tokens"].sum())
    estimated_cost_usd = (
        (input_tokens_total / 1_000_000.0) * INPUT_PRICE_PER_MTOK
        + (output_tokens_total / 1_000_000.0) * OUTPUT_PRICE_PER_MTOK
    )

    summary = {
        "n_rows": int(len(merged)),
        "mean_readability": float(merged["readability"].mean()),
        "mean_interpretability": float(merged["interpretability"].mean()),
        "mean_usefulness": float(merged["usefulness"].mean()),
        "artifact_risk_counts": merged["artifact_risk"].value_counts().to_dict(),
        "input_tokens_total": input_tokens_total,
        "output_tokens_total": output_tokens_total,
        "reasoning_tokens_total": int(merged["reasoning_tokens"].sum()),
        "input_tokens_per_request": float(merged["input_tokens"].mean()),
        "output_tokens_per_request": float(merged["output_tokens"].mean()),
        "estimated_cost_usd": estimated_cost_usd,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
