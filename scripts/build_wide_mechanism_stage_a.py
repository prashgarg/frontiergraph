from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from build_current_path_mediator_shortlist import _load_label_map, _render_row


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONTIER = (
    ROOT
    / "outputs"
    / "paper"
    / "61_current_reranked_frontier_v2_1_canonicalized_search_tuned"
    / "current_reranked_frontier.csv"
)
DEFAULT_CONCEPTS = ROOT / "site" / "public" / "data" / "v2" / "central_concepts.csv"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "173_wide_mechanism_stage_a"

MECHANISM_ROUTE_FAMILIES = {"path_question", "mediator_question"}
POOR_LABELING_SNIPPET = "poorly labeled"

FIELD_SHELF_DEFS = [
    {
        "slug": "macro-finance",
        "title": "Macro and finance",
        "match_tokens": [
            "inflation",
            "business cycle",
            "monetary",
            "interest",
            "credit",
            "bank",
            "banking",
            "stock returns",
            "asset prices",
            "financial development",
            "volatility",
            "debt",
            "investment",
        ],
    },
    {
        "slug": "development-urban",
        "title": "Development and urban",
        "match_tokens": [
            "urban",
            "city",
            "housing",
            "development",
            "poverty",
            "migration",
            "institutions",
            "human capital",
            "education",
            "renewable energy",
            "infrastructure",
        ],
    },
    {
        "slug": "trade-globalization",
        "title": "Trade and globalization",
        "match_tokens": [
            "trade",
            "export",
            "import",
            "fdi",
            "globalization",
            "sanctions",
            "tariff",
            "international",
        ],
    },
    {
        "slug": "climate-energy",
        "title": "Climate and energy",
        "match_tokens": [
            "carbon",
            "co2",
            "emissions",
            "pollution",
            "environment",
            "environmental",
            "climate",
            "energy",
            "oil",
            "gas",
            "electricity",
            "renewable",
            "green finance",
            "ecological footprint",
        ],
    },
    {
        "slug": "innovation-productivity",
        "title": "Innovation and productivity",
        "match_tokens": [
            "innovation",
            "technology",
            "technological",
            "digital",
            "productivity",
            "r&d",
            "research and development",
            "patent",
            "firm productivity",
            "digital transformation",
            "industrial upgrading",
        ],
    },
    {
        "slug": "labor-household-outcomes",
        "title": "Labor and household outcomes",
        "match_tokens": [
            "employment",
            "wage",
            "labor",
            "income inequality",
            "income distribution",
            "consumption",
            "household",
            "health",
            "fertility",
            "job",
            "earnings",
        ],
    },
]

THEME_TO_FIELDS = {
    "environment_climate": ["climate-energy"],
    "innovation_technology": ["innovation-productivity"],
    "macro_cycle_prices": ["macro-finance"],
    "finance_tax": ["macro-finance"],
    "labor_income_demand": ["labor-household-outcomes"],
    "trade_urban_structure": ["development-urban", "trade-globalization"],
    "uncertainty_risk": ["macro-finance"],
}

GENERIC_ENDPOINT_PATTERNS = (
    r"\bwillingness to pay\b",
    r"\bprice changes?\b",
    r"\bregional heterogeneity\b",
    r"\brate of growth\b",
    r"\bmistake\b",
)

BLOCKED_ENDPOINT_PATTERNS = (
    r"\bstate of emergency\b",
    r"\boutline of\b",
    r"\bregional variation\b",
    r"\bspillover effect\b",
    r"\bnonstop\b",
    r"\bpopulation size\b",
    r"\bhigh income countries\b",
    r"\batmospheric emissions\b",
    r"\bnegative carbon dioxide emission\b",
    r"\bindicators?\b",
    r"\bindex\b",
    r"\bhypothesis\b",
)

BLOCKED_MEDIATOR_PATTERNS = (
    r"\bgranger causality\b",
    r"\bhedonic model\b",
    r"\bquantile regression\b",
    r"\bregression\b",
    r"\bmodel\b",
    r"\bindex\b",
    r"\btest\b",
    r"\bshort run\b",
    r"\blong run\b",
    r"\bhypothesis\b",
    r"\bworldwide governance indicators\b",
    r"\bair quality index\b",
)

