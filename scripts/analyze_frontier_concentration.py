from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose thematic and family concentration across frontier pipeline stages.")
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument(
        "--frontier",
        default="outputs/paper/15_current_reranked_frontier/current_reranked_frontier.csv",
        dest="frontier_path",
    )
    parser.add_argument(
        "--shortlist",
        default="outputs/paper/16_current_path_mediator_shortlist/current_path_mediator_shortlist.csv",
        dest="shortlist_path",
    )
    parser.add_argument("--recent-start-year", type=int, default=2016, dest="recent_start_year")
    parser.add_argument("--top-k", type=int, default=100, dest="top_k")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


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
INNOV_PATTERNS = [
    r"\binnovation\b",
    r"\btechnolog",
    r"\bdigital\b",
]
MACRO_PATTERNS = [
    r"\bbusiness cycle\b",
    r"\bgrowth\b",
    r"\binflation\b",
    r"\bhouse prices?\b",
    r"\bprice changes?\b",
    r"\bproductivity\b",
    r"\boutput\b",
]
FIN_PATTERNS = [
    r"\bfinancial\b",
    r"\bfinance\b",
    r"\btax\b",
    r"\bbonds?\b",
    r"\binvestment\b",
    r"\bdebt\b",
]
DEMAND_PATTERNS = [
    r"\bwages?\b",
    r"\bincome\b",
    r"\bemployment\b",
    r"\bwillingness to pay\b",
    r"\bconsumption\b",
]
TRADE_PATTERNS = [
    r"\btrade\b",
    r"\bimports?\b",
    r"\bexports?\b",
    r"\bglobal",
    r"\burban",
    r"\bcity\b",
    r"\btourism\b",
    r"\bindustrial structure\b",
]
UNCERTAINTY_PATTERNS = [
    r"\buncertainty\b",
    r"\brisk\b",
]


def _normalize_label(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    alias_map = {
        "co2 emissions": "carbon emissions",
        "carbon emissions co2 emissions": "carbon emissions",
        "willingness to pay wtp": "willingness to pay",
        "environmental quality co2 emissions": "environmental quality",
    }
    return alias_map.get(text, text)


def _match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _theme_for_label(label: str) -> str:
    text = _normalize_label(label)
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


def _build_endpoint_frame(df: pd.DataFrame, left_label: str, right_label: str, stage: str, extra_cols: list[str] | None = None) -> pd.DataFrame:
    extra_cols = extra_cols or []
    left = df[[left_label] + extra_cols].copy()
    left = left.rename(columns={left_label: "label"})
    left["side"] = "source"
    right = df[[right_label] + extra_cols].copy()
    right = right.rename(columns={right_label: "label"})
    right["side"] = "target"
    out = pd.concat([left, right], ignore_index=True)
    out["family"] = out["label"].map(_normalize_label)
    out["theme"] = out["label"].map(_theme_for_label)
    out["stage"] = stage
    return out


def _share_table(endpoints: pd.DataFrame, group_col: str) -> pd.DataFrame:
    summary = (
        endpoints.groupby(["stage", group_col], as_index=False)
        .size()
        .rename(columns={"size": "count", group_col: "group"})
    )
    totals = endpoints.groupby("stage", as_index=False).size().rename(columns={"size": "total"})
    summary = summary.merge(totals, on="stage", how="left")
    summary["share"] = summary["count"] / summary["total"]
    return summary.sort_values(["stage", "share"], ascending=[True, False]).reset_index(drop=True)


def _family_top_table(endpoints: pd.DataFrame, stages: list[str], top_n: int = 20) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for stage in stages:
        sub = endpoints[endpoints["stage"] == stage]
        if sub.empty:
            continue
        top = sub.groupby("family", as_index=False).size().rename(columns={"size": "count"})
        top["share"] = top["count"] / max(len(sub), 1)
        top = top.sort_values(["count", "family"], ascending=[False, True]).head(top_n).copy()
        top["stage"] = stage
        frames.append(top)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["stage", "family", "count", "share"])


def _top_stage_families(endpoints: pd.DataFrame, stage: str, top_n: int = 15) -> list[str]:
    sub = endpoints[endpoints["stage"] == stage]
    return (
        sub.groupby("family", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["count", "family"], ascending=[False, True])
        .head(top_n)["family"]
        .tolist()
    )


