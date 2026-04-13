from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PATCH_V2_SPEC = {
    "starting_point": "data/processed/research_allocation_v2_patch_v1/hybrid_corpus.parquet",
    "boundary_family": {
        "endpoint_nodes": {
            "FG3C000081": "environmental quality",
            "FG3C000203": "environmental pollution",
            "FG3C000130": "environmental degradation",
            "FG3C000003": "CO2 emissions",
            "FG3C000064": "ecological footprint",
        },
        "mechanism_like_labels": [
            "pollution abatement",
            "environmental taxes",
            "environmental governance",
            "Environmental Kuznets Curve (EKC) hypothesis",
        ],
        "do_not_merge_codes": [
            "FG3C000081",
            "FG3C000203",
            "FG3C000130",
            "FG3C000003",
            "FG3C000064",
        ],
    },
    "code_label_overrides": {
        "FG3C000081": "environmental quality",
        "FG3C000203": "environmental pollution",
        "FG3C000130": "environmental degradation",
        "FG3C000003": "CO2 emissions",
        "FG3C000064": "ecological footprint",
    },
    "exact_label_overrides": {
        "environmental degradation (CO2 emissions)": "environmental degradation",
        "carbon dioxide (CO2) emission": "CO2 emissions",
        "gross domestic product (GDP)": "GDP",
        "economic growth (GDP)": "GDP",
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
    parser = argparse.ArgumentParser(description="Apply conservative targeted ontology patch v2 on top of patch v1.")
    parser.add_argument(
        "--corpus",
        default=PATCH_V2_SPEC["starting_point"],
        dest="corpus_path",
    )
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _apply_label_overrides(frame: pd.DataFrame, code_col: str, label_col: str) -> dict[str, int]:
    counts = {
        f"code::{code}": 0 for code in PATCH_V2_SPEC["code_label_overrides"]
    }
    counts.update({f"label::{label}": 0 for label in PATCH_V2_SPEC["exact_label_overrides"]})

    current_codes = frame[code_col].astype(str)
    current_labels = frame[label_col].astype(str)

    for code, label in PATCH_V2_SPEC["code_label_overrides"].items():
        mask = current_codes.eq(str(code)) & current_labels.ne(str(label))
        counts[f"code::{code}"] = int(mask.sum())
        frame.loc[mask, label_col] = str(label)

    current_labels = frame[label_col].astype(str)
    for raw_label, canonical_label in PATCH_V2_SPEC["exact_label_overrides"].items():
        mask = current_labels.eq(str(raw_label))
        counts[f"label::{raw_label}"] = int(mask.sum())
        frame.loc[mask, label_col] = str(canonical_label)

    return counts


def _aggregate_corpus(df: pd.DataFrame) -> pd.DataFrame:
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


def _boundary_family_report(df: pd.DataFrame) -> pd.DataFrame:
    endpoint_nodes = PATCH_V2_SPEC["boundary_family"]["endpoint_nodes"]
    mechanism_labels = [str(x) for x in PATCH_V2_SPEC["boundary_family"]["mechanism_like_labels"]]
    rows: list[dict[str, object]] = []
    for code, label in endpoint_nodes.items():
        mask = (
            (df["src_code"].astype(str).eq(str(code)) | df["dst_code"].astype(str).eq(str(code)))
            | (df["src_label"].astype(str).eq(str(label)) | df["dst_label"].astype(str).eq(str(label)))
        )
        rows.append(
            {
                "role": "endpoint_outcome",
                "key": str(code),
                "label": str(label),
                "rows": int(mask.sum()),
                "unique_papers": int(df.loc[mask, "paper_id"].nunique()),
            }
        )
    for label in mechanism_labels:
        mask = df["src_label"].astype(str).eq(label) | df["dst_label"].astype(str).eq(label)
        rows.append(
            {
                "role": "mechanism_like",
                "key": label,
                "label": label,
                "rows": int(mask.sum()),
                "unique_papers": int(df.loc[mask, "paper_id"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def _write_patch_note(
    out_path: Path,
    source_corpus: Path,
    after_path: Path,
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    override_counts: dict[str, int],
) -> None:
    lines = [
        "# Targeted Ontology Patch v2 Note",
        "",
        "This is a conservative corpus-layer patch built on top of patch v1.",
        "",
        "It intentionally does **not** introduce new merges across the environmental outcome family.",
        "",
        "## Starting point",
        f"- source corpus: `{source_corpus}`",
        f"- patched corpus: `{after_path}`",
        "",
        "## Locked boundary rule",
        "- keep these as separate canonical nodes in v2:",
    ]
    for code, label in PATCH_V2_SPEC["boundary_family"]["endpoint_nodes"].items():
        lines.append(f"  - `{code}` = `{label}`")
    lines.extend(
        [
            "",
            "## Mechanism-like adjacent labels",
        ]
    )
    for label in PATCH_V2_SPEC["boundary_family"]["mechanism_like_labels"]:
        lines.append(f"- `{label}`")
    lines.extend(
        [
            "",
            "## Exact label overrides applied",
        ]
    )
    for raw_label, canonical_label in PATCH_V2_SPEC["exact_label_overrides"].items():
        count = int(override_counts.get(f"label::{raw_label}", 0))
        lines.append(f"- `{raw_label}` -> `{canonical_label}` | rows touched: `{count}`")
    lines.extend(
        [
            "",
            "## Code-based label overrides applied",
        ]
    )
    for code, canonical_label in PATCH_V2_SPEC["code_label_overrides"].items():
        count = int(override_counts.get(f"code::{code}", 0))
        lines.append(f"- `{code}` -> `{canonical_label}` | rows touched: `{count}`")
    lines.extend(
        [
            "",
            "## Mechanical effect",
            f"- rows: `{len(before_df):,}` -> `{len(after_df):,}`",
            f"- unique concepts: `{pd.Index(before_df['src_code']).union(pd.Index(before_df['dst_code'])).nunique():,}` -> `{pd.Index(after_df['src_code']).union(pd.Index(after_df['dst_code'])).nunique():,}`",
            f"- unique pairs: `{before_df[['src_code', 'dst_code', 'edge_kind']].drop_duplicates().shape[0]:,}` -> `{after_df[['src_code', 'dst_code', 'edge_kind']].drop_duplicates().shape[0]:,}`",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus_path = Path(args.corpus_path)
    before_df = pd.read_parquet(corpus_path)

    patched_df = before_df.copy()
    counts_src = _apply_label_overrides(patched_df, "src_code", "src_label")
    counts_dst = _apply_label_overrides(patched_df, "dst_code", "dst_label")
    override_counts = {
        key: int(counts_src.get(key, 0) + counts_dst.get(key, 0))
        for key in set(counts_src) | set(counts_dst)
    }
    after_df = _aggregate_corpus(patched_df)

    after_path = out_dir / "hybrid_corpus.parquet"
    after_df.to_parquet(after_path, index=False)
    _boundary_family_report(after_df).to_csv(out_dir / "boundary_family_report.csv", index=False)

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
        "override_counts": override_counts,
        "patch_spec": PATCH_V2_SPEC,
    }
    (out_dir / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_patch_note(out_dir / "patch_note.md", corpus_path, after_path, before_df, after_df, override_counts)
    print(f"Wrote: {after_path}")


if __name__ == "__main__":
    main()