GENERIC_MEDIATOR_TERMS = {
    "government",
    "finance",
    "trade",
    "technology",
    "innovation",
    "industry",
    "labor",
    "investment",
    "economic development",
    "economic growth",
    "capital",
    "regulations",
    "institutions",
}

GENERIC_ENDPOINT_TERMS = {
    "growth",
    "technology",
    "innovation",
    "finance",
    "trade",
    "government",
    "investment",
    "consumption",
}

MIN_STAGE_A_SCORE = 0.48


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a wide, deterministically scored mechanism pool for website curation.")
    parser.add_argument("--frontier-csv", default=str(DEFAULT_FRONTIER), dest="frontier_csv")
    parser.add_argument("--concepts-csv", default=str(DEFAULT_CONCEPTS), dest="concepts_csv")
    parser.add_argument("--candidate-pool-per-horizon", type=int, default=10000, dest="candidate_pool_per_horizon")
    parser.add_argument("--min-score", type=float, default=MIN_STAGE_A_SCORE, dest="min_score")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    return parser.parse_args()


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9& ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    alias_map = {
        "fdi": "fdi",
        "r d": "r&d",
        "co2 emissions": "carbon emissions",
        "co2 emission": "carbon emissions",
        "green innovation": "green innovation",
        "digital economy": "digital economy",
        "industrial structure upgrading": "industrial upgrading",
    }
    return alias_map.get(text, text)


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def is_codeish(value: Any) -> bool:
    text = clean_text(value)
    if not text:
        return True
    if re.search(r"^(FG3C|FGV|Q\d+|wp:\d+|jel:|https?://)", text):
        return True
    if re.search(r"[A-Z]{4,}\d{2,}", text):
        return True
    return False


def is_generic_endpoint(label: Any) -> bool:
    text = normalize_text(label)
    if any(re.search(pattern, text) for pattern in GENERIC_ENDPOINT_PATTERNS):
        return True
    return text in GENERIC_ENDPOINT_TERMS


def is_blocked_endpoint(label: Any) -> bool:
    text = normalize_text(label)
    return any(re.search(pattern, text) for pattern in BLOCKED_ENDPOINT_PATTERNS)


def is_blocked_mediator(label: Any) -> bool:
    text = normalize_text(label)
    if any(re.search(pattern, text) for pattern in BLOCKED_MEDIATOR_PATTERNS):
        return True
    return text in GENERIC_MEDIATOR_TERMS


def token_count(label: Any) -> int:
    text = normalize_text(label)
    return len([tok for tok in text.split(" ") if tok])


def label_quality_score(label: Any, endpoint_flag_count: int = 0, endpoint_mode: bool = True) -> float:
    score = 1.0
    text = normalize_text(label)
    if is_codeish(label):
        score -= 0.55
    if endpoint_mode and is_blocked_endpoint(label):
        score -= 0.55
    if endpoint_mode and is_generic_endpoint(label):
        score -= 0.30
    if not endpoint_mode and is_blocked_mediator(label):
        score -= 0.45
    if token_count(text) <= 1 and text:
        score -= 0.08 if endpoint_mode else 0.15
    if endpoint_mode and int(endpoint_flag_count or 0) > 0:
        score -= min(0.25, 0.08 * int(endpoint_flag_count or 0))
    return max(0.0, min(1.0, score))


def parse_label_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean_text(x) for x in value if clean_text(x)]
    text = clean_text(value)
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [clean_text(x) for x in parsed if clean_text(x)]
    except json.JSONDecodeError:
        pass
    return []


