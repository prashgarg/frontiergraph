from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"

DEFAULT_TOO_BROAD = DATA_DIR / "parent_child_reviewed_too_broad_candidates_v2_2.parquet"
DEFAULT_ONTOLOGY = DATA_DIR / "ontology_v2_2_hierarchy_enriched_canonicalized.json"
DEFAULT_MAPPING = DATA_DIR / "extraction_label_mapping_v2_2_guardrailed_canonicalized.parquet"

DEFAULT_OUT_CANDIDATES = DATA_DIR / "too_broad_intermediate_candidates_v2_2.parquet"
DEFAULT_OUT_ROW_SUMMARY = DATA_DIR / "too_broad_intermediate_row_summary_v2_2.parquet"
DEFAULT_OUT_PARENT_SUMMARY = DATA_DIR / "too_broad_intermediate_parent_summary_v2_2.parquet"
DEFAULT_NOTE = DATA_DIR / "too_broad_intermediate_summary_v2_2.md"

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect reviewed too-broad parent cases and surface candidate missing "
            "intermediate parents from the effective ontology hierarchy."
        )
    )
    parser.add_argument("--too-broad", default=str(DEFAULT_TOO_BROAD))
    parser.add_argument("--ontology-json", default=str(DEFAULT_ONTOLOGY))
    parser.add_argument("--mapping", default=str(DEFAULT_MAPPING))
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--plausible-score-threshold", type=float, default=0.30)
    parser.add_argument("--plausible-jaccard-threshold", type=float, default=0.20)
    parser.add_argument("--out-candidates", default=str(DEFAULT_OUT_CANDIDATES))
    parser.add_argument("--out-row-summary", default=str(DEFAULT_OUT_ROW_SUMMARY))
    parser.add_argument("--out-parent-summary", default=str(DEFAULT_OUT_PARENT_SUMMARY))
    parser.add_argument("--note", default=str(DEFAULT_NOTE))
    return parser.parse_args()


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(value: Any) -> list[str]:
    return [token for token in _normalize_text(value).split() if token and token not in STOPWORDS]


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_support_norm(mapping: pd.DataFrame) -> dict[str, float]:
    if "onto_id" not in mapping.columns:
        return {}
    if "freq" not in mapping.columns:
        agg = mapping.groupby("onto_id", as_index=False).agg(support=("label", "size"))
    else:
        agg = mapping.groupby("onto_id", as_index=False).agg(support=("freq", "sum"))
    if agg.empty:
        return {}
    max_support = float(agg["support"].max())
    denom = math.log1p(max_support) if max_support > 0 else 1.0
    return {
        _clean_str(row.onto_id): float(math.log1p(float(row.support)) / denom) if denom > 0 else 0.0
        for row in agg.itertuples(index=False)
    }


def _score_candidate(
    child_label: str,
    child_tokens: set[str],
    child_domain: str,
    cand_label: str,
    cand_tokens: set[str],
    cand_domain: str,
    cand_support_norm: float,
) -> dict[str, float]:
    token_overlap = len(child_tokens & cand_tokens)
    token_union = len(child_tokens | cand_tokens)
    lexical_jaccard = float(token_overlap / token_union) if token_union > 0 else 0.0
    child_norm = _normalize_text(child_label)
    cand_norm = _normalize_text(cand_label)
    containment_bonus = 1.0 if (cand_norm and child_norm and (cand_norm in child_norm or child_norm in cand_norm)) else 0.0
    domain_bonus = 1.0 if child_domain and cand_domain and (child_domain == cand_domain) else 0.0
    score = (
        0.65 * lexical_jaccard
        + 0.20 * containment_bonus
        + 0.10 * float(cand_support_norm)
        + 0.05 * domain_bonus
    )
    return {
        "score": float(score),
        "lexical_jaccard": float(lexical_jaccard),
        "token_overlap": float(token_overlap),
        "containment_bonus": float(containment_bonus),
        "domain_bonus": float(domain_bonus),
    }


