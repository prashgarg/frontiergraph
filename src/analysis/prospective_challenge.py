from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.common import ensure_output_dir, first_appearance_map
from src.analysis.ranking_utils import (
    candidate_cfg_from_config,
    build_all_pairs,
    evaluate_binary_ranking,
    main_ranking_for_cutoff,
    parse_horizons,
    pref_attach_ranking,
)
from src.utils import load_config, load_corpus


def _future_set(
    first_year_map: dict[tuple[str, str], int],
    cutoff_t: int,
    horizon_h: int,
) -> set[tuple[str, str]]:
    return {edge for edge, y in first_year_map.items() if int(cutoff_t) <= int(y) <= int(cutoff_t + horizon_h)}


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def build_locked_predictions(
    corpus_df: pd.DataFrame,
    cfg: dict,
    anchor_year: int,
    horizons: list[int],
    k_values: list[int],
) -> pd.DataFrame:
    train = corpus_df[corpus_df["year"] <= int(anchor_year)].copy()
    if train.empty:
        return pd.DataFrame()
    candidate_cfg = candidate_cfg_from_config(cfg)
    ranking = main_ranking_for_cutoff(train, cutoff_t=int(anchor_year + 1), cfg=candidate_cfg)
    if ranking.empty:
        return pd.DataFrame()
    max_k = int(max(k_values))
    top = ranking.head(max_k).copy()
    for col, default in [("cooc_count", 0.0), ("path_support_norm", 0.0), ("motif_bonus_norm", 0.0)]:
        if col not in top.columns:
            top[col] = default
    rows: list[dict] = []
    for h in horizons:
        part = top.copy()
        part["challenge_anchor_year"] = int(anchor_year)
        part["horizon_h"] = int(h)
        rows.append(part)
    out = pd.concat(rows, ignore_index=True)
    out["challenge_id"] = [f"MC-{int(anchor_year)}-H{int(r.horizon_h)}-R{int(r.rank)}" for r in out.itertuples(index=False)]
    return out[
        [
            "challenge_id",
            "challenge_anchor_year",
            "horizon_h",
            "rank",
            "u",
            "v",
            "score",
            "cooc_count",
            "path_support_norm",
            "motif_bonus_norm",
        ]
    ].copy()


