from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.analysis.common import ensure_output_dir, first_appearance_map
from src.utils import load_corpus


def _load_vintage_panel(
    out_dir: Path,
    candidates_df: pd.DataFrame,
    first_year: dict[tuple[str, str], int],
) -> pd.DataFrame:
    pred_path = out_dir.parent / "04_vintage_exercise" / "vintage_predictions.parquet"
    real_path = out_dir.parent / "04_vintage_exercise" / "vintage_realization.parquet"
    if pred_path.exists() and real_path.exists():
        pred = pd.read_parquet(pred_path)
        real = pd.read_parquet(real_path)
        key_cols = [c for c in ["anchor_year", "u", "v", "rank"] if c in pred.columns and c in real.columns]
        if key_cols:
            return pred.merge(real, on=key_cols, how="inner", suffixes=("", "_real"))

    # Fallback pseudo-panel: evaluate top candidates at last supported anchor.
    if candidates_df.empty:
        return pd.DataFrame(columns=["anchor_year", "u", "v", "rank", "score", "realized_within_h", "time_to_fill"])
    max_year = max(first_year.values()) if first_year else 0
    anchor = int(max_year - 5)
    top = candidates_df.sort_values("score", ascending=False).head(2000).copy()
    if "rank" not in top.columns:
        top = top.reset_index(drop=True)
        top["rank"] = top.index + 1
    rows: list[dict] = []
    for row in top.itertuples(index=False):
        y = first_year.get((str(row.u), str(row.v)))
        realized = y is not None and (anchor + 1) <= int(y) <= (anchor + 5)
        rows.append(
            {
                "anchor_year": anchor,
                "u": str(row.u),
                "v": str(row.v),
                "rank": int(row.rank),
                "score": float(row.score),
                "realized_within_h": int(1 if realized else 0),
                "first_realized_year": int(y) if realized else pd.NA,
                "time_to_fill": int(y - anchor) if realized else pd.NA,
            }
        )
    return pd.DataFrame(rows)


def _edge_first_causal_flag(corpus_df: pd.DataFrame) -> pd.DataFrame:
    edge_first = corpus_df.groupby(["src_code", "dst_code"], as_index=False).agg(first_year=("year", "min"))
    merged = edge_first.merge(
        corpus_df[["src_code", "dst_code", "year", "is_causal"]],
        left_on=["src_code", "dst_code", "first_year"],
        right_on=["src_code", "dst_code", "year"],
        how="left",
    )
    out = (
        merged.groupby(["src_code", "dst_code"], as_index=False)
        .agg(first_edge_causal=("is_causal", "max"))
        .rename(columns={"src_code": "u", "dst_code": "v"})
    )
    out["first_edge_causal"] = out["first_edge_causal"].fillna(False).astype(bool)
    return out


