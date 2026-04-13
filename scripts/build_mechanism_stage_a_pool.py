from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from build_current_path_mediator_shortlist import _load_label_map, _render_row


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONTIER = ROOT / "outputs" / "paper" / "61_current_reranked_frontier_v2_1_canonicalized_search_tuned" / "current_reranked_frontier.csv"
DEFAULT_CONCEPTS = ROOT / "site" / "public" / "data" / "v2" / "central_concepts.csv"
DEFAULT_OUT = ROOT / "outputs" / "paper" / "173_mechanism_stage_a_pool"

GENERIC_ENDPOINT_PATTERNS = (
    r"\bwillingness to pay\b",
    r"\bprice changes?\b",
    r"\bregional heterogeneity\b",
    r"\becological footprint\b",
    r"\brate of growth\b",
    r"\bsustainability\b",
    r"\bsustainable development\b",
    r"\binnovation outcomes\b",
    r"\binnovation outcome\b",
)

BLOCKED_MEDIATOR_PATTERNS = (
    r"\bgranger causality\b",
    r"\bhedonic model\b",
    r"\bquantile regression\b",
    r"\bregression\b",
    r"\btest\b",
    r"\bmodel\b",
    r"\bindex\b",
    r"\bshort run\b",
    r"\blong run\b",
    r"\bstatistical\b",
)