def build_retrospective_scoreboard(
    corpus_df: pd.DataFrame,
    cfg: dict,
    horizons: list[int],
    k_values: list[int],
) -> pd.DataFrame:
    first_year = first_appearance_map(corpus_df)
    all_nodes = sorted(set(corpus_df["src_code"].astype(str)) | set(corpus_df["dst_code"].astype(str)))
    all_pairs = build_all_pairs(all_nodes)
    candidate_cfg = candidate_cfg_from_config(cfg)
    min_y = int(corpus_df["year"].min())
    max_y = int(corpus_df["year"].max())

    rows: list[dict] = []
    for h in horizons:
        eligible = [y for y in range(min_y + 1, max_y - int(h) + 1)]
        if not eligible:
            continue
        # Use sparse anchors for a stable scoreboard.
        anchors = sorted(set([eligible[-1]] + eligible[:: max(1, len(eligible) // 8)]))
        for t in anchors:
            train = corpus_df[corpus_df["year"] <= (int(t) - 1)]
            if train.empty:
                continue
            positives = _future_set(first_year, cutoff_t=int(t), horizon_h=int(h))
            if not positives:
                continue
            main_rank = main_ranking_for_cutoff(train, cutoff_t=int(t), cfg=candidate_cfg)
            pref_rank = pref_attach_ranking(train, all_pairs_df=all_pairs)
            if main_rank.empty or pref_rank.empty:
                continue
            main_m = evaluate_binary_ranking(main_rank, positives=positives, k_values=k_values)
            pref_m = evaluate_binary_ranking(pref_rank, positives=positives, k_values=k_values)
            row = {"anchor_year": int(t), "horizon_h": int(h)}
            for k in k_values:
                row[f"main_recall_at_{k}"] = float(main_m.get(f"recall_at_{k}", 0.0))
                row[f"pref_recall_at_{k}"] = float(pref_m.get(f"recall_at_{k}", 0.0))
                row[f"delta_recall_at_{k}"] = row[f"main_recall_at_{k}"] - row[f"pref_recall_at_{k}"]
            row["main_mrr"] = float(main_m.get("mrr", 0.0))
            row["pref_mrr"] = float(pref_m.get("mrr", 0.0))
            row["delta_mrr"] = row["main_mrr"] - row["pref_mrr"]
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["horizon_h", "anchor_year"]).reset_index(drop=True)


def write_claim_governance(scoreboard_df: pd.DataFrame, out_path: Path, k_ref: int) -> None:
    lines = [
        "# Workstream 12: Prospective Challenge Governance",
        "",
        "## Pre-registered Outcome Rules",
        f"- `win`: mean(delta_recall_at_{k_ref}) >= 0 and mean(delta_mrr) >= 0 across primary horizons.",
        f"- `partial_win`: one metric positive, the other near zero (|delta| <= 0.002).",
        "- `no_win`: both metrics negative against preferential attachment.",
        "",
        "## Why this matters",
        "- Locks claims before future data arrive.",
        "- Separates model development from prospective evaluation.",
        "",
    ]
    if not scoreboard_df.empty:
        agg = (
            scoreboard_df.groupby("horizon_h", as_index=False)
            .agg(
                mean_delta_recall=(f"delta_recall_at_{k_ref}", "mean"),
                mean_delta_mrr=("delta_mrr", "mean"),
                n_anchors=("anchor_year", "nunique"),
            )
            .sort_values("horizon_h")
        )
        lines.append("## Historical Dry-Run Scoreboard")
        for r in agg.itertuples(index=False):
            lines.append(
                f"- h={int(r.horizon_h)}: delta_recall@{k_ref}={float(r.mean_delta_recall):.6f}, "
                f"delta_mrr={float(r.mean_delta_mrr):.6f}, anchors={int(r.n_anchors)}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a lockbox-style prospective challenge artifact.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument("--best_config", default="outputs/paper/03_model_search/best_config.yaml", dest="best_config_path")
    parser.add_argument("--anchor_year", type=int, default=None)
    parser.add_argument("--horizons", default="5,10")
    parser.add_argument("--k_values", type=int, nargs="+", default=[100, 500])
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus_df = load_corpus(args.corpus_path)
    cfg = load_config(args.config_path)
    best_cfg = candidate_cfg_from_config(cfg, best_config_path=args.best_config_path)
    cfg["features"] = dict(cfg.get("features", {}))
    cfg["scoring"] = dict(cfg.get("scoring", {}))
    cfg["filters"] = dict(cfg.get("filters", {}))
    cfg["features"]["tau"] = int(best_cfg.tau)
    cfg["features"]["max_path_len"] = int(best_cfg.max_path_len)
    cfg["features"]["max_neighbors_per_mediator"] = int(best_cfg.max_neighbors_per_mediator)
    cfg["scoring"]["alpha"] = float(best_cfg.alpha)
    cfg["scoring"]["beta"] = float(best_cfg.beta)
    cfg["scoring"]["gamma"] = float(best_cfg.gamma)
    cfg["scoring"]["delta"] = float(best_cfg.delta)
    cfg["filters"]["causal_only"] = bool(best_cfg.causal_only)
    cfg["filters"]["min_stability"] = best_cfg.min_stability

    max_year = int(corpus_df["year"].max())
    anchor_year = int(args.anchor_year) if args.anchor_year is not None else max_year
    horizons = parse_horizons(args.horizons, default=[5, 10])
    k_values = sorted(set(int(k) for k in args.k_values))

    locked = build_locked_predictions(
        corpus_df=corpus_df,
        cfg=cfg,
        anchor_year=anchor_year,
        horizons=horizons,
        k_values=k_values,
    )
    scoreboard = build_retrospective_scoreboard(
        corpus_df=corpus_df,
        cfg=cfg,
        horizons=horizons,
        k_values=k_values,
    )

    pred_pq = out_dir / "challenge_predictions.parquet"
    pred_csv = out_dir / "challenge_predictions.csv"
    template_csv = out_dir / "challenge_scoring_template.csv"
    score_csv = out_dir / "retrospective_scoreboard.csv"
    governance_md = out_dir / "claim_governance.md"

    locked.to_parquet(pred_pq, index=False)
    locked.to_csv(pred_csv, index=False)
    scoring_template = locked[
        ["challenge_id", "challenge_anchor_year", "horizon_h", "rank", "u", "v"]
    ].copy()
    scoring_template["first_realized_year"] = ""
    scoring_template["realized_within_h"] = ""
    scoring_template.to_csv(template_csv, index=False)
    scoreboard.to_csv(score_csv, index=False)
    write_claim_governance(scoreboard, governance_md, k_ref=int(k_values[0]))

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "anchor_year": int(anchor_year),
        "horizons": [int(h) for h in horizons],
        "k_values": [int(k) for k in k_values],
        "n_predictions": int(len(locked)),
        "prediction_sha256": _file_sha256(pred_csv),
        "config": {
            "alpha": float(best_cfg.alpha),
            "beta": float(best_cfg.beta),
            "gamma": float(best_cfg.gamma),
            "delta": float(best_cfg.delta),
            "tau": int(best_cfg.tau),
            "max_path_len": int(best_cfg.max_path_len),
        },
    }
    manifest_path = out_dir / "challenge_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"Wrote: {pred_pq}")
    print(f"Wrote: {pred_csv}")
    print(f"Wrote: {template_csv}")
    print(f"Wrote: {score_csv}")
    print(f"Wrote: {governance_md}")
    print(f"Wrote: {manifest_path}")


if __name__ == "__main__":
    main()
