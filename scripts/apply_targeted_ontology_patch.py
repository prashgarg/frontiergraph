from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PATCH_SPEC = {
    "merge_groups": [
        {
            "family": "emissions_core",
            "canonical_code": "FG3C000003",
            "canonical_label": "CO2 emissions",
            "merge_codes": [
                "FG3C000010",  # carbon emissions
                "FG3C004594",  # carbon emissions (CO2 emissions)
                "FG3C005109",  # CO2 emissions (carbon emissions)
            ],
        },
        {
            "family": "environmental_quality",
            "canonical_code": "FG3C000081",
            "canonical_label": "environmental quality",
            "merge_codes": [
                "FG3C001420",  # environmental quality (CO2 emissions)
            ],
        },
        {
            "family": "ecological_footprint",
            "canonical_code": "FG3C000064",
            "canonical_label": "ecological footprint",
            "merge_codes": [
                "FG3C001218",  # ecological footprints
            ],
        },
        {
            "family": "wtp_core",
            "canonical_code": "FG3C000323",
            "canonical_label": "willingness to pay",
            "merge_codes": [
                "FG3C000787",  # willingness to pay
            ],
        },
        {
            "family": "wtp_estimates",
            "canonical_code": "FG3C002310",
            "canonical_label": "willingness to pay estimates",
            "merge_codes": [
                "FG3C004121",  # willingness to pay estimates
            ],
        },
    ],
    "label_overrides": {
        "FG3C001033": "environmental degradation",
        "FG3C000323": "willingness to pay",
        "FG3C002310": "willingness to pay estimates",
        "FG3C000081": "environmental quality",
        "FG3C000064": "ecological footprint",
        "FG3C000003": "CO2 emissions",
    },
}