CLIMATE_PATTERNS = (
    r"\bcarbon\b",
    r"\bco2\b",
    r"\bemissions?\b",
    r"\bclimate\b",
    r"\benvironment",
    r"\bpollution\b",
    r"\becolog",
    r"\bgreen\b",
    r"\brenewable\b",
    r"\benergy\b",
    r"\bsustainab",
)
INNOVATION_PATTERNS = (r"\binnovation\b", r"\btechnolog", r"\bdigital\b", r"\bproductivity\b", r"\br&d\b", r"\bresearch and development\b")
MACRO_PATTERNS = (r"\bbusiness cycle\b", r"\binflation\b", r"\boutput\b", r"\bmonetary\b", r"\binterest rate", r"\bgdp\b", r"\bpolicy uncertainty\b")
FINANCE_PATTERNS = (r"\bfinancial\b", r"\bfinance\b", r"\bdebt\b", r"\bbank", r"\bcredit\b", r"\basset", r"\bstock returns?\b", r"\btax\b")
LABOR_PATTERNS = (r"\bemployment\b", r"\bunemployment\b", r"\bwage", r"\bincome inequality\b", r"\bhousehold\b", r"\bconsumption\b", r"\blabor\b")
DEVELOPMENT_URBAN_PATTERNS = (r"\burban", r"\bcity\b", r"\bhousing\b", r"\bregional\b", r"\bpoverty\b", r"\bdevelopment\b", r"\bmicrofinance\b", r"\bcatastrophic health spending\b", r"\bhigh-speed rail\b")
TRADE_PATTERNS = (r"\btrade\b", r"\bexport", r"\bimport", r"\bglobal", r"\btariff", r"\bexchange-rate", r"\bexchange rate", r"\bfree trade\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a wide deterministic Stage A mechanism pool from the current reranked frontier.")
    parser.add_argument("--frontier-csv", default=str(DEFAULT_FRONTIER), dest="frontier_csv")
    parser.add_argument("--concepts-csv", default=str(DEFAULT_CONCEPTS), dest="concepts_csv")
    parser.add_argument("--out", default=str(DEFAULT_OUT), dest="out_dir")
    parser.add_argument("--candidate-pool-per-horizon", type=int, default=10000, dest="candidate_pool_per_horizon")
    parser.add_argument("--field-cap", type=int, default=300, dest="field_cap")
    parser.add_argument("--use-case-cap", type=int, default=300, dest="use_case_cap")
    return parser.parse_args()


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_text(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_listish(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [clean_text(item) for item in raw if clean_text(item)]
    text = clean_text(raw)
    if not text:
        return []
    for parser in (json.loads,):
        try:
            value = parser(text)
            if isinstance(value, list):
                return [clean_text(item) for item in value if clean_text(item)]
        except Exception:
            continue
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
        parts = [part.strip().strip("'").strip('"') for part in inner.split(",")]
        return [clean_text(item) for item in parts if clean_text(item)]
    return []


def matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def endpoint_generic(label: str) -> bool:
    return matches_any(normalize_text(label), GENERIC_ENDPOINT_PATTERNS)


def channel_blocked(label: str) -> bool:
    return matches_any(normalize_text(label), BLOCKED_MEDIATOR_PATTERNS)


def theme_flag(texts: list[str], patterns: tuple[str, ...]) -> bool:
    return any(matches_any(normalize_text(text), patterns) for text in texts)


def assign_field_shelves(row: pd.Series) -> list[str]:
    texts = [
        clean_text(row.get("source_label")),
        clean_text(row.get("target_label")),
        *parse_listish(row.get("primary_mediator_labels")),
    ]
    shelves: list[str] = []
    if theme_flag(texts, CLIMATE_PATTERNS):
        shelves.append("climate-energy")
    if theme_flag(texts, MACRO_PATTERNS) or theme_flag(texts, FINANCE_PATTERNS):
        shelves.append("macro-finance")
    if theme_flag(texts, LABOR_PATTERNS):
        shelves.append("labor-household-outcomes")
    if theme_flag(texts, DEVELOPMENT_URBAN_PATTERNS):
        shelves.append("development-urban")
    if theme_flag(texts, TRADE_PATTERNS):
        shelves.append("trade-globalization")
    if theme_flag(texts, INNOVATION_PATTERNS):
        shelves.append("innovation-productivity")
    if not shelves:
        theme_map = {
            "environment_climate": "climate-energy",
            "macro_cycle_prices": "macro-finance",
            "finance_tax": "macro-finance",
            "labor_income_demand": "labor-household-outcomes",
            "trade_urban_structure": "development-urban",
            "innovation_technology": "innovation-productivity",
        }
        for key in [row.get("source_theme"), row.get("target_theme")]:
            mapped = theme_map.get(clean_text(key))
            if mapped and mapped not in shelves:
                shelves.append(mapped)
    return shelves


def assign_use_case_tags(row: pd.Series) -> list[str]:
    tags: list[str] = []
    supporting_path_count = int(row.get("supporting_path_count", 0) or 0)
    mediator_count = int(row.get("mediator_count", 0) or 0)
    cooc_count = int(row.get("cooc_count", 0) or 0)
    source_theme = clean_text(row.get("source_theme"))
    target_theme = clean_text(row.get("target_theme"))
    overall_score = float(row.get("stage_a_overall_score", 0.0) or 0.0)
    if supporting_path_count >= 6 or float(row.get("transparent_score", 0.0) or 0.0) >= 0.19:
        tags.append("strong-nearby-evidence")
    if mediator_count >= 6 or supporting_path_count >= 8:
        tags.append("broader-project")
    if cooc_count <= 1:
        tags.append("open-little-direct")
    if source_theme and target_theme and source_theme != target_theme:
        tags.append("cross-area-mechanism")
    if overall_score >= 70 and supporting_path_count >= 2:
        tags.append("paper-ready")
    return tags


def score_row(row: pd.Series) -> pd.Series:
    source = clean_text(row.get("source_label"))
    target = clean_text(row.get("target_label"))
    channels = parse_listish(row.get("primary_mediator_labels"))
    unresolved_channels = sum(1 for channel in channels if channel.startswith("FG3C") or "http" in channel.lower())
    generic_channels = sum(1 for channel in channels if channel_blocked(channel))
    concrete_channels = max(len(channels) - unresolved_channels - generic_channels, 0)
    generic_endpoint_count = int(endpoint_generic(source)) + int(endpoint_generic(target))
    endpoint_specificity = max(0.0, 5.0 - 1.5 * generic_endpoint_count)
    if len(normalize_text(source).split()) >= 2:
        endpoint_specificity += 0.5
    if len(normalize_text(target).split()) >= 2:
        endpoint_specificity += 0.5
    endpoint_specificity = min(endpoint_specificity, 5.0)

    channel_specificity = 1.0
    if channels:
        channel_specificity += min(concrete_channels, 3) * 1.2
        channel_specificity -= min(generic_channels, 2) * 0.7
        channel_specificity -= min(unresolved_channels, 2) * 0.9
    channel_specificity = max(0.0, min(channel_specificity, 5.0))

    support_strength = 1.0
    support_strength += min(int(row.get("supporting_path_count", 0) or 0), 8) * 0.35
    support_strength += min(int(row.get("mediator_count", 0) or 0), 8) * 0.15
    support_strength = max(0.0, min(support_strength, 5.0))

    clarity = 1.5
    if clean_text(row.get("route_family")) in {"path_question", "mediator_question"}:
        clarity += 1.0
    if concrete_channels >= 1:
        clarity += 1.0
    if generic_endpoint_count == 0:
        clarity += 0.8
    if generic_channels == 0:
        clarity += 0.7
    clarity = max(0.0, min(clarity, 5.0))

    plausibility = max(0.0, min((support_strength * 0.55) + (channel_specificity * 0.45), 5.0))
    overall = ((endpoint_specificity * 0.25) + (channel_specificity * 0.25) + (clarity * 0.25) + (plausibility * 0.25)) * 20.0

    hard_drop_reasons: list[str] = []
    if clean_text(row.get("route_family")) not in {"path_question", "mediator_question"}:
        hard_drop_reasons.append("not_mechanism_route")
    if generic_endpoint_count >= 2:
        hard_drop_reasons.append("both_endpoints_too_generic")
    if len(channels) == 0:
        hard_drop_reasons.append("no_primary_channels")
    if concrete_channels == 0:
        hard_drop_reasons.append("no_concrete_channels")
    if int(row.get("supporting_path_count", 0) or 0) <= 0 and int(row.get("mediator_count", 0) or 0) <= 1:
        hard_drop_reasons.append("weak_local_support")

    return pd.Series(
        {
            "primary_channel_count": len(channels),
            "unresolved_channel_count": unresolved_channels,
            "generic_channel_count": generic_channels,
            "concrete_channel_count": concrete_channels,
            "generic_endpoint_count": generic_endpoint_count,
            "stage_a_endpoint_specificity": round(endpoint_specificity, 3),
            "stage_a_channel_specificity": round(channel_specificity, 3),
            "stage_a_support_strength": round(support_strength, 3),
            "stage_a_clarity": round(clarity, 3),
            "stage_a_plausibility": round(plausibility, 3),
            "stage_a_overall_score": round(overall, 3),
            "stage_a_hard_drop": bool(hard_drop_reasons),
            "stage_a_hard_drop_reasons": ";".join(hard_drop_reasons),
        }
    )


def dedupe_across_horizon(df: pd.DataFrame) -> pd.DataFrame:
    work = df.sort_values(
        [
            "stage_a_hard_drop",
            "stage_a_overall_score",
            "supporting_path_count",
            "surface_rank",
            "horizon",
        ],
        ascending=[True, False, False, True, False],
    ).copy()
    work["pair_key_seen_before"] = work.groupby("pair_key").cumcount()
    return work[work["pair_key_seen_before"] == 0].copy()


def add_duplicate_flags(df: pd.DataFrame) -> pd.DataFrame:
    work = df.sort_values(["surface_rank", "reranker_rank", "transparent_rank"]).copy()
    work["semantic_family_seen_before"] = work.groupby("semantic_family_key").cumcount()
    work["theme_pair_seen_before_stage_a"] = work.groupby("theme_pair_key").cumcount()
    work["source_family_seen_before_stage_a"] = work.groupby("source_family").cumcount()
    work["target_family_seen_before_stage_a"] = work.groupby("target_family").cumcount()
    work["duplicate_family_flag"] = work["semantic_family_seen_before"] > 0
    work["duplicate_theme_pair_flag"] = work["theme_pair_seen_before_stage_a"] > 2
    work["duplicate_endpoint_family_flag"] = (
        (work["source_family_seen_before_stage_a"] > 3) | (work["target_family_seen_before_stage_a"] > 3)
    )
    return work


def build_stage_a_recommended(df: pd.DataFrame, field_cap: int, use_case_cap: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eligible = df[~df["stage_a_hard_drop"]].copy()
    eligible = eligible.sort_values(
        [
            "stage_a_overall_score",
            "stage_a_plausibility",
            "supporting_path_count",
            "surface_rank",
        ],
        ascending=[False, False, False, True],
    ).copy()
    eligible["field_shelves"] = eligible.apply(assign_field_shelves, axis=1)
    eligible["use_case_tags"] = eligible.apply(assign_use_case_tags, axis=1)
    eligible["keep_for_mini_initial"] = (
        (eligible["stage_a_overall_score"] >= 45.0)
        & (eligible["stage_a_clarity"] >= 2.5)
        & (eligible["concrete_channel_count"] >= 1)
    )
    field_rows: list[pd.DataFrame] = []
    for shelf in [
        "macro-finance",
        "development-urban",
        "trade-globalization",
        "climate-energy",
        "innovation-productivity",
        "labor-household-outcomes",
    ]:
        sub = eligible[
            eligible["keep_for_mini_initial"] & eligible["field_shelves"].apply(lambda values: shelf in values)
        ].head(field_cap).copy()
        sub["selected_shelf"] = shelf
        field_rows.append(sub)
    field_pool = pd.concat(field_rows, ignore_index=True) if field_rows else eligible.head(0).copy()

    use_case_rows: list[pd.DataFrame] = []
    for tag in [
        "strong-nearby-evidence",
        "broader-project",
        "open-little-direct",
        "cross-area-mechanism",
        "paper-ready",
    ]:
        sub = eligible[
            eligible["keep_for_mini_initial"] & eligible["use_case_tags"].apply(lambda values: tag in values)
        ].head(use_case_cap).copy()
        sub["selected_use_case"] = tag
        use_case_rows.append(sub)
    use_case_pool = pd.concat(use_case_rows, ignore_index=True) if use_case_rows else eligible.head(0).copy()

    mini_pairs = set(field_pool["pair_key"]).union(set(use_case_pool["pair_key"]))
    mini_pool = eligible[eligible["pair_key"].isin(mini_pairs)].copy()
    mini_pool = mini_pool.sort_values(
        [
            "stage_a_overall_score",
            "stage_a_plausibility",
            "supporting_path_count",
            "surface_rank",
        ],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    return eligible, field_pool, use_case_pool, mini_pool


def write_summary(
    raw_df: pd.DataFrame,
    deduped_df: pd.DataFrame,
    eligible_df: pd.DataFrame,
    field_pool: pd.DataFrame,
    use_case_pool: pd.DataFrame,
    mini_pool: pd.DataFrame,
    out_path: Path,
) -> None:
    lines = [
        "# Wide Mechanism Stage A",
        "",
        f"- raw mechanism-like candidates: `{len(raw_df)}`",
        f"- after cross-horizon dedupe: `{len(deduped_df)}`",
        f"- after deterministic hard-drop filter: `{len(eligible_df)}`",
        f"- field-shelf candidate rows: `{len(field_pool)}`",
        f"- use-case candidate rows: `{len(use_case_pool)}`",
        f"- unique candidates recommended for mini: `{len(mini_pool)}`",
        "",
        "## Field shelf counts",
    ]
    if not field_pool.empty:
        for key, value in field_pool["selected_shelf"].value_counts().to_dict().items():
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Use-case counts"])
    if not use_case_pool.empty:
        for key, value in use_case_pool["selected_use_case"].value_counts().to_dict().items():
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Example top candidates"])
    for row in mini_pool.head(15).itertuples(index=False):
        lines.append(
            f"- `{row.source_label} -> {row.target_label}` | score=`{row.stage_a_overall_score:.1f}` | shelves=`{', '.join(row.field_shelves)}` | use-cases=`{', '.join(row.use_case_tags)}`"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    label_map = _load_label_map(args.concepts_csv)
    frontier = pd.read_csv(args.frontier_csv, low_memory=False)
    rendered_rows: list[dict[str, Any]] = []
    for horizon in sorted(frontier["horizon"].dropna().unique()):
        sub = frontier[frontier["horizon"].astype(int) == int(horizon)].nsmallest(
            int(args.candidate_pool_per_horizon),
            "surface_rank",
        )
        for _, row in sub.iterrows():
            rendered = _render_row(row, label_map)
            rendered["cooc_count"] = int(row.get("cooc_count", 0) or 0)
            rendered_rows.append(rendered)

    raw_df = pd.DataFrame(rendered_rows)
    raw_df = raw_df[raw_df["route_family"].isin(["path_question", "mediator_question"])].copy()
    scored = raw_df.join(raw_df.apply(score_row, axis=1))
    deduped = dedupe_across_horizon(scored)
    deduped = add_duplicate_flags(deduped)
    eligible, field_pool, use_case_pool, mini_pool = build_stage_a_recommended(
        deduped,
        field_cap=int(args.field_cap),
        use_case_cap=int(args.use_case_cap),
    )

    def serialize_lists(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for key in ["primary_mediator_labels", "primary_mediator_codes", "field_shelves", "use_case_tags"]:
            if key in out.columns:
                out[key] = out[key].apply(lambda value: json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value)
        return out

    serialize_lists(raw_df).to_csv(out_dir / "wide_mechanism_raw.csv", index=False)
    serialize_lists(deduped).to_csv(out_dir / "wide_mechanism_stage_a_scored.csv", index=False)
    serialize_lists(eligible).to_csv(out_dir / "wide_mechanism_stage_a_eligible.csv", index=False)
    serialize_lists(field_pool).to_csv(out_dir / "wide_mechanism_field_pool.csv", index=False)
    serialize_lists(use_case_pool).to_csv(out_dir / "wide_mechanism_use_case_pool.csv", index=False)
    serialize_lists(mini_pool).to_csv(out_dir / "wide_mechanism_mini_pool.csv", index=False)
    write_summary(raw_df, deduped, eligible, field_pool, use_case_pool, mini_pool, out_dir / "summary.md")
    manifest = {
        "frontier_csv": str(args.frontier_csv),
        "candidate_pool_per_horizon": int(args.candidate_pool_per_horizon),
        "rows_raw": int(len(raw_df)),
        "rows_deduped": int(len(deduped)),
        "rows_eligible": int(len(eligible)),
        "rows_field_pool": int(len(field_pool)),
        "rows_use_case_pool": int(len(use_case_pool)),
        "rows_mini_pool": int(len(mini_pool)),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {out_dir / 'wide_mechanism_mini_pool.csv'}")


if __name__ == "__main__":
    main()