def compute_heterogeneity_tables(panel_df: pd.DataFrame, first_causal_df: pd.DataFrame) -> pd.DataFrame:
    if panel_df.empty:
        return pd.DataFrame(
            columns=[
                "breakdown",
                "group",
                "n_predictions",
                "realized_rate",
                "mean_score",
                "mean_rank",
                "mean_time_to_fill",
            ]
        )

    p = panel_df.copy()
    p["source_field"] = p["u"].astype(str).str[0]
    p["target_field"] = p["v"].astype(str).str[0]
    p["decade"] = (pd.to_numeric(p["anchor_year"], errors="coerce").fillna(0).astype(int) // 10) * 10
    p = p.merge(first_causal_df, how="left", on=["u", "v"])
    p["first_edge_causal"] = p["first_edge_causal"].astype("boolean").fillna(False).astype(bool)
    p["causal_subsample"] = p["first_edge_causal"].map({True: "causal_first", False: "noncausal_first"})

    def agg(g: pd.DataFrame, breakdown: str, group: str) -> dict:
        return {
            "breakdown": breakdown,
            "group": str(group),
            "n_predictions": int(len(g)),
            "realized_rate": float(g["realized_within_h"].mean()),
            "mean_score": float(g["score"].mean()) if "score" in g.columns else float("nan"),
            "mean_rank": float(g["rank"].mean()) if "rank" in g.columns else float("nan"),
            "mean_time_to_fill": float(g["time_to_fill"].mean()) if "time_to_fill" in g.columns else float("nan"),
        }

    rows: list[dict] = []
    for fld, g in p.groupby("source_field"):
        rows.append(agg(g, "field_source", fld))
    for dec, g in p.groupby("decade"):
        rows.append(agg(g, "anchor_decade", dec))
    for sub, g in p.groupby("causal_subsample"):
        rows.append(agg(g, "causal_subsample", sub))
    for (fld, sub), g in p.groupby(["source_field", "causal_subsample"]):
        rows.append(agg(g, "field_x_causal", f"{fld}|{sub}"))
    return pd.DataFrame(rows).sort_values(["breakdown", "group"]).reset_index(drop=True)


def write_field_gap_atlas(table_df: pd.DataFrame, out_path: Path) -> tuple[list[str], list[str]]:
    field_tbl = table_df[(table_df["breakdown"] == "field_source") & (table_df["n_predictions"] >= 30)].copy()
    if field_tbl.empty:
        out_path.write_text("# Field Gap Atlas\n\nInsufficient field-level data.\n", encoding="utf-8")
        return [], []
    under = field_tbl.sort_values("realized_rate", ascending=True).head(5)
    rapid = field_tbl.sort_values("realized_rate", ascending=False).head(5)
    lines = ["# Field Gap Atlas", "", "## Under-filled Fields", ""]
    for r in under.itertuples(index=False):
        lines.append(f"- {r.group}: realized_rate={float(r.realized_rate):.4f}, n={int(r.n_predictions)}")
    lines.extend(["", "## Rapid-fill Fields", ""])
    for r in rapid.itertuples(index=False):
        lines.append(f"- {r.group}: realized_rate={float(r.realized_rate):.4f}, n={int(r.n_predictions)}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [str(x) for x in under["group"].tolist()], [str(x) for x in rapid["group"].tolist()]


def write_opportunity_examples(
    candidates_df: pd.DataFrame,
    panel_df: pd.DataFrame,
    underfilled_fields: list[str],
    out_path: Path,
    n_examples: int = 10,
) -> None:
    c = candidates_df.copy()
    c["source_field"] = c["u"].astype(str).str[0]
    if underfilled_fields:
        c = c[c["source_field"].isin(underfilled_fields)]
    c = c.sort_values("score", ascending=False).head(max(n_examples * 3, n_examples))
    realized_map = (
        panel_df[["u", "v", "realized_within_h"]]
        .drop_duplicates(subset=["u", "v"])
        .set_index(["u", "v"])["realized_within_h"]
        .to_dict()
        if not panel_df.empty and {"u", "v", "realized_within_h"}.issubset(panel_df.columns)
        else {}
    )
    lines = ["# Opportunity Examples", ""]
    lines.append("High-scoring missing claims in under-filled fields:")
    lines.append("")
    picked = 0
    for row in c.itertuples(index=False):
        if picked >= n_examples:
            break
        realized = realized_map.get((str(row.u), str(row.v)))
        lines.append(
            f"- {row.u}->{row.v} | score={float(row.score):.4f} | field={str(row.source_field)} | "
            f"realized_in_vintage_window={int(realized) if realized is not None else 'NA'}"
        )
        picked += 1
    if picked == 0:
        lines.append("- none")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Field/decade/causal heterogeneity analysis for paper outputs.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--candidates", required=True, dest="candidates_path")
    parser.add_argument(
        "--candidate-kind",
        default="directed_causal",
        choices=[
            "directed_causal",
            "undirected_noncausal",
            "contextual_pair",
            "ordered_claim",
            "causal_claim",
            "identified_causal_claim",
        ],
    )
    parser.add_argument("--candidate-family-mode", default="path_to_direct", choices=["path_to_direct", "direct_to_path"])
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus = load_corpus(args.corpus_path)
    candidates = pd.read_parquet(args.candidates_path)
    first_year = first_appearance_map(
        corpus,
        candidate_kind=str(args.candidate_kind),
        candidate_family_mode=str(args.candidate_family_mode),
    )

    panel = _load_vintage_panel(out_dir=out_dir, candidates_df=candidates, first_year=first_year)
    first_causal = _edge_first_causal_flag(corpus)
    hetero = compute_heterogeneity_tables(panel, first_causal_df=first_causal)

    pq = out_dir / "heterogeneity_tables.parquet"
    csv = out_dir / "heterogeneity_tables.csv"
    atlas = out_dir / "field_gap_atlas.md"
    opp = out_dir / "opportunity_examples.md"

    hetero.to_parquet(pq, index=False)
    hetero.to_csv(csv, index=False)
    under, rapid = write_field_gap_atlas(hetero, atlas)
    write_opportunity_examples(candidates, panel, underfilled_fields=under, out_path=opp, n_examples=10)

    print(f"Wrote: {pq}")
    print(f"Wrote: {csv}")
    print(f"Wrote: {atlas}")
    print(f"Wrote: {opp}")


if __name__ == "__main__":
    main()