def _family_stage_shares(endpoints: pd.DataFrame, families: list[str], stages: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    totals = endpoints.groupby("stage").size().to_dict()
    for family in families:
        family_rows = {"family": family}
        for stage in stages:
            sub = endpoints[(endpoints["stage"] == stage) & (endpoints["family"] == family)]
            count = int(len(sub))
            total = int(totals.get(stage, 0))
            family_rows[f"{stage}_count"] = count
            family_rows[f"{stage}_share"] = (count / total) if total else 0.0
        rows.append(family_rows)
    return pd.DataFrame(rows)


def _pair_family_metrics(frontier: pd.DataFrame, shortlist: pd.DataFrame) -> pd.DataFrame:
    top_short = shortlist[shortlist["shortlist_rank"] <= 100].copy()
    family_rows: list[dict] = []
    for horizon in sorted(top_short["horizon"].unique()):
        sub = top_short[top_short["horizon"] == horizon]
        for family, fam_sub in sub.groupby("source_family"):
            family_rows.append(
                {
                    "horizon": int(horizon),
                    "family": family,
                    "role": "source_family",
                    "shortlist_count": int(len(fam_sub)),
                    "mean_shortlist_penalty": float(fam_sub["shortlist_penalty"].mean()),
                    "route_path_share": float((fam_sub["route_family"] == "path_question").mean()),
                    "route_mediator_share": float((fam_sub["route_family"] == "mediator_question").mean()),
                }
            )
        for family, fam_sub in sub.groupby("target_family"):
            family_rows.append(
                {
                    "horizon": int(horizon),
                    "family": family,
                    "role": "target_family",
                    "shortlist_count": int(len(fam_sub)),
                    "mean_shortlist_penalty": float(fam_sub["shortlist_penalty"].mean()),
                    "route_path_share": float((fam_sub["route_family"] == "path_question").mean()),
                    "route_mediator_share": float((fam_sub["route_family"] == "mediator_question").mean()),
                }
            )
    metrics = pd.DataFrame(family_rows)
    if metrics.empty:
        return metrics

    frontier_metrics = frontier.copy()
    frontier_metrics["source_family"] = frontier_metrics["u_label"].map(_normalize_label)
    frontier_metrics["target_family"] = frontier_metrics["v_label"].map(_normalize_label)

    agg_rows: list[dict] = []
    for horizon in sorted(frontier_metrics["horizon"].unique()):
        fsub = frontier_metrics[frontier_metrics["horizon"] == horizon]
        for role, col in [("source_family", "source_family"), ("target_family", "target_family")]:
            top = (
                fsub.groupby(col, as_index=False)
                .agg(
                    pair_count=("u", "size"),
                    mean_supporting_path_count=("path_support_raw", "mean"),
                    mean_mediator_count=("mediator_count", "mean"),
                    mean_recent_share=(f"{'source' if role == 'source_family' else 'target'}_recent_share", "mean"),
                    mean_fwci=(f"{'source' if role == 'source_family' else 'target'}_mean_fwci", "mean"),
                )
                .rename(columns={col: "family"})
            )
            top["horizon"] = int(horizon)
            top["role"] = role
            agg_rows.append(top)
    agg_df = pd.concat(agg_rows, ignore_index=True) if agg_rows else pd.DataFrame()
    return metrics.merge(agg_df, on=["horizon", "family", "role"], how="left")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = pd.read_parquet(args.corpus_path, columns=["src_label", "dst_label", "year"])
    frontier = pd.read_csv(args.frontier_path)
    shortlist = pd.read_csv(args.shortlist_path)

    corpus_endpoints = _build_endpoint_frame(corpus, "src_label", "dst_label", stage="corpus_all")
    recent_corpus = corpus[corpus["year"] >= int(args.recent_start_year)].copy()
    recent_endpoints = _build_endpoint_frame(recent_corpus, "src_label", "dst_label", stage=f"corpus_recent_{args.recent_start_year}")

    frontier_top_transparent = []
    frontier_top_reranker = []
    frontier_top_surface = []
    for horizon in sorted(frontier["horizon"].unique()):
        sub = frontier[frontier["horizon"] == horizon].copy()
        frontier_top_transparent.append(
            _build_endpoint_frame(
                sub.nsmallest(int(args.top_k), "transparent_rank"),
                "u_label",
                "v_label",
                stage=f"h{int(horizon)}_transparent_top{int(args.top_k)}",
            )
        )
        frontier_top_reranker.append(
            _build_endpoint_frame(
                sub.nsmallest(int(args.top_k), "reranker_rank"),
                "u_label",
                "v_label",
                stage=f"h{int(horizon)}_reranker_top{int(args.top_k)}",
            )
        )
        frontier_top_surface.append(
            _build_endpoint_frame(
                sub.nsmallest(int(args.top_k), "surface_rank"),
                "u_label",
                "v_label",
                stage=f"h{int(horizon)}_surface_top{int(args.top_k)}",
            )
        )

    shortlist_frames = []
    for horizon in sorted(shortlist["horizon"].unique()):
        sub = shortlist[shortlist["horizon"] == horizon].nsmallest(int(args.top_k), "shortlist_rank")
        shortlist_frames.append(
            _build_endpoint_frame(
                sub.rename(columns={"source_label": "u_label", "target_label": "v_label"}),
                "u_label",
                "v_label",
                stage=f"h{int(horizon)}_shortlist_top{int(args.top_k)}",
            )
        )

    endpoints = pd.concat(
        [
            corpus_endpoints,
            recent_endpoints,
            *frontier_top_transparent,
            *frontier_top_reranker,
            *frontier_top_surface,
            *shortlist_frames,
        ],
        ignore_index=True,
    )

    theme_shares = _share_table(endpoints, "theme")
    family_top = _family_top_table(
        endpoints,
        stages=[
            "corpus_all",
            f"corpus_recent_{args.recent_start_year}",
            f"h5_transparent_top{int(args.top_k)}",
            f"h5_reranker_top{int(args.top_k)}",
            f"h5_surface_top{int(args.top_k)}",
            f"h5_shortlist_top{int(args.top_k)}",
            f"h10_transparent_top{int(args.top_k)}",
            f"h10_reranker_top{int(args.top_k)}",
            f"h10_surface_top{int(args.top_k)}",
            f"h10_shortlist_top{int(args.top_k)}",
        ],
        top_n=15,
    )

    tracked_families = sorted(
        set(_top_stage_families(endpoints, f"h5_shortlist_top{int(args.top_k)}", 12))
        | set(_top_stage_families(endpoints, f"h10_shortlist_top{int(args.top_k)}", 12))
    )
    family_stage_shares = _family_stage_shares(
        endpoints,
        tracked_families,
        stages=[
            "corpus_all",
            f"corpus_recent_{args.recent_start_year}",
            f"h5_transparent_top{int(args.top_k)}",
            f"h5_reranker_top{int(args.top_k)}",
            f"h5_surface_top{int(args.top_k)}",
            f"h5_shortlist_top{int(args.top_k)}",
            f"h10_transparent_top{int(args.top_k)}",
            f"h10_reranker_top{int(args.top_k)}",
            f"h10_surface_top{int(args.top_k)}",
            f"h10_shortlist_top{int(args.top_k)}",
        ],
    )

    family_metrics = _pair_family_metrics(frontier, shortlist)

    theme_shares.to_csv(out_dir / "theme_shares.csv", index=False)
    family_top.to_csv(out_dir / "top_families_by_stage.csv", index=False)
    family_stage_shares.to_csv(out_dir / "tracked_family_stage_shares.csv", index=False)
    family_metrics.to_csv(out_dir / "shortlist_family_metrics.csv", index=False)

    stages_of_interest = [
        "corpus_all",
        f"corpus_recent_{args.recent_start_year}",
        f"h5_transparent_top{int(args.top_k)}",
        f"h5_reranker_top{int(args.top_k)}",
        f"h5_surface_top{int(args.top_k)}",
        f"h5_shortlist_top{int(args.top_k)}",
        f"h10_transparent_top{int(args.top_k)}",
        f"h10_reranker_top{int(args.top_k)}",
        f"h10_surface_top{int(args.top_k)}",
        f"h10_shortlist_top{int(args.top_k)}",
    ]
    theme_pivot = theme_shares.pivot(index="group", columns="stage", values="share").fillna(0.0)
    env_row = theme_pivot.loc["environment_climate"] if "environment_climate" in theme_pivot.index else pd.Series(dtype=float)

    summary = {
        "recent_start_year": int(args.recent_start_year),
        "top_k": int(args.top_k),
        "environment_climate_shares": {stage: float(env_row.get(stage, 0.0)) for stage in stages_of_interest},
        "tracked_families": tracked_families,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Frontier Concentration Diagnosis",
        "",
        "This note compares family and theme concentration across pipeline stages:",
        "- underlying corpus",
        f"- recent corpus (`year >= {int(args.recent_start_year)}`)",
        f"- current transparent top {int(args.top_k)}",
        f"- current reranked top {int(args.top_k)}",
        f"- current surfaced top {int(args.top_k)}",
        f"- current cleaned shortlist top {int(args.top_k)}",
        "",
        "## Environment/climate share across stages",
        "",
    ]
    for stage in stages_of_interest:
        share = float(env_row.get(stage, 0.0))
        lines.append(f"- `{stage}`: {share:.1%}")

    lines.extend(["", "## Top tracked families from the cleaned shortlist", ""])
    for family in tracked_families:
        row = family_stage_shares[family_stage_shares["family"] == family]
        if row.empty:
            continue
        rec = row.iloc[0].to_dict()
        lines.append(
            f"- `{family}` | corpus={rec.get('corpus_all_share', 0.0):.2%}, "
            f"recent={rec.get(f'corpus_recent_{int(args.recent_start_year)}_share', 0.0):.2%}, "
            f"h5_short={rec.get(f'h5_shortlist_top{int(args.top_k)}_share', 0.0):.2%}, "
            f"h10_short={rec.get(f'h10_shortlist_top{int(args.top_k)}_share', 0.0):.2%}"
        )

    lines.extend(["", "## Initial read", ""])
    lines.append(
        "The key question is whether environment/climate families are already large in the corpus, become larger in the recent corpus, and then receive further amplification from reranking and shortlist cleanup."
    )
    lines.append(
        "The same decomposition can be used for other repeated families such as business-cycle, willingness-to-pay, green-innovation, and emissions-related objects."
    )
    (out_dir / "frontier_concentration_diagnosis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {out_dir / 'frontier_concentration_diagnosis.md'}")


if __name__ == "__main__":
    main()
