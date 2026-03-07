from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.utils import ensure_parent_dir, load_config, min_max_normalize, pair_key


def _to_map(df: pd.DataFrame, key_cols: tuple[str, str], value_col: str) -> dict[tuple[str, str], float]:
    if df.empty:
        return {}
    return {(str(r[0]), str(r[1])): float(r[2]) for r in df[[key_cols[0], key_cols[1], value_col]].itertuples(index=False)}


def compute_candidate_scores(
    pairs_df: pd.DataFrame,
    paths_df: pd.DataFrame,
    motifs_df: pd.DataFrame,
    alpha: float = 0.5,
    beta: float = 0.2,
    gamma: float = 0.3,
    delta: float = 0.2,
) -> pd.DataFrame:
    pairs_df = pairs_df.copy()
    paths_df = paths_df.copy()
    motifs_df = motifs_df.copy()

    pair_gap = {
        pair_key(str(row.u), str(row.v)): float(row.gap_bonus)
        for row in pairs_df[["u", "v", "gap_bonus"]].itertuples(index=False)
    } if not pairs_df.empty else {}
    pair_cooc = {
        pair_key(str(row.u), str(row.v)): int(row.cooc_count)
        for row in pairs_df[["u", "v", "cooc_count"]].itertuples(index=False)
    } if not pairs_df.empty else {}
    pair_first = {
        pair_key(str(row.u), str(row.v)): int(row.first_year_seen)
        for row in pairs_df[["u", "v", "first_year_seen"]].itertuples(index=False)
    } if not pairs_df.empty else {}
    pair_last = {
        pair_key(str(row.u), str(row.v)): int(row.last_year_seen)
        for row in pairs_df[["u", "v", "last_year_seen"]].itertuples(index=False)
    } if not pairs_df.empty else {}

    candidate_keys: set[tuple[str, str]] = set()
    if not paths_df.empty:
        candidate_keys.update((str(u), str(v)) for u, v in paths_df[["u", "v"]].itertuples(index=False))
    if not motifs_df.empty:
        candidate_keys.update((str(u), str(v)) for u, v in motifs_df[["u", "v"]].itertuples(index=False))
    if not pairs_df.empty:
        for row in pairs_df[["u", "v", "gap_bonus"]].itertuples(index=False):
            if float(row.gap_bonus) > 0:
                u, v = str(row.u), str(row.v)
                candidate_keys.add((u, v))
                candidate_keys.add((v, u))

    path_map = paths_df.set_index(["u", "v"]).to_dict(orient="index") if not paths_df.empty else {}
    motif_map = motifs_df.set_index(["u", "v"]).to_dict(orient="index") if not motifs_df.empty else {}

    rows = []
    for u, v in sorted(candidate_keys):
        undirected = pair_key(u, v)
        path_payload = path_map.get((u, v), {})
        motif_payload = motif_map.get((u, v), {})
        path_support_raw = float(path_payload.get("path_support_raw", 0.0))
        motif_bonus_raw = float(motif_payload.get("motif_bonus_raw", 0.0))
        hub_penalty = float(path_payload.get("hub_penalty", 0.0))
        gap_bonus = float(pair_gap.get(undirected, 1.0))
        rows.append(
            {
                "u": u,
                "v": v,
                "path_support_raw": path_support_raw,
                "gap_bonus": gap_bonus,
                "motif_bonus_raw": motif_bonus_raw,
                "hub_penalty": hub_penalty,
                "mediator_count": int(path_payload.get("mediator_count", 0)),
                "motif_count": int(motif_payload.get("motif_count", 0)),
                "cooc_count": int(pair_cooc.get(undirected, 0)),
                "first_year_seen": int(pair_first.get(undirected, 0)) if undirected in pair_first else None,
                "last_year_seen": int(pair_last.get(undirected, 0)) if undirected in pair_last else None,
                "top_mediators_json": path_payload.get("top_mediators_json", "[]"),
                "top_paths_json": path_payload.get("top_paths_json", "[]"),
                "top_motif_mediators_json": motif_payload.get("top_motif_mediators_json", "[]"),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "u",
                "v",
                "path_support_raw",
                "path_support_norm",
                "gap_bonus",
                "motif_bonus_raw",
                "motif_bonus_norm",
                "hub_penalty",
                "score",
            ]
        )
    out = pd.DataFrame(rows)
    out = out[(out["u"] != out["v"]) & ((out["path_support_raw"] > 0) | (out["motif_bonus_raw"] > 0) | (out["gap_bonus"] > 0))]
    if out.empty:
        return out
    out["hub_penalty_raw"] = out["hub_penalty"]
    out["path_support_norm"] = min_max_normalize(out["path_support_raw"])
    out["motif_bonus_norm"] = min_max_normalize(out["motif_bonus_raw"])
    out["hub_penalty"] = min_max_normalize(out["hub_penalty_raw"])
    out["score"] = (
        alpha * out["path_support_norm"]
        + beta * out["gap_bonus"]
        + gamma * out["motif_bonus_norm"]
        - delta * out["hub_penalty"]
    )
    out = out.sort_values("score", ascending=False).reset_index(drop=True)
    out["rank"] = out.index + 1
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score missing-claim candidates from feature tables.")
    parser.add_argument("--pairs", required=True, dest="pairs_path")
    parser.add_argument("--paths", required=True, dest="paths_path")
    parser.add_argument("--motifs", required=True, dest="motifs_path")
    parser.add_argument("--out", required=True, dest="out_path")
    parser.add_argument("--config", default="config/config.yaml", dest="config_path")
    parser.add_argument("--alpha", type=float, default=None)
    parser.add_argument("--beta", type=float, default=None)
    parser.add_argument("--gamma", type=float, default=None)
    parser.add_argument("--delta", type=float, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config_path)
    scoring_cfg = config.get("scoring", {})
    alpha = args.alpha if args.alpha is not None else float(scoring_cfg.get("alpha", 0.5))
    beta = args.beta if args.beta is not None else float(scoring_cfg.get("beta", 0.2))
    gamma = args.gamma if args.gamma is not None else float(scoring_cfg.get("gamma", 0.3))
    delta = args.delta if args.delta is not None else float(scoring_cfg.get("delta", 0.2))

    pairs_df = pd.read_parquet(args.pairs_path) if Path(args.pairs_path).exists() else pd.DataFrame()
    paths_df = pd.read_parquet(args.paths_path) if Path(args.paths_path).exists() else pd.DataFrame()
    motifs_df = pd.read_parquet(args.motifs_path) if Path(args.motifs_path).exists() else pd.DataFrame()

    out_df = compute_candidate_scores(pairs_df, paths_df, motifs_df, alpha=alpha, beta=beta, gamma=gamma, delta=delta)
    out_path = Path(args.out_path)
    ensure_parent_dir(out_path)
    out_df.to_parquet(out_path, index=False)
    print(f"Wrote candidates: {out_path} ({len(out_df)} rows)")


if __name__ == "__main__":
    main()
