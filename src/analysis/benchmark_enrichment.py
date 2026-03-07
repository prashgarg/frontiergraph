from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.common import ensure_output_dir, jaccard, normalize_text, tokenize
from src.utils import load_corpus


def build_node_mapping(corpus_df: pd.DataFrame) -> tuple[dict[str, str], list[tuple[str, str, set[str]]]]:
    src = corpus_df[["src_code", "src_label"]].rename(columns={"src_code": "code", "src_label": "label"})
    dst = corpus_df[["dst_code", "dst_label"]].rename(columns={"dst_code": "code", "dst_label": "label"})
    nodes = pd.concat([src, dst], ignore_index=True)
    nodes["label_norm"] = nodes["label"].astype(str).map(normalize_text)
    nodes = (
        nodes.groupby(["code", "label_norm"], as_index=False)
        .size()
        .sort_values(["label_norm", "size"], ascending=[True, False])
        .drop_duplicates(subset=["label_norm"])
    )
    exact = {str(r.label_norm): str(r.code) for r in nodes.itertuples(index=False)}
    candidates = [(str(r.code), str(r.label_norm), tokenize(str(r.label_norm))) for r in nodes.itertuples(index=False)]
    return exact, candidates


def map_text_to_code(text: str, exact_map: dict[str, str], candidates: list[tuple[str, str, set[str]]]) -> tuple[str | None, float]:
    n = normalize_text(text)
    if not n:
        return None, 0.0
    if n in exact_map:
        return exact_map[n], 1.0
    toks = tokenize(n)
    best_code = None
    best_score = 0.0
    for code, _label, cand_toks in candidates:
        score = jaccard(toks, cand_toks)
        if score > best_score:
            best_score = score
            best_code = code
    if best_score >= 0.50:
        return best_code, best_score
    return None, best_score


def load_plausibly_edges(
    path: Path,
    exact_map: dict[str, str],
    candidates: list[tuple[str, str, set[str]]],
) -> tuple[pd.DataFrame, dict]:
    df = pd.read_excel(path)
    if not {"lhs", "rhs"}.issubset(df.columns):
        return pd.DataFrame(columns=["u", "v", "source", "map_score_u", "map_score_v"]), {
            "source": "plausibly_exogenous",
            "rows": int(len(df)),
            "mapped_pairs": 0,
            "unmapped_pairs": int(len(df)),
        }

    rows: list[dict] = []
    mapped = 0
    for row in df.itertuples(index=False):
        u, su = map_text_to_code(getattr(row, "lhs", ""), exact_map, candidates)
        v, sv = map_text_to_code(getattr(row, "rhs", ""), exact_map, candidates)
        if u and v and u != v:
            mapped += 1
            rows.append(
                {
                    "u": u,
                    "v": v,
                    "source": "plausibly_exogenous",
                    "map_score_u": float(su),
                    "map_score_v": float(sv),
                }
            )
    out = pd.DataFrame(rows).drop_duplicates(subset=["u", "v"])
    log = {
        "source": "plausibly_exogenous",
        "rows": int(len(df)),
        "mapped_pairs": int(mapped),
        "unmapped_pairs": int(len(df) - mapped),
    }
    return out, log