def assign_fields(row: pd.Series) -> list[dict[str, Any]]:
    endpoint_text = normalize_text(f"{row.get('source_label', '')} {row.get('target_label', '')}")
    mediator_text = normalize_text(" ".join(parse_label_list(row.get("primary_mediator_labels"))))
    endpoint_matches: list[str] = []
    mediator_matches: list[str] = []
    for field_def in FIELD_SHELF_DEFS:
        slug = str(field_def["slug"])
        tokens = [normalize_text(tok) for tok in field_def["match_tokens"]]
        endpoint_match = any(tok and tok in endpoint_text for tok in tokens)
        mediator_match = any(tok and tok in mediator_text for tok in tokens)
        if endpoint_match:
            endpoint_matches.append(slug)
        if mediator_match:
            mediator_matches.append(slug)

    rows: list[dict[str, Any]] = []
    preferred = sorted(set(endpoint_matches))
    if preferred:
        for slug in preferred:
            rows.append(
                {
                    "field_slug": slug,
                    "field_assignment_source": "endpoint_and_mediator" if slug in mediator_matches else "endpoint_only",
                    "field_endpoint_match": True,
                    "field_mediator_match": slug in mediator_matches,
                }
            )
        return rows

    if mediator_matches:
        for slug in sorted(set(mediator_matches)):
            rows.append(
                {
                    "field_slug": slug,
                    "field_assignment_source": "mediator_only",
                    "field_endpoint_match": False,
                    "field_mediator_match": True,
                }
            )
        return rows

    fallback: list[str] = []
    for theme in [clean_text(row.get("source_theme")), clean_text(row.get("target_theme"))]:
        fallback.extend(THEME_TO_FIELDS.get(theme, []))
    for slug in sorted(set(fallback)):
        rows.append(
            {
                "field_slug": slug,
                "field_assignment_source": "theme_fallback",
                "field_endpoint_match": False,
                "field_mediator_match": False,
            }
        )
    if rows:
        return rows

    return [
        {
            "field_slug": "other",
            "field_assignment_source": "other",
            "field_endpoint_match": False,
            "field_mediator_match": False,
        }
    ]


