from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.common import ensure_output_dir
from src.analysis.ranking_utils import build_all_pairs, missing_pairs, pref_attach_ranking
from src.utils import load_corpus


def _node_label_map(corpus_df: pd.DataFrame) -> dict[str, str]:
    src = corpus_df[["src_code", "src_label"]].drop_duplicates().rename(columns={"src_code": "code", "src_label": "label"})
    dst = corpus_df[["dst_code", "dst_label"]].drop_duplicates().rename(columns={"dst_code": "code", "dst_label": "label"})
    nodes = pd.concat([src, dst], ignore_index=True).drop_duplicates(subset=["code"])
    return {str(r.code): str(r.label) for r in nodes.itertuples(index=False)}


def _build_support_lookups(corpus_df: pd.DataFrame) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], dict[tuple[str, str], list[dict]]]:
    edge_counts = (
        corpus_df.groupby(["src_code", "dst_code"], as_index=False)
        .agg(weight=("paper_id", "size"))
        .astype({"src_code": str, "dst_code": str})
    )
    out_map: dict[str, dict[str, float]] = {}
    in_map: dict[str, dict[str, float]] = {}
    for row in edge_counts.itertuples(index=False):
        out_map.setdefault(str(row.src_code), {})[str(row.dst_code)] = float(row.weight)
        in_map.setdefault(str(row.dst_code), {})[str(row.src_code)] = float(row.weight)

    paper_rows = (
        corpus_df[["src_code", "dst_code", "paper_id", "title", "year"]]
        .drop_duplicates(subset=["src_code", "dst_code", "paper_id"])
        .sort_values(["src_code", "dst_code", "year"], ascending=[True, True, False])
    )
    paper_lookup: dict[tuple[str, str], list[dict]] = {}
    for r in paper_rows.itertuples(index=False):
        key = (str(r.src_code), str(r.dst_code))
        paper_lookup.setdefault(key, []).append(
            {"paper_id": str(r.paper_id), "title": str(r.title), "year": int(r.year)}
        )
    return out_map, in_map, paper_lookup


def _edge_brief(
    u: str,
    v: str,
    out_map: dict[str, dict[str, float]],
    in_map: dict[str, dict[str, float]],
    paper_lookup: dict[tuple[str, str], list[dict]],
) -> tuple[str, str]:
    out_u = out_map.get(str(u), {})
    in_v = in_map.get(str(v), {})
    shared = sorted(set(out_u).intersection(in_v))
    mediators: list[tuple[str, float]] = []
    for w in shared:
        mediators.append((str(w), float(out_u.get(w, 0.0) * in_v.get(w, 0.0))))
    mediators = sorted(mediators, key=lambda x: x[1], reverse=True)[:3]

    med_txt = ", ".join([f"{m}({s:.1f})" for m, s in mediators]) if mediators else "none"
    papers: list[str] = []
    for m, _s in mediators[:2]:
        p1 = paper_lookup.get((str(u), str(m)), [])
        p2 = paper_lookup.get((str(m), str(v)), [])
        if p1:
            papers.append(f"{p1[0]['paper_id']}:{p1[0]['year']}")
        if p2:
            papers.append(f"{p2[0]['paper_id']}:{p2[0]['year']}")
    ptxt = ", ".join(papers) if papers else "none"
    return med_txt, ptxt


def _pick_unique_edges(df: pd.DataFrame, n: int, seen: set[tuple[str, str]]) -> list[tuple[str, str, float]]:
    picked: list[tuple[str, str, float]] = []
    for r in df.itertuples(index=False):
        e = (str(r.u), str(r.v))
        if e in seen:
            continue
        seen.add(e)
        score = float(getattr(r, "score", 0.0))
        picked.append((e[0], e[1], score))
        if len(picked) >= n:
            break
    return picked