GROUP_KEY_COLS = [
    "paper_id",
    "year",
    "title",
    "authors",
    "venue",
    "source",
    "src_code",
    "dst_code",
    "src_label",
    "dst_label",
    "edge_kind",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a narrow targeted ontology patch directly to the hybrid corpus.")
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _build_code_maps() -> tuple[dict[str, str], dict[str, str], list[dict[str, object]]]:
    remap: dict[str, str] = {}
    label_overrides = dict(PATCH_SPEC["label_overrides"])
    families: list[dict[str, object]] = []
    for group in PATCH_SPEC["merge_groups"]:
        canonical_code = str(group["canonical_code"])
        canonical_label = str(group["canonical_label"])
        label_overrides[canonical_code] = canonical_label
        merge_codes = [str(code) for code in group["merge_codes"]]
        for code in merge_codes:
            remap[code] = canonical_code
        families.append(
            {
                "family": str(group["family"]),
                "canonical_code": canonical_code,
                "canonical_label": canonical_label,
                "merge_codes": merge_codes,
            }
        )
    return remap, label_overrides, families


def _apply_endpoint_patch(frame: pd.DataFrame, code_col: str, label_col: str, remap: dict[str, str], label_overrides: dict[str, str]) -> None:
    original_codes = frame[code_col].astype(str)
    patched_codes = original_codes.map(lambda code: remap.get(code, code))
    frame[code_col] = patched_codes
    current_labels = frame[label_col].astype(str)
    frame[label_col] = patched_codes.map(lambda code: label_overrides.get(code, "")).where(
        patched_codes.map(lambda code: code in label_overrides),
        current_labels,
    )


def _aggregate_patched_corpus(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    undirected_mask = frame["edge_kind"].eq("undirected_noncausal")
    swap_mask = undirected_mask & (frame["src_code"].astype(str) > frame["dst_code"].astype(str))
    if swap_mask.any():
        left_codes = frame.loc[swap_mask, "src_code"].copy()
        left_labels = frame.loc[swap_mask, "src_label"].copy()
        frame.loc[swap_mask, "src_code"] = frame.loc[swap_mask, "dst_code"].values
        frame.loc[swap_mask, "src_label"] = frame.loc[swap_mask, "dst_label"].values
        frame.loc[swap_mask, "dst_code"] = left_codes.values
        frame.loc[swap_mask, "dst_label"] = left_labels.values

    frame["edge_instance_count"] = pd.to_numeric(frame["edge_instance_count"], errors="coerce").fillna(0).astype(int)
    frame["weight"] = pd.to_numeric(frame["weight"], errors="coerce").fillna(0.0).astype(float)
    frame["stability"] = pd.to_numeric(frame["stability"], errors="coerce").fillna(0.0).astype(float)
    frame["stability_numer"] = frame["stability"] * frame["edge_instance_count"].clip(lower=1)
    frame["is_causal"] = frame["is_causal"].fillna(False).astype(int)

    aggregated = (
        frame.groupby(GROUP_KEY_COLS, sort=False, as_index=False)
        .agg(
            relation_type=("relation_type", "first"),
            evidence_type=("evidence_type", "first"),
            causal_presentation=("causal_presentation", "first"),
            directionality_raw=("directionality_raw", "first"),
            edge_instance_count=("edge_instance_count", "sum"),
            stability_numer=("stability_numer", "sum"),
            weight=("weight", "sum"),
            is_causal=("is_causal", "max"),
        )
        .sort_values(["year", "paper_id", "src_code", "dst_code", "edge_kind"], ascending=[True, True, True, True, True])
        .reset_index(drop=True)
    )
    denom = aggregated["edge_instance_count"].clip(lower=1).astype(float)
    aggregated["stability"] = (aggregated["stability_numer"] / denom).astype(float)
    aggregated["is_causal"] = aggregated["is_causal"].astype(bool)
    return aggregated.drop(columns=["stability_numer"])


def _family_report(before_df: pd.DataFrame, after_df: pd.DataFrame, families: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for family in families:
        canonical_code = str(family["canonical_code"])
        canonical_label = str(family["canonical_label"])
        family_codes = [canonical_code] + list(family["merge_codes"])
        before_mask = before_df["src_code"].isin(family_codes) | before_df["dst_code"].isin(family_codes)
        after_mask = after_df["src_code"].eq(canonical_code) | after_df["dst_code"].eq(canonical_code)
        rows.append(
            {
                "family": str(family["family"]),
                "canonical_code": canonical_code,
                "canonical_label": canonical_label,
                "merged_codes_json": json.dumps(family["merge_codes"]),
                "before_rows": int(before_mask.sum()),
                "after_rows": int(after_mask.sum()),
                "before_unique_papers": int(before_df.loc[before_mask, "paper_id"].nunique()),
                "after_unique_papers": int(after_df.loc[after_mask, "paper_id"].nunique()),
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus_path = Path(args.corpus_path)
    before_df = pd.read_parquet(corpus_path)

    remap, label_overrides, families = _build_code_maps()
    patched_df = before_df.copy()
    _apply_endpoint_patch(patched_df, "src_code", "src_label", remap, label_overrides)
    _apply_endpoint_patch(patched_df, "dst_code", "dst_label", remap, label_overrides)
    after_df = _aggregate_patched_corpus(patched_df)

    family_rows = _family_report(before_df, after_df, families)
    family_df = pd.DataFrame(family_rows)
    family_df.to_csv(out_dir / "family_patch_report.csv", index=False)

    after_path = out_dir / "hybrid_corpus.parquet"
    after_df.to_parquet(after_path, index=False)

    summary = {
        "source_corpus": str(corpus_path),
        "patched_corpus": str(after_path),
        "before_rows": int(len(before_df)),
        "after_rows": int(len(after_df)),
        "before_unique_pairs": int(before_df[["src_code", "dst_code", "edge_kind"]].drop_duplicates().shape[0]),
        "after_unique_pairs": int(after_df[["src_code", "dst_code", "edge_kind"]].drop_duplicates().shape[0]),
        "before_unique_concepts": int(pd.Index(before_df["src_code"]).union(pd.Index(before_df["dst_code"])).nunique()),
        "after_unique_concepts": int(pd.Index(after_df["src_code"]).union(pd.Index(after_df["dst_code"])).nunique()),
        "n_rows_collapsed": int(len(before_df) - len(after_df)),
        "patch_spec": PATCH_SPEC,
    }
    (out_dir / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Narrow Ontology Patch v1",
        "",
        "This patch applies a targeted code-level merge layer directly to the local hybrid corpus.",
        "",
        "It is a local experimental patch, not a claim that the full ontology database was rebuilt in this workspace.",
        "",
        "## Summary",
        f"- Before rows: `{summary['before_rows']}`",
        f"- After rows: `{summary['after_rows']}`",
        f"- Collapsed rows: `{summary['n_rows_collapsed']}`",
        f"- Before unique concepts: `{summary['before_unique_concepts']}`",
        f"- After unique concepts: `{summary['after_unique_concepts']}`",
        "",
        "## Families patched",
    ]
    for row in family_rows:
        lines.append(
            f"- `{row['family']}` -> `{row['canonical_label']}` ({row['canonical_code']}); "
            f"rows `{row['before_rows']}` -> `{row['after_rows']}`, papers `{row['before_unique_papers']}` -> `{row['after_unique_papers']}`"
        )
    (out_dir / "patch_note.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote: {after_path}")


if __name__ == "__main__":
    main()
