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
    parser = argparse.ArgumentParser(description="Analyze historical appendix usefulness responses.")
    parser.add_argument("--responses", required=True)
    parser.add_argument("--selected-csv", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    responses_path = Path(args.responses)
    selected_path = Path(args.selected_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    response_rows: list[dict] = []
    usage_rows: list[dict] = []
    with responses_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            payload = json.loads(line)
            response = payload["response"]
            parsed = _extract_json(response)
            response_rows.append({"item_id": payload["custom_id"], **parsed})
            usage = response.get("usage", {})
            usage_rows.append(
                {
                    "item_id": payload["custom_id"],
                    "input_tokens": int(usage.get("input_tokens", 0) or 0),
                    "output_tokens": int(usage.get("output_tokens", 0) or 0),
                    "reasoning_tokens": int(((usage.get("output_tokens_details", {}) or {}).get("reasoning_tokens", 0) or 0)),
                }
            )

    selected_df = pd.read_csv(selected_path)
    parsed_df = pd.DataFrame(response_rows)
    usage_df = pd.DataFrame(usage_rows)
    merged = selected_df.merge(parsed_df, on="item_id", how="inner").merge(usage_df, on="item_id", how="inner")
    merged.to_csv(out_dir / "historical_usefulness_outputs.csv", index=False)

    merged["mean_score"] = merged[["readability", "interpretability", "usefulness"]].mean(axis=1)

    summary_by_arm = (
        merged.groupby(["selection_arm", "selection_horizon"], as_index=False)
        .agg(
            n_items=("item_id", "size"),
            mean_readability=("readability", "mean"),
            mean_interpretability=("interpretability", "mean"),
            mean_usefulness=("usefulness", "mean"),
            mean_score=("mean_score", "mean"),
        )
        .sort_values(["selection_horizon", "selection_arm"])
        .reset_index(drop=True)
    )
    summary_by_arm_era = (
        merged.groupby(["era", "selection_arm", "selection_horizon"], as_index=False)
        .agg(
            n_items=("item_id", "size"),
            mean_readability=("readability", "mean"),
            mean_interpretability=("interpretability", "mean"),
            mean_usefulness=("usefulness", "mean"),
            mean_score=("mean_score", "mean"),
            high_artifact_share=("artifact_risk", lambda s: float((s == "high").mean())),
        )
        .sort_values(["era", "selection_horizon", "selection_arm"])
        .reset_index(drop=True)
    )
    artifact_counts = (
        merged.groupby(["selection_arm", "selection_horizon", "artifact_risk"], as_index=False)
        .agg(n_items=("item_id", "size"))
        .sort_values(["selection_horizon", "selection_arm", "artifact_risk"])
        .reset_index(drop=True)
    )

    summary_by_arm.to_csv(out_dir / "summary_by_arm.csv", index=False)
    summary_by_arm_era.to_csv(out_dir / "summary_by_arm_era.csv", index=False)
    artifact_counts.to_csv(out_dir / "artifact_counts_by_arm.csv", index=False)
    merged.sort_values(["mean_score", "item_id"]).head(25).to_csv(out_dir / "examples_low_score.csv", index=False)
    merged.sort_values(["mean_score", "item_id"], ascending=[False, True]).head(25).to_csv(out_dir / "examples_high_score.csv", index=False)

    input_tokens_total = int(merged["input_tokens"].fillna(0).sum())
    output_tokens_total = int(merged["output_tokens"].fillna(0).sum())
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
        "reasoning_tokens_total": int(merged["reasoning_tokens"].fillna(0).sum()),
        "input_tokens_per_request": float(merged["input_tokens"].mean()),
        "output_tokens_per_request": float(merged["output_tokens"].mean()),
        "estimated_cost_usd": estimated_cost_usd,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
