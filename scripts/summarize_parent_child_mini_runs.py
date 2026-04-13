from pathlib import Path
import pandas as pd

ROOT = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/GraphDir")
BASE = ROOT / "data" / "ontology_v2"

RUNS = {
    "stage1": BASE / "parent_child_relation_review_results_v2_2_stage1_mini_low.parquet",
    "stage2": BASE / "parent_child_relation_review_results_v2_2_stage2_mini_low.parquet",
    "stage3": BASE / "parent_child_relation_review_results_v2_2_stage3_mini_low.parquet",
}

parts = []
lines = ["# Parent-Child Mini Run Summary", ""]
for name, path in RUNS.items():
    df = pd.read_parquet(path)
    parts.append(df.assign(run_stage=name))
    lines.append(f"## {name}")
    lines.append(f"- rows: `{len(df):,}`")
    if "prompt_tokens" in df.columns:
        lines.append(f"- prompt tokens: `{int(df['prompt_tokens'].sum()):,}`")
    if "completion_tokens" in df.columns:
        lines.append(f"- completion tokens: `{int(df['completion_tokens'].sum()):,}`")
    for key, value in df["decision"].fillna("missing").value_counts().to_dict().items():
        lines.append(f"- `{key}`: `{value:,}`")
    lines.append("")
merged = pd.concat(parts, ignore_index=True)
merged.to_parquet(BASE / "parent_child_relation_review_results_v2_2_all_mini_low.parquet", index=False)
lines.append("## All stages")
lines.append(f"- rows: `{len(merged):,}`")
for key, value in merged["decision"].fillna("missing").value_counts().to_dict().items():
    lines.append(f"- `{key}`: `{value:,}`")
(BASE / "parent_child_relation_review_results_v2_2_all_mini_low.md").write_text("\n".join(lines) + "\n")
print(BASE / "parent_child_relation_review_results_v2_2_all_mini_low.md")