def build_expert_pack(
    corpus_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    n_per_arm: int = 30,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    label_map = _node_label_map(corpus_df)
    out_map, in_map, paper_lookup = _build_support_lookups(corpus_df)
    nodes = sorted(set(corpus_df["src_code"].astype(str)) | set(corpus_df["dst_code"].astype(str)))
    all_pairs = build_all_pairs(nodes)
    pref = pref_attach_ranking(corpus_df, all_pairs_df=all_pairs)
    missing = missing_pairs(corpus_df, all_pairs_df=all_pairs)

    main = candidates_df[["u", "v", "score"]].sort_values("score", ascending=False).reset_index(drop=True)
    if "score" not in pref.columns:
        pref["score"] = 0.0

    seen: set[tuple[str, str]] = set()
    main_pick = _pick_unique_edges(main, n=n_per_arm, seen=seen)
    pref_pick = _pick_unique_edges(pref[["u", "v", "score"]], n=n_per_arm, seen=seen)

    remaining = missing.copy()
    if not remaining.empty:
        remaining["edge"] = list(zip(remaining["u"].astype(str), remaining["v"].astype(str)))
        remaining = remaining[~remaining["edge"].isin(seen)][["u", "v"]].reset_index(drop=True)
    if len(remaining) > n_per_arm:
        rand_idx = rng.choice(len(remaining), size=n_per_arm, replace=False)
        rand_df = remaining.iloc[rand_idx].copy()
    else:
        rand_df = remaining.copy()
    rand_pick = [(str(r.u), str(r.v), 0.0) for r in rand_df[["u", "v"]].itertuples(index=False)]

    rows: list[dict] = []
    for arm, picked in [("main_top", main_pick), ("pref_top", pref_pick), ("random_missing", rand_pick)]:
        for u, v, score in picked:
            med_txt, paper_txt = _edge_brief(u, v, out_map=out_map, in_map=in_map, paper_lookup=paper_lookup)
            rows.append(
                {
                    "arm": arm,
                    "u": str(u),
                    "v": str(v),
                    "u_label": label_map.get(str(u), str(u)),
                    "v_label": label_map.get(str(v), str(v)),
                    "model_score": float(score),
                    "mediator_hint": med_txt,
                    "paper_trace_hint": paper_txt,
                }
            )
    full = pd.DataFrame(rows)
    if full.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    blinded = full.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    blinded["item_id"] = [f"EXP{int(i + 1):03d}" for i in range(len(blinded))]
    answer_key = blinded[["item_id", "arm", "u", "v", "model_score"]].copy()

    eval_sheet = blinded[
        ["item_id", "u_label", "v_label", "mediator_hint", "paper_trace_hint"]
    ].copy()
    eval_sheet["plausibility_1to7"] = ""
    eval_sheet["novelty_1to7"] = ""
    eval_sheet["priority_1to7"] = ""
    eval_sheet["comments"] = ""
    return blinded, answer_key, eval_sheet


def write_instructions(
    blinded_df: pd.DataFrame,
    out_path: Path,
) -> None:
    n = int(len(blinded_df))
    lines = [
        "# Workstream 11: Expert Validation Pack",
        "",
        "## Objective",
        "Blindly score candidate missing claims to test whether algorithmic ranking aligns with expert judgment.",
        "",
        "## Hypotheses",
        "1. Main-top items receive higher plausibility and priority scores than random missing edges.",
        "2. Main-top items outperform pref-top items on novelty-adjusted priority.",
        "3. Signal traces (mediator + paper hints) increase confidence in reviewer judgments.",
        "",
        "## Rating Protocol",
        "- Rate each item on plausibility, novelty, and priority using 1-7 scales.",
        "- Use comments to flag false-mechanism paths or unclear concept mapping.",
        "- Keep ratings blind to source arm until key reveal.",
        "",
        f"## Pack Size\n- total items: {n}",
    ]
    if not blinded_df.empty:
        counts = blinded_df["arm"].value_counts().to_dict()
        lines.append(f"- arm composition (hidden from reviewers): {counts}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a blinded expert-validation packet for candidate claims.")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--candidates", required=True, dest="candidates_path")
    parser.add_argument("--n_per_arm", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    corpus_df = load_corpus(args.corpus_path)
    candidates_df = pd.read_parquet(args.candidates_path)

    blinded, answer_key, eval_sheet = build_expert_pack(
        corpus_df,
        candidates_df,
        n_per_arm=int(args.n_per_arm),
        seed=int(args.seed),
    )

    blinded_csv = out_dir / "expert_items_blinded.csv"
    key_csv = out_dir / "expert_answer_key.csv"
    eval_csv = out_dir / "expert_rating_sheet.csv"
    instructions_md = out_dir / "instructions.md"

    blinded.to_csv(blinded_csv, index=False)
    answer_key.to_csv(key_csv, index=False)
    eval_sheet.to_csv(eval_csv, index=False)
    write_instructions(blinded, instructions_md)

    print(f"Wrote: {blinded_csv}")
    print(f"Wrote: {key_csv}")
    print(f"Wrote: {eval_csv}")
    print(f"Wrote: {instructions_md}")


if __name__ == "__main__":
    main()