def load_brodeur_edges(
    path: Path,
    corpus_df: pd.DataFrame,
    source_name: str,
    encoding: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    if encoding:
        df = pd.read_csv(path, encoding=encoding)
    else:
        df = pd.read_csv(path)
    if "title" not in df.columns:
        return pd.DataFrame(columns=["u", "v", "source"]), {
            "source": source_name,
            "rows": int(len(df)),
            "matched_titles": 0,
            "matched_papers": 0,
            "mapped_edges": 0,
        }
    corpus_titles = (
        corpus_df[["paper_id", "title"]]
        .drop_duplicates(subset=["paper_id"])
        .assign(title_norm=lambda x: x["title"].astype(str).map(normalize_text))
    )
    t2p = corpus_titles.groupby("title_norm")["paper_id"].apply(list).to_dict()
    matched_papers: set[str] = set()
    matched_titles = 0
    for title in df["title"].fillna("").astype(str):
        tn = normalize_text(title)
        if tn in t2p:
            matched_titles += 1
            matched_papers.update(str(pid) for pid in t2p[tn])
    edges = corpus_df[corpus_df["paper_id"].astype(str).isin(matched_papers)][["src_code", "dst_code"]].copy()
    edges["u"] = edges["src_code"].astype(str)
    edges["v"] = edges["dst_code"].astype(str)
    out = edges[["u", "v"]].drop_duplicates()
    out["source"] = source_name
    log = {
        "source": source_name,
        "rows": int(len(df)),
        "matched_titles": int(matched_titles),
        "matched_papers": int(len(matched_papers)),
        "mapped_edges": int(len(out)),
    }
    return out, log


def compute_enrichment(candidates: pd.DataFrame, benchmark_edges: pd.DataFrame) -> pd.DataFrame:
    c = candidates.copy()
    if "rank" not in c.columns:
        c = c.sort_values("score", ascending=False).reset_index(drop=True)
        c["rank"] = c.index + 1
    bset = set(zip(benchmark_edges["u"].astype(str), benchmark_edges["v"].astype(str)))
    c["is_benchmark"] = [int((str(r.u), str(r.v)) in bset) for r in c[["u", "v"]].itertuples(index=False)]
    base_rate = float(c["is_benchmark"].mean()) if len(c) else 0.0
    rows: list[dict] = []
    for k in [50, 100, 500, 1000, 5000, 10000]:
        top = c[c["rank"] <= k]
        if top.empty:
            continue
        rate = float(top["is_benchmark"].mean())
        rows.append(
            {
                "bucket": f"top_{k}",
                "k": int(k),
                "n": int(len(top)),
                "benchmark_hits": int(top["is_benchmark"].sum()),
                "top_rate": rate,
                "overall_rate": base_rate,
                "enrichment_ratio": float(rate / base_rate) if base_rate > 0 else np.nan,
            }
        )
    ranks_b = c[c["is_benchmark"] == 1]["rank"].astype(float)
    rows.append(
        {
            "bucket": "overall",
            "k": int(len(c)),
            "n": int(len(c)),
            "benchmark_hits": int(c["is_benchmark"].sum()),
            "top_rate": base_rate,
            "overall_rate": base_rate,
            "enrichment_ratio": 1.0,
            "rank_mean_benchmark": float(ranks_b.mean()) if len(ranks_b) else np.nan,
            "rank_median_benchmark": float(ranks_b.median()) if len(ranks_b) else np.nan,
        }
    )
    return pd.DataFrame(rows), c


def plot_benchmark_rank_diagnostics(candidates_with_flag: pd.DataFrame, enrichment_df: pd.DataFrame, out_path: Path) -> None:
    c = candidates_with_flag.copy().sort_values("rank")
    plt.figure(figsize=(10, 4.5))
    ax1 = plt.subplot(1, 2, 1)
    c["cum_hits"] = c["is_benchmark"].cumsum()
    denom = max(1, int(c["is_benchmark"].sum()))
    c["cum_hit_share"] = c["cum_hits"] / float(denom)
    ax1.plot(c["rank"], c["cum_hit_share"], color="tab:blue")
    ax1.set_xscale("log")
    ax1.set_xlabel("Rank (log scale)")
    ax1.set_ylabel("Cumulative benchmark hit share")
    ax1.set_title("Benchmark hit accumulation")

    ax2 = plt.subplot(1, 2, 2)
    sub = enrichment_df[enrichment_df["bucket"].str.startswith("top_")].copy()
    if not sub.empty:
        ax2.plot(sub["k"], sub["enrichment_ratio"], marker="o", color="tab:orange")
    ax2.set_xscale("log")
    ax2.set_xlabel("Top-K (log scale)")
    ax2.set_ylabel("Enrichment ratio")
    ax2.set_title("Enrichment in top ranks")
    ax2.axhline(1.0, color="gray", linestyle="--", linewidth=1)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark enrichment diagnostics using internal benchmark assets.")
    parser.add_argument("--benchdir", required=True, dest="bench_dir")
    parser.add_argument("--corpus", required=True, dest="corpus_path")
    parser.add_argument("--candidates", required=True, dest="candidates_path")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    bench_dir = Path(args.bench_dir)
    corpus = load_corpus(args.corpus_path)
    candidates = pd.read_parquet(args.candidates_path)

    exact, cand_map = build_node_mapping(corpus)
    logs: list[dict] = []
    edge_tables: list[pd.DataFrame] = []

    plaus_path = bench_dir / "plausibly_exogenous.xlsx"
    if plaus_path.exists():
        p_edges, p_log = load_plausibly_edges(plaus_path, exact, cand_map)
        edge_tables.append(p_edges)
        logs.append(p_log)

    brod1 = bench_dir / "brodeur_primary.csv"
    if brod1.exists():
        b1_edges, b1_log = load_brodeur_edges(brod1, corpus_df=corpus, source_name="brodeur_primary", encoding=None)
        edge_tables.append(b1_edges)
        logs.append(b1_log)

    brod2 = bench_dir / "brodeur_with_wp.csv"
    if brod2.exists():
        b2_edges, b2_log = load_brodeur_edges(brod2, corpus_df=corpus, source_name="brodeur_with_wp", encoding="latin1")
        edge_tables.append(b2_edges)
        logs.append(b2_log)

    bench_edges = (
        pd.concat(edge_tables, ignore_index=True)[["u", "v", "source"]].drop_duplicates(subset=["u", "v"])
        if edge_tables
        else pd.DataFrame(columns=["u", "v", "source"])
    )
    enrich_df, flagged = compute_enrichment(candidates, bench_edges)

    log_df = pd.DataFrame(logs)
    log_csv = out_dir / "benchmark_mapping_log.csv"
    enr_pq = out_dir / "enrichment_results.parquet"
    enr_csv = out_dir / "enrichment_results.csv"
    fig = out_dir / "benchmark_rank_plots.png"
    edge_pq = out_dir / "benchmark_edges_mapped.parquet"

    log_df.to_csv(log_csv, index=False)
    enrich_df.to_parquet(enr_pq, index=False)
    enrich_df.to_csv(enr_csv, index=False)
    bench_edges.to_parquet(edge_pq, index=False)
    plot_benchmark_rank_diagnostics(flagged, enrich_df, fig)

    print(f"Wrote: {log_csv}")
    print(f"Wrote: {enr_pq}")
    print(f"Wrote: {enr_csv}")
    print(f"Wrote: {edge_pq}")
    print(f"Wrote: {fig}")


if __name__ == "__main__":
    main()