def main() -> None:
    args = parse_args()
    too_broad_path = Path(args.too_broad)
    ontology_path = Path(args.ontology_json)
    mapping_path = Path(args.mapping)
    out_candidates = Path(args.out_candidates)
    out_row_summary = Path(args.out_row_summary)
    out_parent_summary = Path(args.out_parent_summary)
    note_path = Path(args.note)
    top_k = int(args.top_k)
    score_threshold = float(args.plausible_score_threshold)
    jaccard_threshold = float(args.plausible_jaccard_threshold)

    too_broad = pd.read_parquet(too_broad_path).copy()
    ontology_rows = json.loads(ontology_path.read_text(encoding="utf-8"))
    mapping = pd.read_parquet(mapping_path)

    ontology_df = pd.DataFrame(
        [
            {
                "id": _clean_str(row.get("id")),
                "label": _clean_str(row.get("label")),
                "domain": _clean_str(row.get("domain")),
                "source": _clean_str(row.get("source")),
                "effective_parent_id": _clean_str(row.get("effective_parent_id")),
                "effective_parent_label": _clean_str(row.get("effective_parent_label")),
            }
            for row in ontology_rows
        ]
    )
    ontology_df = ontology_df.drop_duplicates("id")
    ontology_df["tokens"] = ontology_df["label"].map(_tokenize)
    ontology_df["token_set"] = ontology_df["tokens"].map(set)

    support_norm = _build_support_norm(mapping)
    ontology_df["support_norm"] = ontology_df["id"].map(lambda cid: float(support_norm.get(str(cid), 0.0)))

    by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ontology_df.itertuples(index=False):
        parent_id = _clean_str(row.effective_parent_id)
        if parent_id:
            by_parent[parent_id].append(
                {
                    "id": _clean_str(row.id),
                    "label": _clean_str(row.label),
                    "domain": _clean_str(row.domain),
                    "token_set": set(row.token_set) if isinstance(row.token_set, set) else set(),
                    "support_norm": float(row.support_norm),
                }
            )

    candidate_rows: list[dict[str, Any]] = []
    row_summary_rows: list[dict[str, Any]] = []
    missing_gap_tokens: Counter[str] = Counter()

    for row in too_broad.itertuples(index=False):
        child_id = _clean_str(getattr(row, "child_id", ""))
        child_label = _clean_str(getattr(row, "child_label", ""))
        child_domain = _clean_str(getattr(row, "child_domain", ""))
        parent_id = _clean_str(getattr(row, "candidate_parent_id", ""))
        parent_label = _clean_str(getattr(row, "candidate_parent_label", ""))
        review_id = _clean_str(getattr(row, "review_id", ""))
        channel = _clean_str(getattr(row, "candidate_channel", ""))
        confidence = _clean_str(getattr(row, "confidence", ""))
        child_weight = _safe_float(getattr(row, "child_mapped_total_freq", 0.0))
        child_tokens = set(_tokenize(child_label))
        parent_tokens = set(_tokenize(parent_label))
        gap_tokens = sorted(list(child_tokens - parent_tokens))

        candidates: list[dict[str, Any]] = []
        for cand in by_parent.get(parent_id, []):
            cand_id = _clean_str(cand["id"])
            if not cand_id or cand_id == child_id or cand_id == parent_id:
                continue
            cand_token_set = set(cand["token_set"])
            token_overlap = len(child_tokens & cand_token_set)
            if token_overlap == 0:
                continue
            score_payload = _score_candidate(
                child_label=child_label,
                child_tokens=child_tokens,
                child_domain=child_domain,
                cand_label=_clean_str(cand["label"]),
                cand_tokens=cand_token_set,
                cand_domain=_clean_str(cand["domain"]),
                cand_support_norm=float(cand["support_norm"]),
            )
            candidates.append(
                {
                    "suggested_intermediate_id": cand_id,
                    "suggested_intermediate_label": _clean_str(cand["label"]),
                    "suggested_intermediate_domain": _clean_str(cand["domain"]),
                    "suggested_intermediate_support_norm": float(cand["support_norm"]),
                    **score_payload,
                }
            )

        candidates = sorted(
            candidates,
            key=lambda item: (
                -float(item["score"]),
                -float(item["lexical_jaccard"]),
                -float(item["suggested_intermediate_support_norm"]),
                _clean_str(item["suggested_intermediate_label"]),
            ),
        )
        top_candidates = candidates[:top_k]

        if not top_candidates:
            status = "missing_intermediate_candidate"
            top_score = 0.0
            top_jaccard = 0.0
            missing_gap_tokens.update(gap_tokens)
            candidate_rows.append(
                {
                    "review_id": review_id,
                    "child_id": child_id,
                    "child_label": child_label,
                    "child_domain": child_domain,
                    "candidate_parent_id": parent_id,
                    "candidate_parent_label": parent_label,
                    "candidate_channel": channel,
                    "confidence": confidence,
                    "child_weight": child_weight,
                    "gap_tokens_json": json.dumps(gap_tokens, ensure_ascii=False),
                    "suggestion_rank": 0,
                    "suggested_intermediate_id": "",
                    "suggested_intermediate_label": "",
                    "suggested_intermediate_domain": "",
                    "suggested_intermediate_support_norm": 0.0,
                    "score": 0.0,
                    "lexical_jaccard": 0.0,
                    "token_overlap": 0.0,
                    "containment_bonus": 0.0,
                    "domain_bonus": 0.0,
                    "status": status,
                }
            )
        else:
            top = top_candidates[0]
            top_score = float(top["score"])
            top_jaccard = float(top["lexical_jaccard"])
            plausible = top_score >= score_threshold and top_jaccard >= jaccard_threshold
            status = "has_plausible_intermediate" if plausible else "low_confidence_intermediate_only"
            if status != "has_plausible_intermediate":
                missing_gap_tokens.update(gap_tokens)
            for rank, candidate in enumerate(top_candidates, start=1):
                candidate_rows.append(
                    {
                        "review_id": review_id,
                        "child_id": child_id,
                        "child_label": child_label,
                        "child_domain": child_domain,
                        "candidate_parent_id": parent_id,
                        "candidate_parent_label": parent_label,
                        "candidate_channel": channel,
                        "confidence": confidence,
                        "child_weight": child_weight,
                        "gap_tokens_json": json.dumps(gap_tokens, ensure_ascii=False),
                        "suggestion_rank": int(rank),
                        "status": status,
                        **candidate,
                    }
                )

        row_summary_rows.append(
            {
                "review_id": review_id,
                "child_id": child_id,
                "child_label": child_label,
                "child_domain": child_domain,
                "candidate_parent_id": parent_id,
                "candidate_parent_label": parent_label,
                "candidate_channel": channel,
                "confidence": confidence,
                "child_weight": child_weight,
                "status": status,
                "top_score": top_score,
                "top_lexical_jaccard": top_jaccard,
                "candidate_count_considered": int(len(candidates)),
                "gap_tokens_json": json.dumps(gap_tokens, ensure_ascii=False),
            }
        )

    candidate_df = pd.DataFrame(candidate_rows)
    row_summary_df = pd.DataFrame(row_summary_rows)

    parent_summary = (
        row_summary_df.groupby(["candidate_parent_id", "candidate_parent_label"], as_index=False)
        .agg(
            cases=("review_id", "size"),
            cases_with_plausible=("status", lambda s: int((s == "has_plausible_intermediate").sum())),
            missing_cases=("status", lambda s: int((s == "missing_intermediate_candidate").sum())),
            low_confidence_cases=("status", lambda s: int((s == "low_confidence_intermediate_only").sum())),
            avg_top_score=("top_score", "mean"),
            weighted_child_mass=("child_weight", "sum"),
        )
    )
    parent_summary["plausible_rate"] = parent_summary["cases_with_plausible"] / parent_summary["cases"].clip(lower=1)
    parent_summary = parent_summary.sort_values(
        ["missing_cases", "low_confidence_cases", "cases", "candidate_parent_label"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    out_candidates.parent.mkdir(parents=True, exist_ok=True)
    out_row_summary.parent.mkdir(parents=True, exist_ok=True)
    out_parent_summary.parent.mkdir(parents=True, exist_ok=True)
    note_path.parent.mkdir(parents=True, exist_ok=True)

    candidate_df.to_parquet(out_candidates, index=False)
    row_summary_df.to_parquet(out_row_summary, index=False)
    parent_summary.to_parquet(out_parent_summary, index=False)

    status_counts = row_summary_df["status"].value_counts().to_dict()
    top_missing = parent_summary.head(25)
    top_gap_tokens = missing_gap_tokens.most_common(30)

    lines = [
        "# Too-Broad Intermediate Parent Inspection (v2.2)",
        "",
        f"- reviewed too-broad rows inspected: `{len(row_summary_df):,}`",
        f"- suggestion rows written: `{len(candidate_df):,}`",
        f"- parents represented: `{parent_summary['candidate_parent_id'].nunique():,}`",
        f"- top-k suggestions per row: `{top_k}`",
        f"- plausible threshold: `score >= {score_threshold:.2f}` and `lexical_jaccard >= {jaccard_threshold:.2f}`",
        "",
        "## Row Status Counts",
        "",
    ]
    for status, count in status_counts.items():
        lines.append(f"- `{status}`: `{int(count):,}`")

    lines.extend(["", "## Parents With Most Missing/Low-Confidence Intermediate Coverage", ""])
    if not top_missing.empty:
        lines.append(top_missing.to_markdown(index=False))

    lines.extend(["", "## Frequent Gap Tokens In Missing/Low-Confidence Cases", ""])
    for token, count in top_gap_tokens:
        lines.append(f"- `{token}`: `{int(count):,}`")

    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote candidate suggestions: {out_candidates}")
    print(f"Wrote row summary: {out_row_summary}")
    print(f"Wrote parent summary: {out_parent_summary}")
    print(f"Wrote summary note: {note_path}")


if __name__ == "__main__":
    main()
