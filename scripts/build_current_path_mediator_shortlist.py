from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


PATH_TITLE_TEMPLATE = "What nearby pathways could connect {source} to {target}?"
MEDIATOR_TITLE_TEMPLATE = "Which mechanisms most plausibly connect {source} to {target}?"
DIRECT_TITLE_TEMPLATE = "How might {source} change {target}?"

PROMOTE_PATH_FIRST_STEP = "Start with a short review of the nearest mediating topics, then test which pathway looks most credible."
PROMOTE_MEDIATOR_FIRST_STEP = "Start by testing which candidate mechanism carries the relation."
KEEP_DIRECT_FIRST_STEP = "A direct empirical test looks like the natural next step."

CODE_RE = re.compile(r"^FG3C\d+$")

ENV_PATTERNS = [
    r"\bcarbon\b",
    r"\bco2\b",
    r"\bemissions?\b",
    r"\bclimate\b",
    r"\benvironment",
    r"\bpollution\b",
    r"\becological\b",
    r"\bgreen\b",
    r"\brenewable\b",
    r"\benergy\b",
    r"\bsustainab",
]
INNOV_PATTERNS = [r"\binnovation\b", r"\btechnolog", r"\bdigital\b"]
MACRO_PATTERNS = [r"\bbusiness cycle\b", r"\bgrowth\b", r"\binflation\b", r"\bhouse prices?\b", r"\bprice changes?\b", r"\bproductivity\b", r"\boutput\b"]
FIN_PATTERNS = [r"\bfinancial\b", r"\bfinance\b", r"\btax\b", r"\bbonds?\b", r"\binvestment\b", r"\bdebt\b"]
DEMAND_PATTERNS = [r"\bwages?\b", r"\bincome\b", r"\bemployment\b", r"\bwillingness to pay\b", r"\bconsumption\b"]
TRADE_PATTERNS = [r"\btrade\b", r"\bimports?\b", r"\bexports?\b", r"\bglobal", r"\burban", r"\bcity\b", r"\btourism\b", r"\bindustrial structure\b"]
UNCERTAINTY_PATTERNS = [r"\buncertainty\b", r"\brisk\b"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the filtered current frontier as path/mechanism questions.")
    parser.add_argument(
        "--frontier-csv",
        default="outputs/paper/15_current_reranked_frontier/current_reranked_frontier.csv",
        dest="frontier_csv",
    )
    parser.add_argument(
        "--concepts-csv",
        default="site/public/data/v2/central_concepts.csv",
        dest="concepts_csv",
    )
    parser.add_argument("--top-k", type=int, default=100, dest="top_k")
    parser.add_argument("--candidate-pool", type=int, default=250, dest="candidate_pool")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def _load_label_map(concepts_csv: str | Path) -> dict[str, str]:
    path = Path(concepts_csv)
    if not path.exists():
        return {}
    df = pd.read_csv(path, usecols=["concept_id", "plain_label"])
    return {str(r.concept_id): str(r.plain_label) for r in df.drop_duplicates("concept_id").itertuples(index=False)}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _is_unresolved_code(value: str) -> bool:
    return bool(CODE_RE.match(str(value or "").strip()))


def _pretty_label(value: str, label_map: dict[str, str]) -> str:
    text = _clean_text(value)
    if text in label_map:
        return label_map[text]
    return text


def _parse_mediators(raw: Any, label_map: dict[str, str]) -> list[dict[str, Any]]:
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = []
    elif isinstance(raw, list):
        payload = raw
    else:
        payload = []
    out: list[dict[str, Any]] = []
    for item in payload:
        mediator = _clean_text(item.get("mediator"))
        provided_label = _clean_text(item.get("label"))
        label = provided_label if provided_label else _pretty_label(mediator, label_map)
        out.append(
            {
                "mediator": mediator,
                "label": label,
                "score": float(item.get("score", 0.0) or 0.0),
                "resolved": not _is_unresolved_code(label),
            }
        )
    return out


def _choose_primary_mediators(mediators: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    resolved = [m for m in mediators if m["resolved"]]
    if resolved:
        return resolved[:k]
    return []


def _quote_list(items: list[str]) -> str:
    vals = [_clean_text(x) for x in items if _clean_text(x)]
    deduped: list[str] = []
    seen: set[str] = set()
    alias_map = {
        "gdp": "GDP",
        "gross domestic product (gdp)": "GDP",
        "gross domestic product gdp": "GDP",
        "economic growth (gdp)": "GDP",
        "economic growth gdp": "GDP",
        "gross domestic product": "GDP",
        "economic growth": "economic growth",
        "investments": "investment",
        "carbon dioxide (co2) emission": "CO2 emissions",
        "carbon emission intensity": "carbon emission intensity",
    }
    for value in vals:
        key = _normalize_family_label(value)
        canonical = alias_map.get(value.strip().lower(), value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(canonical)
    vals = deduped
    if not vals:
        return "the nearest available mediators"
    if len(vals) == 1:
        return vals[0]
    if len(vals) == 2:
        return f"{vals[0]} and {vals[1]}"
    return f"{vals[0]}, {vals[1]}, and {vals[2]}"


def _normalize_family_label(value: str) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    alias_map = {
        "gdp": "gdp",
        "gross domestic product gdp": "gdp",
        "gross domestic product": "gdp",
        "economic growth gdp": "gdp",
        "co2 emissions": "carbon emissions",
        "carbon emissions co2 emissions": "carbon emissions",
        "willingness to pay wtp": "willingness to pay",
        "environmental quality co2 emissions": "environmental quality",
    }
    return alias_map.get(text, text)


def _match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _theme_for_label(label: str) -> str:
    text = _normalize_family_label(label)
    if _match_any(text, ENV_PATTERNS):
        return "environment_climate"
    if _match_any(text, INNOV_PATTERNS):
        return "innovation_technology"
    if _match_any(text, MACRO_PATTERNS):
        return "macro_cycle_prices"
    if _match_any(text, FIN_PATTERNS):
        return "finance_tax"
    if _match_any(text, DEMAND_PATTERNS):
        return "labor_income_demand"
    if _match_any(text, TRADE_PATTERNS):
        return "trade_urban_structure"
    if _match_any(text, UNCERTAINTY_PATTERNS):
        return "uncertainty_risk"
    return "other"


def _route_family(row: pd.Series, mediators: list[dict[str, Any]]) -> str:
    supporting_path_count = int(row.get("supporting_path_count", 0) or 0)
    mediator_count = int(row.get("mediator_count", 0) or 0)
    if not mediators and mediator_count <= 0 and supporting_path_count <= 0:
        return "direct_edge_question"
    scores = [float(m["score"]) for m in mediators if float(m["score"]) > 0]
    if not scores:
        return "path_question" if supporting_path_count > 0 or mediator_count > 0 else "direct_edge_question"
    top_share = scores[0] / max(sum(scores), 1e-9)
    if mediator_count <= 3 or top_share >= 0.62:
        return "mediator_question"
    return "path_question"


def _baseline_direct_title(source: str, target: str) -> str:
    return DIRECT_TITLE_TEMPLATE.format(source=source, target=target)


def _render_row(row: pd.Series, label_map: dict[str, str]) -> dict[str, Any]:
    source = _pretty_label(_clean_text(row.get("u_label") or row.get("u")), label_map)
    target = _pretty_label(_clean_text(row.get("v_label") or row.get("v")), label_map)
    mediators = _parse_mediators(row.get("top_mediators_json"), label_map)
    primary = _choose_primary_mediators(mediators, k=3)
    primary_labels = [m["label"] for m in primary]
    route_family = _route_family(row, mediators)
    source_family = _normalize_family_label(source)
    target_family = _normalize_family_label(target)
    family_key = f"{source_family}__{target_family}"
    source_theme = _theme_for_label(source)
    target_theme = _theme_for_label(target)
    theme_pair_key = f"{source_theme}__{target_theme}"

    if route_family == "path_question":
        title = PATH_TITLE_TEMPLATE.format(source=source, target=target)
        if primary_labels:
            why = f"Nearby work points to {_quote_list(primary_labels)} as plausible connecting pathways."
        else:
            why = "Nearby work points to several plausible connecting pathways, but the nearest mediators are still poorly labeled."
        first_step = PROMOTE_PATH_FIRST_STEP
    elif route_family == "mediator_question":
        title = MEDIATOR_TITLE_TEMPLATE.format(source=source, target=target)
        if primary_labels:
            why = f"The leading candidate mechanisms are {_quote_list(primary_labels)}."
        else:
            why = "The leading candidate mechanisms are still poorly labeled."
        first_step = PROMOTE_MEDIATOR_FIRST_STEP
    else:
        title = _baseline_direct_title(source, target)
        why = f"The endpoint pair already has enough local structure to justify a direct test."
        first_step = KEEP_DIRECT_FIRST_STEP

    return {
        "pair_key": f"{row['u']}__{row['v']}",
        "horizon": int(row["horizon"]),
        "surface_rank": int(row["surface_rank"]),
        "reranker_rank": int(row["reranker_rank"]),
        "transparent_rank": int(row["transparent_rank"]),
        "source_label": source,
        "target_label": target,
        "source_family": source_family,
        "target_family": target_family,
        "semantic_family_key": family_key,
        "source_theme": source_theme,
        "target_theme": target_theme,
        "theme_pair_key": theme_pair_key,
        "route_family": route_family,
        "display_title": title,
        "display_why": why,
        "display_first_step": first_step,
        "primary_mediator_labels": primary_labels,
        "primary_mediator_codes": [m["mediator"] for m in primary],
        "baseline_direct_title": _baseline_direct_title(source, target),
        "surface_penalty": int(row.get("surface_penalty", 0) or 0),
        "surface_flagged": int(row.get("surface_flagged", 0) or 0),
        "rank_delta": int(row.get("rank_delta", 0) or 0),
        "reranker_score": float(row.get("reranker_score", 0.0) or 0.0),
        "transparent_score": float(row.get("transparent_score", 0.0) or 0.0),
        "mediator_count": int(row.get("mediator_count", 0) or 0),
        "supporting_path_count": int(row.get("supporting_path_count", 0) or 0),
        "top_mediators_json": row.get("top_mediators_json", "[]"),
        "top_paths_json": row.get("top_paths_json", "[]"),
    }


def _diversify_rows(rows: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    remaining = sorted(rows, key=lambda row: (int(row["surface_rank"]), int(row["reranker_rank"])))
    chosen: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    target_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    source_theme_counts: Counter[str] = Counter()
    target_theme_counts: Counter[str] = Counter()
    theme_pair_counts: Counter[str] = Counter()

    while remaining and len(chosen) < top_k:
        best_idx = 0
        best_score: tuple[float, int, int] | None = None
        for idx, row in enumerate(remaining):
            source_family = str(row.get("source_family", ""))
            target_family = str(row.get("target_family", ""))
            family_key = str(row.get("semantic_family_key", ""))
            source_theme = str(row.get("source_theme", ""))
            target_theme = str(row.get("target_theme", ""))
            theme_pair_key = str(row.get("theme_pair_key", ""))
            theme_penalty = (
                2 * max(source_theme_counts[source_theme] - 2, 0)
                + 2 * max(target_theme_counts[target_theme] - 2, 0)
                + 3 * theme_pair_counts[theme_pair_key]
            )
            redundancy_penalty = (
                12 * family_counts[family_key]
                + 4 * source_counts[source_family]
                + 4 * target_counts[target_family]
            )
            score = (
                float(row["surface_rank"]) + float(redundancy_penalty + theme_penalty),
                int(row["surface_rank"]),
                int(row["reranker_rank"]),
            )
            if best_score is None or score < best_score:
                best_score = score
                best_idx = idx

        row = remaining.pop(best_idx)
        source_family = str(row.get("source_family", ""))
        target_family = str(row.get("target_family", ""))
        family_key = str(row.get("semantic_family_key", ""))
        source_theme = str(row.get("source_theme", ""))
        target_theme = str(row.get("target_theme", ""))
        theme_pair_key = str(row.get("theme_pair_key", ""))
        theme_penalty = (
            2 * max(source_theme_counts[source_theme] - 2, 0)
            + 2 * max(target_theme_counts[target_theme] - 2, 0)
            + 3 * theme_pair_counts[theme_pair_key]
        )
        redundancy_penalty = (
            12 * family_counts[family_key]
            + 4 * source_counts[source_family]
            + 4 * target_counts[target_family]
        )
        row["shortlist_rank"] = len(chosen) + 1
        row["shortlist_penalty"] = int(redundancy_penalty + theme_penalty)
        row["theme_penalty"] = int(theme_penalty)
        row["source_family_seen_before"] = int(source_counts[source_family])
        row["target_family_seen_before"] = int(target_counts[target_family])
        row["family_seen_before"] = int(family_counts[family_key])
        row["source_theme_seen_before"] = int(source_theme_counts[source_theme])
        row["target_theme_seen_before"] = int(target_theme_counts[target_theme])
        row["theme_pair_seen_before"] = int(theme_pair_counts[theme_pair_key])
        chosen.append(row)
        source_counts[source_family] += 1
        target_counts[target_family] += 1
        family_counts[family_key] += 1
        source_theme_counts[source_theme] += 1
        target_theme_counts[target_theme] += 1
        theme_pair_counts[theme_pair_key] += 1

    return chosen


def _write_review_note(rows: list[dict[str, Any]], out_path: Path) -> None:
    route_counts = pd.Series([row["route_family"] for row in rows]).value_counts().to_dict()
    total = max(len(rows), 1)
    lines = [
        "# Current Path/Mediator Shortlist",
        "",
        "This note renders the filtered current frontier into path/mechanism questions.",
        "",
        "## Route counts",
        "",
    ]
    for route in ["path_question", "mediator_question", "direct_edge_question"]:
        count = int(route_counts.get(route, 0))
        share = count / total
        lines.append(f"- `{route}`: {count} ({share:.1%})")

    for horizon in sorted(set(int(row["horizon"]) for row in rows)):
        sub = [row for row in rows if int(row["horizon"]) == horizon]
        lines.extend(["", f"## Horizon {horizon}", ""])
        for row in sub[:15]:
            lines.append(
                f"- `#{int(row['shortlist_rank'])}` `{row['route_family']}` | {row['display_title']}  \n"
                f"  Before: {row['baseline_direct_title']}  \n"
                f"  Original surface rank: {int(row['surface_rank'])}; shortlist penalty: {int(row['shortlist_penalty'])}  \n"
                f"  Why: {row['display_why']}  \n"
                f"  First step: {row['display_first_step']}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    label_map = _load_label_map(args.concepts_csv)
    frontier_df = pd.read_csv(args.frontier_csv)
    rendered_rows: list[dict[str, Any]] = []
    for horizon in sorted(frontier_df["horizon"].dropna().unique()):
        sub = frontier_df[frontier_df["horizon"] == int(horizon)].nsmallest(int(args.candidate_pool), "surface_rank").copy()
        for _, row in sub.iterrows():
            rendered_rows.append(_render_row(row, label_map))

    diversified_rows: list[dict[str, Any]] = []
    for horizon in sorted(set(int(row["horizon"]) for row in rendered_rows)):
        sub = [row for row in rendered_rows if int(row["horizon"]) == horizon]
        diversified_rows.extend(_diversify_rows(sub, top_k=int(args.top_k)))

    out_df = pd.DataFrame(diversified_rows).sort_values(["horizon", "shortlist_rank"], ascending=[True, True]).reset_index(drop=True)
    out_df.to_csv(out_dir / "current_path_mediator_shortlist.csv", index=False)
    with (out_dir / "current_path_mediator_shortlist.jsonl").open("w", encoding="utf-8") as handle:
        for row in out_df.to_dict(orient="records"):
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    route_summary = (
        out_df.groupby(["horizon", "route_family"], as_index=False)
        .agg(count=("pair_key", "size"))
        .sort_values(["horizon", "count"], ascending=[True, False])
        .reset_index(drop=True)
    )
    route_summary.to_csv(out_dir / "route_summary.csv", index=False)
    _write_review_note(out_df.to_dict(orient="records"), out_dir / "current_path_mediator_shortlist.md")
    manifest = {
        "source_frontier_csv": args.frontier_csv,
        "top_k_per_horizon": int(args.top_k),
        "candidate_pool_per_horizon": int(args.candidate_pool),
        "n_rows": int(len(out_df)),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote: {out_dir / 'current_path_mediator_shortlist.csv'}")


if __name__ == "__main__":
    main()
