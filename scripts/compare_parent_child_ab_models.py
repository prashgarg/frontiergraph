from pathlib import Path

import pandas as pd


ROOT = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/GraphDir")
BASE = ROOT / "data" / "ontology_v2"


def main() -> None:
    nano = pd.read_parquet(BASE / "parent_child_relation_review_results_v2_2_ab_nano.parquet")
    mini = pd.read_parquet(BASE / "parent_child_relation_review_results_v2_2_ab_mini_low.parquet")

    key_cols = ["child_label", "candidate_parent_label", "review_tier", "candidate_channel"]
    cols = key_cols + ["review_id", "decision", "confidence", "reason", "raw_response_ok"]

    nano = nano[cols].rename(
        columns={
            "review_id": "review_id_nano",
            "decision": "decision_nano",
            "confidence": "confidence_nano",
            "reason": "reason_nano",
            "raw_response_ok": "raw_response_ok_nano",
        }
    )
    mini = mini[cols].rename(
        columns={
            "review_id": "review_id_mini",
            "decision": "decision_mini",
            "confidence": "confidence_mini",
            "reason": "reason_mini",
            "raw_response_ok": "raw_response_ok_mini",
        }
    )

    merged = nano.merge(mini, on=key_cols, how="inner")
    merged["agree"] = merged["decision_nano"] == merged["decision_mini"]
    merged.to_parquet(BASE / "parent_child_ab_comparison.parquet", index=False)

    out = []
    out.append("# Parent-Child A/B Comparison")
    out.append("")
    out.append(f"- rows: `{len(merged):,}`")
    out.append(f"- overall agreement: `{merged['agree'].mean():.3f}`")
    out.append("")
    out.append("## Decisions by model")
    for name, series in [("nano", merged["decision_nano"]), ("mini", merged["decision_mini"])]:
        out.append(f"### {name}")
        for key, value in series.fillna("missing").value_counts().to_dict().items():
            out.append(f"- `{key}`: `{value:,}`")
        out.append("")
    out.append("## Agreement by tier")
    for tier, sub in merged.groupby("review_tier"):
        out.append(f"- `{tier}`: `{sub['agree'].mean():.3f}` ({len(sub):,} rows)")
    out.append("")
    out.append("## Alias Usage by tier")
    for tier, sub in merged.groupby("review_tier"):
        nano_alias = int((sub["decision_nano"] == "alias_or_duplicate").sum())
        mini_alias = int((sub["decision_mini"] == "alias_or_duplicate").sum())
        out.append(f"- `{tier}`: nano `{nano_alias}`, mini `{mini_alias}`")
    out.append("")
    out.append("## Disagreements")
    disagreements = merged[~merged["agree"]][
        [
            "review_tier",
            "candidate_channel",
            "child_label",
            "candidate_parent_label",
            "decision_nano",
            "decision_mini",
            "reason_nano",
            "reason_mini",
        ]
    ].head(60)
    out.append(disagreements.to_markdown(index=False))
    out.append("")
    out.append("## Alias-Focused Rows")
    alias_rows = merged[
        (merged["decision_nano"] == "alias_or_duplicate")
        | (merged["decision_mini"] == "alias_or_duplicate")
    ][
        [
            "review_tier",
            "candidate_channel",
            "child_label",
            "candidate_parent_label",
            "decision_nano",
            "decision_mini",
            "reason_nano",
            "reason_mini",
        ]
    ].head(80)
    out.append(alias_rows.to_markdown(index=False))
    (BASE / "parent_child_ab_comparison.md").write_text("\n".join(out) + "\n")
    print(BASE / "parent_child_ab_comparison.md")
    print(len(merged), merged["agree"].mean())


if __name__ == "__main__":
    main()