def merge_duplicate_pairs(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, sub in df.groupby("pair_key", sort=False):
        ordered = sub.sort_values(
            ["surface_rank", "reranker_rank", "transparent_rank", "horizon"],
            ascending=[True, True, True, False],
        ).reset_index(drop=True)
        best = ordered.iloc[0].to_dict()
        best["available_horizons"] = json_dumps(sorted(set(int(x) for x in ordered["horizon"].tolist())))
        best["available_route_families"] = json_dumps(sorted(set(str(x) for x in ordered["route_family"].tolist())))
        best["pair_horizon_count"] = int(len(ordered))
        best["best_horizon"] = int(ordered["horizon"].min())
        rows.append(best)
    return pd.DataFrame(rows)


def compute_scores(df: pd.DataFrame, min_score: float) -> pd.DataFrame:
    work = df.copy()
    work["primary_mediator_labels"] = work["primary_mediator_labels"].apply(parse_label_list)
    work["primary_mediator_count"] = work["primary_mediator_labels"].apply(len)
    work["primary_clean_channel_count"] = work["primary_mediator_labels"].apply(
        lambda items: int(sum(1 for label in items if label_quality_score(label, endpoint_mode=False) >= 0.55))
    )
    work["primary_blocked_channel_count"] = work["primary_mediator_labels"].apply(
        lambda items: int(sum(1 for label in items if is_blocked_mediator(label) or is_codeish(label)))
    )
    work["primary_resolved_share"] = work.apply(
        lambda row: float(row["primary_clean_channel_count"]) / float(max(int(row["primary_mediator_count"]), 1)),
        axis=1,
    )
    work["source_label_score"] = work.apply(
        lambda row: label_quality_score(row["source_label"], int(row.get("u_endpoint_flag_count", 0) or 0), endpoint_mode=True),
        axis=1,
    )
    work["target_label_score"] = work.apply(
        lambda row: label_quality_score(row["target_label"], int(row.get("v_endpoint_flag_count", 0) or 0), endpoint_mode=True),
        axis=1,
    )
    work["endpoint_specificity_score"] = (work["source_label_score"] + work["target_label_score"]) / 2.0
    work["channel_specificity_score"] = work["primary_mediator_labels"].apply(
        lambda items: float(sum(label_quality_score(label, endpoint_mode=False) for label in items)) / float(max(len(items), 1))
    )
    work.loc[work["primary_mediator_count"] < 2, "channel_specificity_score"] *= 0.8
    shared_core_token = []
    stop = {"of", "the", "and", "per", "total", "factor"}
    for row in work.itertuples(index=False):
        source_tokens = {tok for tok in normalize_text(row.source_label).split() if tok and tok not in stop}
        target_tokens = {tok for tok in normalize_text(row.target_label).split() if tok and tok not in stop}
        shared = source_tokens & target_tokens
        shared_core_token.append(int(len(shared) > 0))
    work["endpoint_overlap_flag"] = shared_core_token
    work["specificity_score"] = (
        0.55 * work["endpoint_specificity_score"] + 0.45 * work["channel_specificity_score"]
    ).clip(0.0, 1.0)
    work.loc[work["endpoint_overlap_flag"] == 1, "specificity_score"] *= 0.88

    title_len_ok = (
        work["display_title"].astype(str).str.len().between(45, 140, inclusive="both").astype(float) * 0.5 + 0.5
    )
    poor_labeling = work["display_why"].astype(str).str.contains(POOR_LABELING_SNIPPET, case=False, na=False)
    work["poor_labeling_flag"] = poor_labeling.astype(int)
    work["clarity_score"] = (
        0.45 * work["endpoint_specificity_score"]
        + 0.30 * work["primary_resolved_share"].clip(0.0, 1.0)
        + 0.15 * (~poor_labeling).astype(float)
        + 0.10 * title_len_ok
    ).clip(0.0, 1.0)

    reranker_pct = work.get("reranker_pct")
    if reranker_pct is None:
        work["reranker_pct"] = 1.0 - (work["surface_rank"].rank(method="average", pct=True) - 0.000001)
    else:
        work["reranker_pct"] = pd.to_numeric(reranker_pct, errors="coerce").fillna(0.0).clip(0.0, 1.0)
    work["supporting_path_pct"] = pd.to_numeric(work["supporting_path_count"], errors="coerce").rank(
        method="average", pct=True
    )
    work["cooc_pct"] = pd.to_numeric(work["cooc_count"], errors="coerce").fillna(0.0).rank(method="average", pct=True)
    work["route_bonus"] = work["route_family"].astype(str).map({"mediator_question": 1.0, "path_question": 0.88}).fillna(0.75)
    work["plausibility_score"] = (
        0.55 * work["reranker_pct"]
        + 0.20 * work["supporting_path_pct"]
        + 0.15 * work["cooc_pct"]
        + 0.10 * work["route_bonus"]
    ).clip(0.0, 1.0)
    work["stage_a_score"] = (
        0.40 * work["plausibility_score"] + 0.30 * work["clarity_score"] + 0.30 * work["specificity_score"]
    ).clip(0.0, 1.0)

    work["field_memberships"] = work.apply(assign_fields, axis=1)
    work["field_shelves"] = work["field_memberships"].apply(lambda rows: [str(row["field_slug"]) for row in rows])
    work["field_shelf_count"] = work["field_shelves"].apply(len)
    work["cross_theme_flag"] = (
        work["source_theme"].fillna("").astype(str) != work["target_theme"].fillna("").astype(str)
    ).astype(int)

    def _assign_use_cases(row: pd.Series) -> list[str]:
        tags: list[str] = []
        if float(row["plausibility_score"]) >= 0.82 and int(row["primary_clean_channel_count"]) >= 2:
            tags.append("strong-nearby-evidence")
        elif float(row["reranker_pct"]) >= 0.90 and float(row["specificity_score"]) >= 0.62:
            tags.append("strong-nearby-evidence")
        if (
            (
                int(row["field_shelf_count"]) >= 2
                and int(row["primary_clean_channel_count"]) >= 2
            )
            or int(row["primary_clean_channel_count"]) >= 3
            or (
                int(row["mediator_count"]) >= 4
                and float(row["supporting_path_pct"]) >= 0.55
            )
        ):
            tags.append("phd-topic")
        if float(row["cooc_pct"]) <= 0.22 or (
            float(row["supporting_path_pct"]) <= 0.25 and float(row["clarity_score"]) >= 0.60
        ):
            tags.append("open-little-direct")
        if int(row["cross_theme_flag"]) == 1 or int(row["field_shelf_count"]) >= 2:
            tags.append("cross-area-mechanism")
        if (
            float(row["clarity_score"]) >= 0.80
            and float(row["specificity_score"]) >= 0.74
            and int(row["primary_clean_channel_count"]) >= 2
        ):
            tags.append("paper-ready")
        if not tags:
            tags.append("phd-topic" if float(row["stage_a_score"]) >= 0.60 else "open-little-direct")
        return tags

    work["collection_tags"] = work.apply(_assign_use_cases, axis=1)
    work["primary_use_case"] = work["collection_tags"].apply(
        lambda tags: next((tag for tag in tags if tag in {"strong-nearby-evidence", "phd-topic", "open-little-direct"}), tags[0])
    )

    family_counts = work["semantic_family_key"].astype(str).value_counts()
    theme_pair_counts = work["theme_pair_key"].astype(str).value_counts()
    source_counts = work["source_family"].astype(str).value_counts()
    target_counts = work["target_family"].astype(str).value_counts()
    work["semantic_family_duplicate_count"] = work["semantic_family_key"].astype(str).map(family_counts).fillna(0).astype(int)
    work["theme_pair_duplicate_count"] = work["theme_pair_key"].astype(str).map(theme_pair_counts).fillna(0).astype(int)
    work["source_family_duplicate_count"] = work["source_family"].astype(str).map(source_counts).fillna(0).astype(int)
    work["target_family_duplicate_count"] = work["target_family"].astype(str).map(target_counts).fillna(0).astype(int)
    work["duplicate_family_flag"] = (work["semantic_family_duplicate_count"] > 1).astype(int)

    keep_flags: list[bool] = []
    keep_reasons: list[str] = []
    drop_reasons: list[str] = []
    for row in work.itertuples(index=False):
        reasons: list[str] = []
        if int(row.poor_labeling_flag) == 1:
            reasons.append("poorly_labeled")
        if float(row.source_label_score) < 0.50:
            reasons.append("weak_source_endpoint")
        if float(row.target_label_score) < 0.50:
            reasons.append("weak_target_endpoint")
        if int(row.primary_clean_channel_count) == 0:
            reasons.append("no_clean_channels")
        elif int(row.primary_clean_channel_count) == 1:
            reasons.append("only_one_clean_channel")
        if int(row.primary_blocked_channel_count) >= max(1, int(row.primary_mediator_count)):
            reasons.append("method_heavy_channels")
        if float(row.clarity_score) < 0.50:
            reasons.append("low_clarity")
        if float(row.specificity_score) < 0.50:
            reasons.append("low_specificity")
        if float(row.plausibility_score) < 0.35:
            reasons.append("low_plausibility")
        if float(row.stage_a_score) < float(min_score):
            reasons.append("below_stage_a_score_cut")

        hard_fail = any(
            key in reasons
            for key in [
                "poorly_labeled",
                "weak_source_endpoint",
                "weak_target_endpoint",
                "no_clean_channels",
                "method_heavy_channels",
            ]
        )
        keep = not hard_fail and float(row.stage_a_score) >= float(min_score)
        if keep and reasons == ["only_one_clean_channel"]:
            reasons = []
        keep_flags.append(keep)
        keep_reasons.append(";".join(sorted(set(reasons))) if keep else "")
        drop_reasons.append("" if keep else ";".join(sorted(set(reasons))))

    work["stage_a_keep"] = keep_flags
    work["stage_a_keep_reason"] = keep_reasons
    work["stage_a_drop_reason"] = drop_reasons
    return work


def build_field_pool(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    exploded = work.explode("field_memberships").reset_index(drop=True)
    memberships = exploded["field_memberships"].apply(pd.Series)
    return pd.concat([exploded.drop(columns=["field_memberships"]), memberships], axis=1)


def build_use_case_pool(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["collection_tag"] = work["collection_tags"]
    exploded = work.explode("collection_tag").reset_index(drop=True)
    return exploded


def render_rows(frontier_df: pd.DataFrame, label_map: dict[str, str], candidate_pool_per_horizon: int) -> pd.DataFrame:
    rendered_rows: list[dict[str, Any]] = []
    keep_cols = [
        "u",
        "v",
        "frontier_rank",
        "cooc_count",
        "reranker_pct",
        "support_age_years",
        "recent_support_age_years",
        "nearby_closure_density",
        "u_endpoint_flag_count",
        "v_endpoint_flag_count",
        "u_endpoint_flags",
        "v_endpoint_flags",
        "source_mean_fwci",
        "target_mean_fwci",
        "pair_mean_fwci",
    ]
    for horizon in sorted(frontier_df["horizon"].dropna().astype(int).unique()):
        sub = frontier_df[frontier_df["horizon"].astype(int) == int(horizon)].nsmallest(
            int(candidate_pool_per_horizon), "surface_rank"
        )
        for _, row in sub.iterrows():
            rendered = _render_row(row, label_map)
            if clean_text(rendered.get("route_family")) not in MECHANISM_ROUTE_FAMILIES:
                continue
            for col in keep_cols:
                rendered[col] = row.get(col)
            rendered_rows.append(rendered)
    return pd.DataFrame(rendered_rows)


def write_outputs(
    raw_df: pd.DataFrame,
    scored_df: pd.DataFrame,
    kept_df: pd.DataFrame,
    field_pool: pd.DataFrame,
    use_case_pool: pd.DataFrame,
    out_dir: Path,
    args: argparse.Namespace,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_df.to_csv(out_dir / "wide_mechanism_raw.csv", index=False)
    scored_df.to_csv(out_dir / "wide_mechanism_stage_a_scored.csv", index=False)
    kept_df.to_csv(out_dir / "wide_mechanism_stage_a_kept.csv", index=False)
    field_pool.to_csv(out_dir / "wide_mechanism_field_shelf_pool.csv", index=False)
    use_case_pool.to_csv(out_dir / "wide_mechanism_use_case_pool.csv", index=False)

    manifest = {
        "frontier_csv": str(args.frontier_csv),
        "concepts_csv": str(args.concepts_csv),
        "candidate_pool_per_horizon": int(args.candidate_pool_per_horizon),
        "min_score": float(args.min_score),
        "n_raw_rows": int(len(raw_df)),
        "n_scored_rows": int(len(scored_df)),
        "n_kept_rows": int(len(kept_df)),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Wide Mechanism Stage A",
        "",
        f"- raw mechanism rows after route filtering: {len(raw_df):,}",
        f"- unique pair rows after horizon collapse: {len(scored_df):,}",
        f"- Stage A kept rows: {len(kept_df):,}",
        "",
        "## Route family mix",
        "",
    ]
    for route, count in scored_df["route_family"].astype(str).value_counts().items():
        lines.append(f"- {route}: {int(count):,}")

    lines.extend(["", "## Field shelf counts (kept)", ""])
    for field_slug, count in field_pool["field_slug"].astype(str).value_counts().items():
        lines.append(f"- {field_slug}: {int(count):,}")

    lines.extend(["", "## Use-case counts (kept)", ""])
    for tag, count in use_case_pool["collection_tag"].astype(str).value_counts().items():
        lines.append(f"- {tag}: {int(count):,}")

    lines.extend(["", "## Top kept candidates", ""])
    top_kept = kept_df.sort_values(["stage_a_score", "surface_rank"], ascending=[False, True]).head(20)
    for row in top_kept.itertuples(index=False):
        lines.append(
            f"- {row.display_title} | score={float(row.stage_a_score):.3f} | fields={', '.join(row.field_shelves)} | use-cases={', '.join(row.collection_tags)}"
        )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    label_map = _load_label_map(args.concepts_csv)
    frontier_df = pd.read_csv(args.frontier_csv, low_memory=False)

    raw_rendered_df = render_rows(frontier_df, label_map, int(args.candidate_pool_per_horizon))
    merged_df = merge_duplicate_pairs(raw_rendered_df)
    scored_df = compute_scores(merged_df, min_score=float(args.min_score))
    kept_df = (
        scored_df[scored_df["stage_a_keep"]]
        .copy()
        .sort_values(["stage_a_score", "surface_rank"], ascending=[False, True])
        .reset_index(drop=True)
    )
    field_pool = build_field_pool(kept_df)
    use_case_pool = build_use_case_pool(kept_df)
    write_outputs(raw_rendered_df, scored_df, kept_df, field_pool, use_case_pool, out_dir, args)
    print(f"Wrote {out_dir}")


if __name__ == "__main__":
    main()
