from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib-codex"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research_allocation_v2 import candidate_layer_mask
from src.utils import ensure_dir


DEFAULT_OUT = ROOT / "outputs/paper/167_exploratory_testbeds"
DEFAULT_PATH_PANEL = ROOT / "outputs/paper/156_effective_benchmark_widened_1990_2015_detail_on/historical_feature_panel.parquet"
DEFAULT_DIRECT_PANEL = ROOT / "outputs/paper/145_effective_benchmark_direct_to_path/historical_feature_panel.parquet"
DEFAULT_CORPUS = ROOT / "data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet"
DEFAULT_PAPER_META = ROOT / "data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet"
DEFAULT_AUTHORSHIPS = ROOT / "data/processed/research_allocation_v2/paper_authorships.parquet"
DEFAULT_OPENALEX_SQLITE = ROOT / "data/processed/openalex/published_enriched/openalex_published_enriched.sqlite"
DEFAULT_DERIVED_OPENALEX_DIR = ROOT / "data/processed/openalex/derived_testbeds"

GENERAL_INTEREST_VENUES = {
    "american economic review",
    "quarterly journal of economics",
    "journal of political economy",
    "econometrica",
    "review of economic studies",
    "economic journal",
    "journal of the european economic association",
}

FAMILY_LABELS = {
    "path_to_direct": "Path-to-direct",
    "direct_to_path": "Direct-to-path",
}

HORIZON_ORDER = [5, 10, 15]
DISTANCE_CAP = 6


def _safe_json_list(value: Any) -> list[Any]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _safe_json_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "[]"
    text = str(value or "").strip()
    return text or "[]"


def _normalize_work_id(paper_id: str) -> str:
    text = str(paper_id or "")
    return text.split("__", 1)[0]


def _prediction_key(row: pd.Series) -> str:
    return f"{row['candidate_family_mode']}|{row['source_id']}|{row['target_id']}"


def _staged_sqlite_path(sqlite_path: Path) -> Path:
    staged = Path(tempfile.gettempdir()) / "frontiergraph_openalex_published_enriched.sqlite"
    if staged.exists():
        try:
            if staged.stat().st_size == sqlite_path.stat().st_size and staged.stat().st_mtime >= sqlite_path.stat().st_mtime:
                print(f"[testbeds] reusing staged OpenAlex sqlite at {staged}", flush=True)
                return staged
        except FileNotFoundError:
            pass
        staged.unlink(missing_ok=True)
    print(f"[testbeds] staging OpenAlex sqlite to {staged}", flush=True)
    shutil.copy2(sqlite_path, staged)
    return staged


def _open_sqlite(sqlite_path: Path) -> sqlite3.Connection:
    target = sqlite_path
    if sqlite_path.parent != Path(tempfile.gettempdir()):
        target = _staged_sqlite_path(sqlite_path)
    return sqlite3.connect(f"file:{target}?mode=ro", uri=True)


def _read_realized_panel(panel_path: Path, family_mode: str) -> pd.DataFrame:
    cols = [
        "candidate_id",
        "candidate_family_mode",
        "source_id",
        "target_id",
        "source_label",
        "target_label",
        "focal_mediator_id",
        "focal_mediator_label",
        "top_mediators_json",
        "top_paths_json",
        "cutoff_year_t",
        "horizon",
        "first_realized_year",
        "appears_within_h",
        "in_pool_5000",
        "pair_id",
    ]
    df = pd.read_parquet(panel_path, columns=cols)
    if "candidate_family_mode" not in df.columns:
        df["candidate_family_mode"] = family_mode
    df["candidate_family_mode"] = df["candidate_family_mode"].fillna(family_mode).astype(str)
    df = df[df["candidate_family_mode"] == family_mode].copy()
    if "in_pool_5000" in df.columns:
        df = df[df["in_pool_5000"].astype(bool)].copy()
    df = df[df["appears_within_h"].astype(bool)].copy()
    if df.empty:
        return df
    df["cutoff_year_t"] = pd.to_numeric(df["cutoff_year_t"], errors="coerce").astype(int)
    df["horizon"] = pd.to_numeric(df["horizon"], errors="coerce").astype(int)
    df["first_realized_year"] = pd.to_numeric(df["first_realized_year"], errors="coerce")
    df = df[df["first_realized_year"].notna()].copy()
    df["first_realized_year"] = df["first_realized_year"].astype(int)
    df["prediction_key"] = df.apply(_prediction_key, axis=1)
    df["event_mediator_ids_json"] = df["focal_mediator_id"].apply(
        lambda x: json.dumps([str(x)], ensure_ascii=True) if pd.notna(x) and str(x).strip() else "[]"
    )
    df["event_support_edges_json"] = "[]"
    keep = [
        "candidate_id",
        "candidate_family_mode",
        "prediction_key",
        "source_id",
        "target_id",
        "source_label",
        "target_label",
        "focal_mediator_id",
        "focal_mediator_label",
        "top_mediators_json",
        "top_paths_json",
        "cutoff_year_t",
        "horizon",
        "first_realized_year",
        "pair_id",
        "event_mediator_ids_json",
        "event_support_edges_json",
    ]
    return df[keep].drop_duplicates().reset_index(drop=True)


def _load_core_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path_panel = _read_realized_panel(Path(args.path_panel), "path_to_direct")
    direct_panel = _read_realized_panel(Path(args.direct_panel), "direct_to_path")
    corpus_cols = [
        "paper_id",
        "year",
        "title",
        "authors",
        "venue",
        "source",
        "src_code",
        "dst_code",
        "src_label",
        "dst_label",
        "edge_kind",
        "relation_type",
        "causal_presentation",
        "directionality_raw",
    ]
    corpus_df = pd.read_parquet(Path(args.corpus), columns=corpus_cols)
    meta_cols = [
        "paper_id",
        "year",
        "title",
        "authors",
        "venue",
        "primary_subfield_display_name",
        "unique_funder_count",
        "first_funder",
        "funder_display_names",
        "funder_ids",
    ]
    paper_meta = pd.read_parquet(Path(args.paper_meta), columns=meta_cols)
    authorships = pd.read_parquet(Path(args.authorships))
    return path_panel, direct_panel, corpus_df, paper_meta, authorships


def _prepare_direct_rows(corpus_df: pd.DataFrame) -> pd.DataFrame:
    direct = corpus_df[corpus_df["edge_kind"].astype(str) == "directed_causal"].copy()
    direct["src_code"] = direct["src_code"].astype(str)
    direct["dst_code"] = direct["dst_code"].astype(str)
    direct["paper_id"] = direct["paper_id"].astype(str)
    direct["year"] = pd.to_numeric(direct["year"], errors="coerce").astype(int)
    return direct.drop_duplicates(subset=["paper_id", "year", "src_code", "dst_code"]).reset_index(drop=True)


def _prepare_support_rows(corpus_df: pd.DataFrame) -> pd.DataFrame:
    ordered = corpus_df[candidate_layer_mask(corpus_df, "ordered_claim")][
        ["paper_id", "year", "src_code", "dst_code"]
    ].copy()
    contextual = corpus_df[candidate_layer_mask(corpus_df, "contextual_pair")][
        ["paper_id", "year", "src_code", "dst_code"]
    ].copy()
    if not contextual.empty:
        left = contextual["src_code"].astype(str)
        right = contextual["dst_code"].astype(str)
        swap_mask = left > right
        left_vals = contextual.loc[swap_mask, "src_code"].copy()
        contextual.loc[swap_mask, "src_code"] = contextual.loc[swap_mask, "dst_code"].values
        contextual.loc[swap_mask, "dst_code"] = left_vals.values
        rev = contextual.rename(columns={"src_code": "dst_code", "dst_code": "src_code"})
        support = pd.concat([ordered, contextual, rev], ignore_index=True)
    else:
        support = ordered
    support["paper_id"] = support["paper_id"].astype(str)
    support["year"] = pd.to_numeric(support["year"], errors="coerce").astype(int)
    support["src_code"] = support["src_code"].astype(str)
    support["dst_code"] = support["dst_code"].astype(str)
    support = support.drop_duplicates(subset=["paper_id", "year", "src_code", "dst_code"]).sort_values(
        ["year", "src_code", "dst_code", "paper_id"]
    )
    return support.reset_index(drop=True)


def _paper_meta_lookup(paper_meta: pd.DataFrame) -> pd.DataFrame:
    meta = paper_meta.copy()
    meta["paper_id"] = meta["paper_id"].astype(str)
    meta["realizing_work_id"] = meta["paper_id"].map(_normalize_work_id)
    return meta.drop_duplicates(subset=["paper_id"])


def _map_path_to_direct_realizers(realized_df: pd.DataFrame, direct_rows: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    print(
        f"[testbeds] path-to-direct mapper: {len(realized_df):,} realized prediction rows, {len(direct_rows):,} direct corpus rows",
        flush=True,
    )
    merged = realized_df.merge(
        direct_rows.rename(columns={"src_code": "source_id", "dst_code": "target_id"}),
        on=["source_id", "target_id"],
        how="left",
        suffixes=("", "_corpus"),
    )
    merged = merged[
        merged["year"].notna()
        & (pd.to_numeric(merged["year"], errors="coerce") >= merged["cutoff_year_t"])
        & (pd.to_numeric(merged["year"], errors="coerce") <= (merged["cutoff_year_t"] + merged["horizon"]))
    ].copy()
    merged["realizing_paper_id"] = merged["paper_id"].astype(str)
    merged["realizing_paper_year"] = pd.to_numeric(merged["year"], errors="coerce").astype(int)
    merged["is_first_realizing_paper"] = (
        merged["realizing_paper_year"] == pd.to_numeric(merged["first_realized_year"], errors="coerce").astype(int)
    ).astype(int)
    merged["is_first_realization_event"] = merged["is_first_realizing_paper"]
    key_cols = ["candidate_id", "cutoff_year_t", "horizon"]
    n_map = (
        merged.groupby(key_cols, as_index=False)
        .agg(n_realizing_papers_within_h=("realizing_paper_id", "nunique"))
        .astype({"n_realizing_papers_within_h": int})
    )
    merged = merged.merge(n_map, on=key_cols, how="left")
    keep = [
        "candidate_id",
        "candidate_family_mode",
        "prediction_key",
        "source_id",
        "target_id",
        "source_label",
        "target_label",
        "focal_mediator_id",
        "focal_mediator_label",
        "top_mediators_json",
        "top_paths_json",
        "cutoff_year_t",
        "horizon",
        "first_realized_year",
        "pair_id",
        "event_mediator_ids_json",
        "event_support_edges_json",
        "realizing_paper_id",
        "realizing_paper_year",
        "is_first_realizing_paper",
        "is_first_realization_event",
        "n_realizing_papers_within_h",
    ]
    out = merged[keep].drop_duplicates().reset_index(drop=True)
    summary = {
        "family": "path_to_direct",
        "n_realized_prediction_rows": int(len(realized_df)),
        "n_uptake_rows": int(len(out)),
        "n_unique_realizing_papers": int(out["realizing_paper_id"].nunique()) if not out.empty else 0,
        "n_missing_realizers": int(len(realized_df) - out[key_cols].drop_duplicates().shape[0]),
    }
    return out, summary


def _build_direct_to_path_event_lookup(support_rows: pd.DataFrame, target_pairs: set[tuple[str, str]]) -> dict[tuple[str, str], dict[str, Any]]:
    target_pairs = {(str(u), str(v)) for u, v in target_pairs if str(u) != str(v)}
    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    existing_edges: set[tuple[str, str]] = set()
    remaining = set(target_pairs)
    events: dict[tuple[str, str], dict[str, Any]] = {}

    edge_papers_by_year: dict[int, dict[tuple[str, str], set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in support_rows.itertuples(index=False):
        edge_papers_by_year[int(row.year)][(str(row.src_code), str(row.dst_code))].add(str(row.paper_id))

    for year in sorted(edge_papers_by_year.keys()):
        batch_edge_papers = edge_papers_by_year[year]
        batch_edges = set(batch_edge_papers.keys())
        new_edges = batch_edges.difference(existing_edges)
        if not new_edges:
            continue
        if year % 5 == 0 or year == min(edge_papers_by_year.keys()) or len(remaining) < 100:
            print(
                f"[testbeds] direct-to-path event lookup year={year}: new_edges={len(new_edges):,}, remaining_pairs={len(remaining):,}",
                flush=True,
            )
        for u, v in new_edges:
            existing_edges.add((u, v))
            outgoing[u].add(v)
            incoming[v].add(u)

        impacted_pairs: set[tuple[str, str]] = set()
        for a, b in new_edges:
            for u in incoming.get(a, set()):
                if u != b:
                    impacted_pairs.add((u, b))
            for v in outgoing.get(b, set()):
                if a != v:
                    impacted_pairs.add((a, v))

        for pair in sorted(impacted_pairs.intersection(remaining)):
            u, v = pair
            mediators = sorted(outgoing.get(u, set()).intersection(incoming.get(v, set())))
            event_mediators: list[str] = []
            contributor_papers: set[str] = set()
            contributor_edges: list[dict[str, str]] = []
            for mediator in mediators:
                left_edge = (u, mediator)
                right_edge = (mediator, v)
                left_new = left_edge in new_edges
                right_new = right_edge in new_edges
                if not (left_new or right_new):
                    continue
                event_mediators.append(mediator)
                if left_new:
                    contributor_edges.append({"src": u, "dst": mediator})
                    contributor_papers.update(batch_edge_papers.get(left_edge, set()))
                if right_new:
                    contributor_edges.append({"src": mediator, "dst": v})
                    contributor_papers.update(batch_edge_papers.get(right_edge, set()))
            if not event_mediators:
                continue
            events[pair] = {
                "first_realized_year": int(year),
                "paper_ids": sorted(contributor_papers),
                "event_mediator_ids_json": json.dumps(sorted(set(event_mediators)), ensure_ascii=True),
                "event_support_edges_json": json.dumps(contributor_edges, ensure_ascii=True),
                "n_realizing_papers_within_h": int(len(contributor_papers)),
            }
            remaining.remove(pair)
        if not remaining:
            break
    print(
        f"[testbeds] direct-to-path event lookup complete: events={len(events):,}, unresolved_pairs={len(remaining):,}",
        flush=True,
    )
    return events


def _map_direct_to_path_realizers(realized_df: pd.DataFrame, support_rows: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    print(
        f"[testbeds] direct-to-path mapper: {len(realized_df):,} realized prediction rows, {len(support_rows):,} support rows",
        flush=True,
    )
    event_lookup = _build_direct_to_path_event_lookup(
        support_rows=support_rows,
        target_pairs={(str(r.source_id), str(r.target_id)) for r in realized_df.itertuples(index=False)},
    )
    rows: list[dict[str, Any]] = []
    missing = 0
    mismatched_year = 0
    for row in realized_df.itertuples(index=False):
        pair = (str(row.source_id), str(row.target_id))
        event = event_lookup.get(pair)
        if event is None:
            missing += 1
            continue
        if int(event["first_realized_year"]) != int(row.first_realized_year):
            mismatched_year += 1
        for paper_id in event["paper_ids"]:
            rows.append(
                {
                    "candidate_id": str(row.candidate_id),
                    "candidate_family_mode": str(row.candidate_family_mode),
                    "prediction_key": str(row.prediction_key),
                    "source_id": str(row.source_id),
                    "target_id": str(row.target_id),
                    "source_label": str(row.source_label),
                    "target_label": str(row.target_label),
                    "focal_mediator_id": None,
                    "focal_mediator_label": None,
                    "top_mediators_json": _safe_json_text(row.top_mediators_json),
                    "top_paths_json": _safe_json_text(row.top_paths_json),
                    "cutoff_year_t": int(row.cutoff_year_t),
                    "horizon": int(row.horizon),
                    "first_realized_year": int(event["first_realized_year"]),
                    "pair_id": str(row.pair_id),
                    "event_mediator_ids_json": str(event["event_mediator_ids_json"]),
                    "event_support_edges_json": str(event["event_support_edges_json"]),
                    "realizing_paper_id": str(paper_id),
                    "realizing_paper_year": int(event["first_realized_year"]),
                    "is_first_realizing_paper": 1,
                    "is_first_realization_event": 1,
                    "n_realizing_papers_within_h": int(event["n_realizing_papers_within_h"]),
                }
            )
    out = pd.DataFrame(rows)
    summary = {
        "family": "direct_to_path",
        "n_realized_prediction_rows": int(len(realized_df)),
        "n_uptake_rows": int(len(out)),
        "n_unique_realizing_papers": int(out["realizing_paper_id"].nunique()) if not out.empty else 0,
        "n_missing_realizers": int(missing),
        "n_mismatched_first_year": int(mismatched_year),
    }
    return out, summary


def _enrich_spine_with_paper_meta(spine_df: pd.DataFrame, paper_meta: pd.DataFrame) -> pd.DataFrame:
    meta = _paper_meta_lookup(paper_meta).rename(
        columns={
            "paper_id": "realizing_paper_id",
            "year": "realizing_meta_year",
            "title": "realizing_paper_title",
            "authors": "realizing_paper_authors",
            "venue": "realizing_paper_venue",
            "primary_subfield_display_name": "realizing_primary_subfield_display_name",
            "unique_funder_count": "realizing_unique_funder_count",
            "first_funder": "realizing_first_funder",
            "funder_display_names": "realizing_funder_display_names",
            "funder_ids": "realizing_funder_ids",
        }
    )
    out = spine_df.merge(meta, on="realizing_paper_id", how="left")
    out["realizing_paper_title"] = out["realizing_paper_title"].fillna("")
    out["realizing_paper_authors"] = out["realizing_paper_authors"].fillna("")
    out["realizing_paper_venue"] = out["realizing_paper_venue"].fillna("")
    out["realizing_primary_subfield_display_name"] = out["realizing_primary_subfield_display_name"].fillna("Unknown")
    out["realizing_unique_funder_count"] = pd.to_numeric(
        out["realizing_unique_funder_count"], errors="coerce"
    ).fillna(0).astype(int)
    out["realizing_paper_year"] = pd.to_numeric(out["realizing_paper_year"], errors="coerce").fillna(
        pd.to_numeric(out["realizing_meta_year"], errors="coerce")
    ).astype(int)
    out["realizing_work_id"] = out["realizing_paper_id"].map(_normalize_work_id)
    return out.drop(columns=["realizing_meta_year"])


def _build_uptake_spine(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    print("[testbeds] loading panels and corpus inputs", flush=True)
    path_panel, direct_panel, corpus_df, paper_meta, _ = _load_core_inputs(args)
    print(
        f"[testbeds] loaded inputs: path_panel={len(path_panel):,}, direct_panel={len(direct_panel):,}, corpus={len(corpus_df):,}, paper_meta={len(paper_meta):,}",
        flush=True,
    )
    direct_rows = _prepare_direct_rows(corpus_df)
    support_rows = _prepare_support_rows(corpus_df)
    print(
        f"[testbeds] prepared rows: direct_rows={len(direct_rows):,}, support_rows={len(support_rows):,}",
        flush=True,
    )

    path_spine, path_summary = _map_path_to_direct_realizers(path_panel, direct_rows)
    direct_spine, direct_summary = _map_direct_to_path_realizers(direct_panel, support_rows)
    spine_df = pd.concat([path_spine, direct_spine], ignore_index=True)
    spine_df = _enrich_spine_with_paper_meta(spine_df, paper_meta)
    spine_df = spine_df.sort_values(
        ["candidate_family_mode", "cutoff_year_t", "horizon", "candidate_id", "realizing_paper_year", "realizing_paper_id"]
    ).reset_index(drop=True)

    manifest = pd.DataFrame([path_summary, direct_summary])
    return spine_df, manifest


def _dedupe_for_paper_level(spine_df: pd.DataFrame) -> pd.DataFrame:
    adopters = spine_df[spine_df["is_first_realizing_paper"].astype(bool)].copy()
    if adopters.empty:
        return adopters
    adopters = adopters.sort_values(
        ["realizing_paper_id", "horizon", "prediction_key", "cutoff_year_t", "candidate_id"]
    )
    deduped = adopters.drop_duplicates(subset=["realizing_paper_id", "horizon", "prediction_key"]).reset_index(drop=True)
    return deduped


def _build_support_graphs_by_cutoff(corpus_df: pd.DataFrame, cutoffs: list[int]) -> dict[int, dict[str, set[str]]]:
    support_rows = _prepare_support_rows(corpus_df)
    graphs: dict[int, dict[str, set[str]]] = {}
    for cutoff in sorted(set(int(x) for x in cutoffs)):
        train = support_rows[support_rows["year"] <= (int(cutoff) - 1)]
        adj: dict[str, set[str]] = defaultdict(set)
        for row in train.itertuples(index=False):
            u = str(row.src_code)
            v = str(row.dst_code)
            adj[u].add(v)
            adj[v].add(u)
        graphs[int(cutoff)] = adj
    return graphs


def _shortest_path_cap(adj: dict[str, set[str]], start: str, targets: set[str], cap: int = DISTANCE_CAP) -> int | None:
    if start in targets:
        return 0
    seen = {start}
    q = deque([(start, 0)])
    while q:
        node, dist = q.popleft()
        if dist >= cap:
            continue
        for nxt in adj.get(node, set()):
            if nxt in seen:
                continue
            if nxt in targets:
                return dist + 1
            seen.add(nxt)
            q.append((nxt, dist + 1))
    return None


def _edge_pair_distance(adj: dict[str, set[str]], edge_a: tuple[str, str], edge_b: tuple[str, str]) -> int | None:
    a_nodes = {str(edge_a[0]), str(edge_a[1])}
    b_nodes = {str(edge_b[0]), str(edge_b[1])}
    dists = []
    for node in a_nodes:
        dist = _shortest_path_cap(adj, node, b_nodes, cap=DISTANCE_CAP)
        if dist is not None:
            dists.append(dist)
    return min(dists) if dists else None


def _family_mix(path_n: int, direct_n: int) -> str:
    total = int(path_n) + int(direct_n)
    if total <= 1:
        if path_n == 1:
            return "single_path_to_direct"
        if direct_n == 1:
            return "single_direct_to_path"
        return "none"
    if path_n > 0 and direct_n > 0:
        return "mixed_family"
    if path_n > 0:
        return "multi_path_only"
    return "multi_direct_only"


def _bundle_metrics_for_group(sub: pd.DataFrame, graph_cache: dict[int, dict[str, set[str]]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path_n = int((sub["candidate_family_mode"] == "path_to_direct").sum())
    direct_n = int((sub["candidate_family_mode"] == "direct_to_path").sum())
    source_counts = Counter(sub["source_id"].astype(str))
    target_counts = Counter(sub["target_id"].astype(str))
    endpoint_counts = Counter(list(sub["source_id"].astype(str)) + list(sub["target_id"].astype(str)))
    mediator_sets = [set(_safe_json_list(v)) for v in sub["event_mediator_ids_json"]]
    has_shared_mediator = False
    if mediator_sets:
        merged = Counter()
        for items in mediator_sets:
            for item in items:
                merged[str(item)] += 1
        has_shared_mediator = any(count > 1 for count in merged.values())

    pairwise_rows: list[dict[str, Any]] = []
    rows = list(sub.itertuples(index=False))
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            r1 = rows[i]
            r2 = rows[j]
            cutoff_ref = int(min(int(r1.cutoff_year_t), int(r2.cutoff_year_t)))
            adj = graph_cache.get(cutoff_ref, {})
            distance = _edge_pair_distance(
                adj,
                (str(r1.source_id), str(r1.target_id)),
                (str(r2.source_id), str(r2.target_id)),
            )
            pairwise_rows.append(
                {
                    "realizing_paper_id": str(r1.realizing_paper_id),
                    "horizon": int(r1.horizon),
                    "prediction_key_a": str(r1.prediction_key),
                    "prediction_key_b": str(r2.prediction_key),
                    "cutoff_reference_year": cutoff_ref,
                    "graph_distance": distance if distance is not None else np.nan,
                    "share_source": int(str(r1.source_id) == str(r2.source_id)),
                    "share_target": int(str(r1.target_id) == str(r2.target_id)),
                    "share_endpoint": int(
                        bool({str(r1.source_id), str(r1.target_id)}.intersection({str(r2.source_id), str(r2.target_id)}))
                    ),
                }
            )

    pairwise_df = pd.DataFrame(pairwise_rows)
    distance_series = (
        pd.to_numeric(pairwise_df["graph_distance"], errors="coerce").dropna() if not pairwise_df.empty else pd.Series(dtype=float)
    )
    out = {
        "predicted_edge_count": int(len(sub)),
        "path_to_direct_count": path_n,
        "direct_to_path_count": direct_n,
        "family_mix": _family_mix(path_n, direct_n),
        "unique_sources": int(len(source_counts)),
        "unique_targets": int(len(target_counts)),
        "unique_endpoints": int(len(endpoint_counts)),
        "has_shared_source": int(any(v > 1 for v in source_counts.values())),
        "has_shared_target": int(any(v > 1 for v in target_counts.values())),
        "has_shared_endpoint": int(any(v > 1 for v in endpoint_counts.values())),
        "has_shared_mediator": int(has_shared_mediator),
        "pairwise_edge_pairs": int(len(pairwise_df)),
        "min_graph_distance": float(distance_series.min()) if not distance_series.empty else np.nan,
        "mean_graph_distance": float(distance_series.mean()) if not distance_series.empty else np.nan,
    }
    return out, pairwise_rows


def _write_tex_table(df: pd.DataFrame, out_path: Path, index: bool = False, float_format: str | None = None) -> None:
    ensure_dir(out_path.parent)
    safe = df.copy()
    safe.columns = [str(col).replace("_", r"\_") for col in safe.columns]
    for col in safe.columns:
        if safe[col].dtype == object:
            safe[col] = safe[col].astype(str).str.replace("_", r"\_", regex=False)
    tex = safe.to_latex(index=index, escape=False, float_format=(lambda x: float_format % x) if float_format else None)
    out_path.write_text(tex, encoding="utf-8")


def _build_bundle_uptake_package(adopters: pd.DataFrame, corpus_df: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    ensure_dir(out_dir)
    graph_cache = _build_support_graphs_by_cutoff(corpus_df, adopters["cutoff_year_t"].astype(int).unique().tolist())
    bundle_rows: list[dict[str, Any]] = []
    pairwise_rows: list[dict[str, Any]] = []
    group_cols = [
        "realizing_paper_id",
        "realizing_work_id",
        "realizing_paper_year",
        "realizing_paper_title",
        "realizing_paper_venue",
        "realizing_primary_subfield_display_name",
        "horizon",
    ]
    for keys, sub in adopters.groupby(group_cols, sort=True):
        metrics, pair_rows = _bundle_metrics_for_group(sub, graph_cache)
        row = dict(zip(group_cols, keys))
        row.update(metrics)
        bundle_rows.append(row)
        pairwise_rows.extend(pair_rows)

    bundle_df = pd.DataFrame(bundle_rows)
    pairwise_df = pd.DataFrame(pairwise_rows)
    if bundle_df.empty:
        return {}

    summary = (
        bundle_df.groupby("horizon", as_index=False)
        .agg(
            n_papers=("realizing_paper_id", "nunique"),
            mean_predicted_edge_count=("predicted_edge_count", "mean"),
            share_multi_edge=("predicted_edge_count", lambda s: float((pd.to_numeric(s) > 1).mean())),
            share_mixed_family=("family_mix", lambda s: float((pd.Series(s) == "mixed_family").mean())),
            share_shared_endpoint=("has_shared_endpoint", "mean"),
            share_shared_mediator=("has_shared_mediator", "mean"),
            median_min_graph_distance=("min_graph_distance", "median"),
        )
        .sort_values("horizon")
    )

    mix = (
        bundle_df.groupby(["horizon", "family_mix"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
        .sort_values(["horizon", "family_mix"])
    )

    bundle_df.to_parquet(out_dir / "bundle_uptake_paper_level.parquet", index=False)
    bundle_df.to_csv(out_dir / "bundle_uptake_paper_level.csv", index=False)
    pairwise_df.to_parquet(out_dir / "bundle_uptake_pairwise.parquet", index=False)
    pairwise_df.to_csv(out_dir / "bundle_uptake_pairwise.csv", index=False)
    summary.to_csv(out_dir / "bundle_uptake_summary.csv", index=False)
    mix.to_csv(out_dir / "bundle_uptake_family_mix.csv", index=False)
    _write_tex_table(summary.round(3), out_dir / "bundle_uptake_summary.tex", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8))
    for ax, horizon in zip(axes, HORIZON_ORDER):
        sub = bundle_df[bundle_df["horizon"] == horizon]
        vals = sub["predicted_edge_count"].astype(int)
        bins = np.arange(1, min(int(vals.max()) if len(vals) else 1, 10) + 2) - 0.5
        ax.hist(vals, bins=bins, color="#1d4ed8", edgecolor="white")
        ax.set_title(f"h={horizon}")
        ax.set_xlabel("Predicted edges realized in same paper")
        ax.set_ylabel("Papers")
    fig.suptitle("Bundle uptake: predicted-edge counts per realizing paper", y=1.02)
    fig.tight_layout()
    fig.savefig(out_dir / "bundle_uptake_histogram.png", dpi=200, bbox_inches="tight")
    fig.savefig(out_dir / "bundle_uptake_histogram.pdf", bbox_inches="tight")
    plt.close(fig)

    mix_pivot = mix.pivot(index="horizon", columns="family_mix", values="n_papers").fillna(0)
    mix_pivot = mix_pivot.reindex(HORIZON_ORDER).fillna(0)
    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    bottom = np.zeros(len(mix_pivot))
    colors = {
        "single_path_to_direct": "#1d4ed8",
        "single_direct_to_path": "#b45309",
        "multi_path_only": "#60a5fa",
        "multi_direct_only": "#f59e0b",
        "mixed_family": "#7c3aed",
    }
    for col in [
        "single_path_to_direct",
        "single_direct_to_path",
        "multi_path_only",
        "multi_direct_only",
        "mixed_family",
    ]:
        vals = mix_pivot.get(col, pd.Series(0, index=mix_pivot.index)).values
        ax.bar(mix_pivot.index.astype(str), vals, bottom=bottom, label=col.replace("_", " "), color=colors[col])
        bottom += vals
    ax.set_ylabel("Realizing papers")
    ax.set_title("Bundle uptake: family mix within realizing papers")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out_dir / "bundle_uptake_family_mix.png", dpi=200, bbox_inches="tight")
    fig.savefig(out_dir / "bundle_uptake_family_mix.pdf", bbox_inches="tight")
    plt.close(fig)

    if not pairwise_df.empty:
        fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharey=True)
        for ax, horizon in zip(axes, HORIZON_ORDER):
            sub = pairwise_df[pairwise_df["horizon"] == horizon]
            vals = pd.to_numeric(sub["graph_distance"], errors="coerce").dropna()
            if vals.empty:
                ax.text(0.5, 0.5, "No multi-edge papers", ha="center", va="center", fontsize=9)
            else:
                bins = np.arange(0, DISTANCE_CAP + 2) - 0.5
                ax.hist(vals, bins=bins, color="#059669", edgecolor="white")
                ax.set_xticks(range(0, DISTANCE_CAP + 1))
            ax.set_title(f"h={horizon}")
            ax.set_xlabel("Endpoint graph distance")
        axes[0].set_ylabel("Edge-pair count")
        fig.suptitle("Bundle uptake: graph locality within multi-edge papers", y=1.02)
        fig.tight_layout()
        fig.savefig(out_dir / "bundle_uptake_graph_distance.png", dpi=200, bbox_inches="tight")
        fig.savefig(out_dir / "bundle_uptake_graph_distance.pdf", bbox_inches="tight")
        plt.close(fig)

    share_multi = summary.set_index("horizon")["share_multi_edge"].to_dict()
    share_mixed = summary.set_index("horizon")["share_mixed_family"].to_dict()
    note_lines = [
        "# Bundle uptake note",
        "",
        "This package studies whether later papers realize isolated predicted edges or bundles of nearby predicted edges.",
        "",
    ]
    for horizon in HORIZON_ORDER:
        if horizon not in share_multi:
            continue
        note_lines.append(
            f"- h={horizon}: share of realizing papers with more than one predicted edge = {float(share_multi[horizon]):.3f}; mixed-family share = {float(share_mixed[horizon]):.3f}."
        )
    (out_dir / "bundle_uptake_note.md").write_text("\n".join(note_lines) + "\n", encoding="utf-8")

    return {
        "bundle_df": bundle_df,
        "pairwise_df": pairwise_df,
        "summary_df": summary,
        "mix_df": mix,
    }


def _load_openalex_works_subset(sqlite_path: Path, work_ids: list[str]) -> pd.DataFrame:
    if not work_ids:
        return pd.DataFrame()
    conn = _open_sqlite(sqlite_path)
    out_frames = []
    try:
        chunk_size = 500
        for i in range(0, len(work_ids), chunk_size):
            chunk = work_ids[i : i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            query = f"""
                SELECT work_id, publication_year, source_display_name, frontiergraph_bucket,
                       primary_subfield_display_name, cited_by_count, authors_count
                FROM works_base
                WHERE work_id IN ({placeholders})
            """
            out_frames.append(pd.read_sql_query(query, conn, params=chunk))
    finally:
        conn.close()
    return pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame()


def _load_openalex_author_history(sqlite_path: Path, author_ids: list[str]) -> pd.DataFrame:
    if not author_ids:
        return pd.DataFrame()
    conn = _open_sqlite(sqlite_path)
    out_frames = []
    try:
        chunk_size = 400
        for i in range(0, len(author_ids), chunk_size):
            chunk = author_ids[i : i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            query = f"""
                SELECT wa.author_id,
                       wa.work_id,
                       wa.author_seq,
                       wa.author_position,
                       wa.is_corresponding,
                       wb.publication_year,
                       wb.primary_subfield_display_name,
                       wb.cited_by_count,
                       wb.frontiergraph_bucket,
                       wb.source_display_name
                FROM works_authorships wa
                JOIN works_base wb ON wa.work_id = wb.work_id
                WHERE wa.author_id IN ({placeholders})
            """
            out_frames.append(pd.read_sql_query(query, conn, params=chunk))
    finally:
        conn.close()
    return pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame()


def _load_focal_authorship_enrichment(sqlite_path: Path, work_ids: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not work_ids:
        return pd.DataFrame(), pd.DataFrame()
    conn = _open_sqlite(sqlite_path)
    auth_frames = []
    inst_frames = []
    try:
        chunk_size = 500
        for i in range(0, len(work_ids), chunk_size):
            chunk = work_ids[i : i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            auth_query = f"""
                SELECT work_id, author_seq, author_position, author_id, author_display_name, is_corresponding
                FROM works_authorships
                WHERE work_id IN ({placeholders})
            """
            inst_query = f"""
                SELECT work_id, author_seq, institution_id, display_name, country_code, type
                FROM works_authorship_institutions
                WHERE work_id IN ({placeholders})
            """
            auth_frames.append(pd.read_sql_query(auth_query, conn, params=chunk))
            inst_frames.append(pd.read_sql_query(inst_query, conn, params=chunk))
    finally:
        conn.close()
    auth_df = pd.concat(auth_frames, ignore_index=True) if auth_frames else pd.DataFrame()
    inst_df = pd.concat(inst_frames, ignore_index=True) if inst_frames else pd.DataFrame()
    return auth_df, inst_df


def _venue_bucket(venue: str, frontiergraph_bucket: str) -> str:
    norm = str(venue or "").strip().lower()
    if norm in GENERAL_INTEREST_VENUES:
        return "general_interest"
    bucket = str(frontiergraph_bucket or "").strip().lower()
    if "core_econ" in bucket:
        return "field"
    if "adjacent" in bucket:
        return "adjacent_interdisciplinary"
    return "other"


def _funder_bucket(n: int) -> str:
    n = int(n)
    if n <= 0:
        return "none"
    if n == 1:
        return "one"
    return "two_plus"


def _build_author_enrichment(
    adopters: pd.DataFrame,
    authorships: pd.DataFrame,
    sqlite_path: Path,
    derived_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ensure_dir(derived_dir)
    focal_papers = adopters[["realizing_paper_id", "realizing_work_id", "realizing_paper_year", "realizing_primary_subfield_display_name"]].drop_duplicates()
    focal_auth = authorships.rename(columns={"paper_id": "realizing_paper_id"}).copy()
    focal_auth["realizing_paper_id"] = focal_auth["realizing_paper_id"].astype(str)
    focal_auth["work_id"] = focal_auth["work_id"].astype(str)
    focal = focal_papers.merge(focal_auth, on="realizing_paper_id", how="left")
    focal = focal[focal["author_id"].notna()].copy()
    focal["author_id"] = focal["author_id"].astype(str)
    focal["institution_id"] = focal["institution_id"].fillna("").astype(str)

    work_ids = sorted(focal["realizing_work_id"].dropna().astype(str).unique())
    focal_works = _load_openalex_works_subset(sqlite_path, work_ids)
    focal_sql_auth, focal_sql_inst = _load_focal_authorship_enrichment(sqlite_path, work_ids)
    author_history = _load_openalex_author_history(sqlite_path, sorted(focal["author_id"].unique()))

    if not focal_sql_auth.empty:
        focal = focal.merge(
            focal_sql_auth.rename(columns={"work_id": "realizing_work_id"}),
            on=["realizing_work_id", "author_id", "author_position"],
            how="left",
            suffixes=("", "_sqlite"),
        )
    if not focal_sql_inst.empty and "author_seq" in focal.columns:
        focal = focal.merge(
            focal_sql_inst.rename(columns={"work_id": "realizing_work_id"}),
            on=["realizing_work_id", "author_seq", "institution_id"],
            how="left",
            suffixes=("", "_inst"),
        )
    if not focal_works.empty:
        focal = focal.merge(
            focal_works.rename(columns={"work_id": "realizing_work_id"}),
            on="realizing_work_id",
            how="left",
        )

    author_history["publication_year"] = pd.to_numeric(author_history["publication_year"], errors="coerce")
    focal["realizing_paper_year"] = pd.to_numeric(focal["realizing_paper_year"], errors="coerce")
    metrics_rows: list[dict[str, Any]] = []
    if not author_history.empty:
        by_author = {aid: grp.sort_values("publication_year").copy() for aid, grp in author_history.groupby("author_id", sort=False)}
        for row in focal.itertuples(index=False):
            hist = by_author.get(str(row.author_id))
            if hist is None or hist.empty or pd.isna(row.realizing_paper_year):
                metrics_rows.append(
                    {
                        "realizing_paper_id": str(row.realizing_paper_id),
                        "author_id": str(row.author_id),
                        "career_age_local": np.nan,
                        "prior_works_local": np.nan,
                        "prior_same_subfield_local": np.nan,
                        "prior_distinct_subfields_local": np.nan,
                        "prior_focal_subfield_share_local": np.nan,
                        "prior_lifetime_citations_local": np.nan,
                        "entrant_local": np.nan,
                        "bridge_author_local": np.nan,
                    }
                )
                continue
            prior = hist[hist["publication_year"] < float(row.realizing_paper_year)].copy()
            focal_subfield = str(row.realizing_primary_subfield_display_name or "")
            same_subfield = prior["primary_subfield_display_name"].fillna("").astype(str).eq(focal_subfield)
            earliest = pd.to_numeric(hist["publication_year"], errors="coerce").dropna()
            earliest_year = float(earliest.min()) if not earliest.empty else np.nan
            prior_works = int(len(prior))
            prior_same = int(same_subfield.sum())
            prior_distinct = int(prior["primary_subfield_display_name"].fillna("").astype(str).replace("", np.nan).dropna().nunique())
            prior_share = float(prior_same / prior_works) if prior_works > 0 else np.nan
            prior_cites = float(pd.to_numeric(prior["cited_by_count"], errors="coerce").fillna(0.0).sum())
            career_age = float(row.realizing_paper_year - earliest_year) if np.isfinite(earliest_year) else np.nan
            entrant = float(prior_same == 0) if prior_works >= 0 else np.nan
            bridge = float(prior_distinct >= 2 and (np.isnan(prior_share) or prior_share < 0.5)) if prior_works > 0 else np.nan
            metrics_rows.append(
                {
                    "realizing_paper_id": str(row.realizing_paper_id),
                    "author_id": str(row.author_id),
                    "career_age_local": career_age,
                    "prior_works_local": float(prior_works),
                    "prior_same_subfield_local": float(prior_same),
                    "prior_distinct_subfields_local": float(prior_distinct),
                    "prior_focal_subfield_share_local": prior_share,
                    "prior_lifetime_citations_local": prior_cites,
                    "entrant_local": entrant,
                    "bridge_author_local": bridge,
                }
            )
    metrics_df = pd.DataFrame(metrics_rows)
    focal_enriched = focal.merge(metrics_df, on=["realizing_paper_id", "author_id"], how="left")
    focal_enriched.to_parquet(derived_dir / "author_paper_enriched_local.parquet", index=False)
    focal_enriched.to_csv(derived_dir / "author_paper_enriched_local.csv", index=False)

    coverage = pd.DataFrame(
        [
            {
                "field": "author_id",
                "missing_share": float(focal_enriched["author_id"].isna().mean()) if len(focal_enriched) else np.nan,
            },
            {
                "field": "institution_country_code",
                "missing_share": float(focal_enriched["country_code"].replace("", np.nan).isna().mean()) if len(focal_enriched) else np.nan,
            },
            {
                "field": "institution_type",
                "missing_share": float(focal_enriched["type"].replace("", np.nan).isna().mean()) if len(focal_enriched) else np.nan,
            },
            {
                "field": "career_age_local",
                "missing_share": float(focal_enriched["career_age_local"].isna().mean()) if len(focal_enriched) else np.nan,
            },
            {
                "field": "prior_works_local",
                "missing_share": float(focal_enriched["prior_works_local"].isna().mean()) if len(focal_enriched) else np.nan,
            },
        ]
    )
    coverage.to_csv(derived_dir / "author_enrichment_coverage.csv", index=False)
    focal_works.to_csv(derived_dir / "focal_works_openalex_subset.csv", index=False)
    return focal_enriched, coverage, focal_works


def _build_adopter_profiles_package(
    adopters: pd.DataFrame,
    bundle_outputs: dict[str, Any],
    authorships: pd.DataFrame,
    sqlite_path: Path,
    out_dir: Path,
    derived_openalex_dir: Path,
) -> dict[str, Any]:
    ensure_dir(out_dir)
    bundle_df = bundle_outputs["bundle_df"].copy()
    summary_df = bundle_outputs["summary_df"].copy()

    focal_enriched, coverage_df, focal_works = _build_author_enrichment(
        adopters=adopters,
        authorships=authorships,
        sqlite_path=sqlite_path,
        derived_dir=derived_openalex_dir,
    )

    paper_base = bundle_df.merge(
        adopters[
            [
                "realizing_paper_id",
                "realizing_work_id",
                "realizing_paper_year",
                "realizing_paper_title",
                "realizing_paper_venue",
                "realizing_primary_subfield_display_name",
                "realizing_unique_funder_count",
                "realizing_first_funder",
            ]
        ].drop_duplicates(),
        on=[
            "realizing_paper_id",
            "realizing_work_id",
            "realizing_paper_year",
            "realizing_paper_title",
            "realizing_paper_venue",
            "realizing_primary_subfield_display_name",
        ],
        how="left",
    )
    if not focal_works.empty:
        paper_base = paper_base.merge(
            focal_works.rename(columns={"work_id": "realizing_work_id"}),
            on="realizing_work_id",
            how="left",
            suffixes=("", "_oa"),
        )
    paper_base["has_any_funder"] = (pd.to_numeric(paper_base["realizing_unique_funder_count"], errors="coerce").fillna(0) > 0).astype(int)
    paper_base["funder_count_bucket"] = pd.to_numeric(paper_base["realizing_unique_funder_count"], errors="coerce").fillna(0).astype(int).map(_funder_bucket)
    paper_base["venue_bucket"] = [
        _venue_bucket(v, b)
        for v, b in zip(paper_base["realizing_paper_venue"], paper_base.get("frontiergraph_bucket", pd.Series("", index=paper_base.index)))
    ]

    auth_agg = (
        focal_enriched.groupby("realizing_paper_id", as_index=False)
        .agg(
            team_size=("author_id", pd.Series.nunique),
            share_entrant_local=("entrant_local", "mean"),
            share_bridge_author_local=("bridge_author_local", "mean"),
            mean_career_age_local=("career_age_local", "mean"),
            max_career_age_local=("career_age_local", "max"),
            mean_prior_works_local=("prior_works_local", "mean"),
            max_prior_works_local=("prior_works_local", "max"),
            distinct_institutions=("institution_id", lambda s: pd.Series(s).replace("", np.nan).dropna().nunique()),
            distinct_countries=("country_code", lambda s: pd.Series(s).replace("", np.nan).dropna().nunique()),
        )
    )
    auth_agg["solo_vs_team"] = np.where(pd.to_numeric(auth_agg["team_size"], errors="coerce").fillna(0).astype(int) <= 1, "solo", "team")
    auth_agg["team_size_bucket"] = pd.cut(
        pd.to_numeric(auth_agg["team_size"], errors="coerce").fillna(0),
        bins=[-1, 1, 3, 6, 1000],
        labels=["solo", "2-3", "4-6", "7+"],
    ).astype(str)
    auth_agg["cross_country_team"] = (pd.to_numeric(auth_agg["distinct_countries"], errors="coerce").fillna(0) > 1).astype(int)
    paper_base = paper_base.merge(auth_agg, on="realizing_paper_id", how="left")

    subfield_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "realizing_primary_subfield_display_name"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
        .sort_values(["horizon", "candidate_family_mode", "n_papers"], ascending=[True, True, False])
    )
    top_subfields = (
        subfield_summary.groupby(["horizon", "candidate_family_mode"], as_index=False)
        .head(5)
        .reset_index(drop=True)
    )

    venue_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "venue_bucket"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
        .sort_values(["horizon", "candidate_family_mode", "venue_bucket"])
    )
    team_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "team_size_bucket"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
        .sort_values(["horizon", "candidate_family_mode", "team_size_bucket"])
    )
    funder_summary = (
        paper_base.groupby(["horizon", "candidate_family_mode", "funder_count_bucket"], as_index=False)
        .agg(n_papers=("realizing_paper_id", "nunique"))
        .sort_values(["horizon", "candidate_family_mode", "funder_count_bucket"])
    )
    bundle_split_summary = (
        paper_base.assign(bundle_type=np.where(pd.to_numeric(paper_base["predicted_edge_count"], errors="coerce").fillna(0) > 1, "multi_edge", "single_edge"))
        .groupby(["horizon", "candidate_family_mode", "bundle_type"], as_index=False)
        .agg(
            n_papers=("realizing_paper_id", "nunique"),
            mean_team_size=("team_size", "mean"),
            share_any_funder=("has_any_funder", "mean"),
            share_cross_country=("cross_country_team", "mean"),
        )
    )

    paper_base.to_parquet(out_dir / "adopter_profile_paper_level.parquet", index=False)
    paper_base.to_csv(out_dir / "adopter_profile_paper_level.csv", index=False)
    venue_summary.to_csv(out_dir / "adopter_profile_venue_summary.csv", index=False)
    team_summary.to_csv(out_dir / "adopter_profile_team_summary.csv", index=False)
    funder_summary.to_csv(out_dir / "adopter_profile_funder_summary.csv", index=False)
    top_subfields.to_csv(out_dir / "adopter_profile_top_subfields.csv", index=False)
    bundle_split_summary.to_csv(out_dir / "adopter_profile_bundle_split_summary.csv", index=False)
    coverage_df.to_csv(out_dir / "adopter_profile_enrichment_coverage.csv", index=False)

    overview = (
        paper_base.groupby(["horizon", "candidate_family_mode"], as_index=False)
        .agg(
            n_papers=("realizing_paper_id", "nunique"),
            mean_team_size=("team_size", "mean"),
            share_any_funder=("has_any_funder", "mean"),
            share_cross_country=("cross_country_team", "mean"),
            mean_career_age_local=("mean_career_age_local", "mean"),
            share_mixed_family=("family_mix", lambda s: float((pd.Series(s) == "mixed_family").mean())),
        )
    )
    _write_tex_table(overview.round(3), out_dir / "adopter_profile_overview.tex", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharey=True)
    for ax, horizon in zip(axes, HORIZON_ORDER):
        sub = venue_summary[venue_summary["horizon"] == horizon]
        pivot = sub.pivot(index="venue_bucket", columns="candidate_family_mode", values="n_papers").fillna(0)
        pivot = pivot.reindex(["general_interest", "field", "adjacent_interdisciplinary", "other"]).fillna(0)
        x = np.arange(len(pivot))
        width = 0.38
        ax.bar(x - width / 2, pivot.get("path_to_direct", pd.Series(0, index=pivot.index)).values, width=width, label="Path-to-direct", color="#1d4ed8")
        ax.bar(x + width / 2, pivot.get("direct_to_path", pd.Series(0, index=pivot.index)).values, width=width, label="Direct-to-path", color="#b45309")
        ax.set_xticks(x)
        ax.set_xticklabels(["GI", "Field", "Adj.", "Other"], rotation=0)
        ax.set_title(f"h={horizon}")
    axes[0].set_ylabel("Realizing papers")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Adopter profiles: venue bucket by family", y=1.02)
    fig.tight_layout()
    fig.savefig(out_dir / "adopter_profile_venue.png", dpi=200, bbox_inches="tight")
    fig.savefig(out_dir / "adopter_profile_venue.pdf", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharey=True)
    for ax, horizon in zip(axes, HORIZON_ORDER):
        sub = team_summary[team_summary["horizon"] == horizon]
        pivot = sub.pivot(index="team_size_bucket", columns="candidate_family_mode", values="n_papers").fillna(0)
        pivot = pivot.reindex(["solo", "2-3", "4-6", "7+"]).fillna(0)
        x = np.arange(len(pivot))
        width = 0.38
        ax.bar(x - width / 2, pivot.get("path_to_direct", pd.Series(0, index=pivot.index)).values, width=width, color="#1d4ed8")
        ax.bar(x + width / 2, pivot.get("direct_to_path", pd.Series(0, index=pivot.index)).values, width=width, color="#b45309")
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index.tolist())
        ax.set_title(f"h={horizon}")
    axes[0].set_ylabel("Realizing papers")
    fig.suptitle("Adopter profiles: team size by family", y=1.02)
    fig.tight_layout()
    fig.savefig(out_dir / "adopter_profile_team_size.png", dpi=200, bbox_inches="tight")
    fig.savefig(out_dir / "adopter_profile_team_size.pdf", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharey=True)
    for ax, horizon in zip(axes, HORIZON_ORDER):
        sub = funder_summary[funder_summary["horizon"] == horizon]
        pivot = sub.pivot(index="funder_count_bucket", columns="candidate_family_mode", values="n_papers").fillna(0)
        pivot = pivot.reindex(["none", "one", "two_plus"]).fillna(0)
        x = np.arange(len(pivot))
        width = 0.38
        ax.bar(x - width / 2, pivot.get("path_to_direct", pd.Series(0, index=pivot.index)).values, width=width, color="#1d4ed8")
        ax.bar(x + width / 2, pivot.get("direct_to_path", pd.Series(0, index=pivot.index)).values, width=width, color="#b45309")
        ax.set_xticks(x)
        ax.set_xticklabels(["None", "One", "2+"])
        ax.set_title(f"h={horizon}")
    axes[0].set_ylabel("Realizing papers")
    fig.suptitle("Adopter profiles: funder presence by family", y=1.02)
    fig.tight_layout()
    fig.savefig(out_dir / "adopter_profile_funders.png", dpi=200, bbox_inches="tight")
    fig.savefig(out_dir / "adopter_profile_funders.pdf", bbox_inches="tight")
    plt.close(fig)

    top_subfields = top_subfields.copy()
    top_subfields["rank"] = top_subfields.groupby(["horizon", "candidate_family_mode"]).cumcount() + 1
    note_lines = [
        "# Adopter profiles note",
        "",
        "This package describes the papers and teams that independently move toward graph-supported questions.",
        "",
    ]
    for horizon in HORIZON_ORDER:
        block = overview[overview["horizon"] == horizon]
        if block.empty:
            continue
        note_lines.append(f"## h={horizon}")
        for row in block.itertuples(index=False):
            note_lines.append(
                f"- {FAMILY_LABELS.get(str(row.candidate_family_mode), str(row.candidate_family_mode))}: mean team size {float(row.mean_team_size):.2f}, share with any funder {float(row.share_any_funder):.3f}, share cross-country {float(row.share_cross_country):.3f}."
            )
        note_lines.append("")
    note_lines.append("## Coverage")
    for row in coverage_df.itertuples(index=False):
        note_lines.append(f"- {row.field}: missing share {float(row.missing_share):.3f}")
    (out_dir / "adopter_profile_note.md").write_text("\n".join(note_lines) + "\n", encoding="utf-8")

    return {
        "paper_base": paper_base,
        "overview": overview,
        "coverage_df": coverage_df,
        "summary_df": summary_df,
    }


def _write_manifest(out_dir: Path, payload: dict[str, Any]) -> None:
    (out_dir / "manifest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _load_existing_bundle_outputs(out_dir: Path) -> dict[str, Any]:
    return {
        "bundle_df": pd.read_parquet(out_dir / "bundle_uptake_paper_level.parquet"),
        "pairwise_df": pd.read_parquet(out_dir / "bundle_uptake_pairwise.parquet"),
        "summary_df": pd.read_csv(out_dir / "bundle_uptake_summary.csv"),
        "mix_df": pd.read_csv(out_dir / "bundle_uptake_family_mix.csv"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build exploratory bundle-uptake and adopter-profile testbeds.")
    parser.add_argument("--path-panel", default=str(DEFAULT_PATH_PANEL))
    parser.add_argument("--direct-panel", default=str(DEFAULT_DIRECT_PANEL))
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--paper-meta", default=str(DEFAULT_PAPER_META))
    parser.add_argument("--authorships", default=str(DEFAULT_AUTHORSHIPS))
    parser.add_argument("--openalex-sqlite", default=str(DEFAULT_OPENALEX_SQLITE))
    parser.add_argument("--derived-openalex-dir", default=str(DEFAULT_DERIVED_OPENALEX_DIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out)
    ensure_dir(out_dir)
    uptake_dir = out_dir / "uptake_spine"
    bundle_dir = out_dir / "bundle_uptake"
    adopter_dir = out_dir / "adopter_profiles"
    ensure_dir(uptake_dir)
    ensure_dir(bundle_dir)
    ensure_dir(adopter_dir)

    uptake_spine_parquet = uptake_dir / "historical_edge_uptake_spine.parquet"
    uptake_deduped_parquet = uptake_dir / "historical_edge_uptake_deduped.parquet"
    family_manifest_csv = uptake_dir / "family_manifest.csv"
    if uptake_spine_parquet.exists() and uptake_deduped_parquet.exists() and family_manifest_csv.exists():
        print("[testbeds] reusing existing uptake spine package", flush=True)
        spine_df = pd.read_parquet(uptake_spine_parquet)
        deduped = pd.read_parquet(uptake_deduped_parquet)
        family_manifest = pd.read_csv(family_manifest_csv)
    else:
        print("[testbeds] building uptake spine", flush=True)
        spine_df, family_manifest = _build_uptake_spine(args)
        deduped = _dedupe_for_paper_level(spine_df)
        spine_df.to_parquet(uptake_dir / "historical_edge_uptake_spine.parquet", index=False)
        spine_df.to_csv(uptake_dir / "historical_edge_uptake_spine.csv", index=False)
        deduped.to_parquet(uptake_dir / "historical_edge_uptake_deduped.parquet", index=False)
        deduped.to_csv(uptake_dir / "historical_edge_uptake_deduped.csv", index=False)
        family_manifest.to_csv(uptake_dir / "family_manifest.csv", index=False)

        validation = (
            spine_df.groupby(["candidate_family_mode", "horizon"], as_index=False)
            .agg(
                n_uptake_rows=("candidate_id", "size"),
                n_unique_predictions=("prediction_key", "nunique"),
                n_realizing_papers=("realizing_paper_id", "nunique"),
                non_first_realizer_share=("is_first_realization_event", lambda s: 1.0 - float(pd.to_numeric(s).mean())),
            )
            .sort_values(["candidate_family_mode", "horizon"])
        )
        validation.to_csv(uptake_dir / "uptake_validation_summary.csv", index=False)
        sample = spine_df[
            [
                "candidate_family_mode",
                "candidate_id",
                "cutoff_year_t",
                "horizon",
                "source_label",
                "target_label",
                "first_realized_year",
                "realizing_paper_id",
                "realizing_paper_year",
                "realizing_paper_title",
            ]
        ].head(20)
        sample.to_csv(uptake_dir / "uptake_validation_sample.csv", index=False)
        _write_manifest(
            uptake_dir,
            {
                "path_panel": str(Path(args.path_panel)),
                "direct_panel": str(Path(args.direct_panel)),
                "corpus": str(Path(args.corpus)),
                "paper_meta": str(Path(args.paper_meta)),
                "n_spine_rows": int(len(spine_df)),
                "n_deduped_rows": int(len(deduped)),
                "family_summary": family_manifest.to_dict(orient="records"),
            },
        )

    _, _, corpus_df, _, authorships = _load_core_inputs(args)
    bundle_paper_parquet = bundle_dir / "bundle_uptake_paper_level.parquet"
    bundle_pairwise_parquet = bundle_dir / "bundle_uptake_pairwise.parquet"
    bundle_summary_csv = bundle_dir / "bundle_uptake_summary.csv"
    bundle_mix_csv = bundle_dir / "bundle_uptake_family_mix.csv"
    if bundle_paper_parquet.exists() and bundle_pairwise_parquet.exists() and bundle_summary_csv.exists() and bundle_mix_csv.exists():
        print("[testbeds] reusing existing bundle uptake package", flush=True)
        bundle_outputs = _load_existing_bundle_outputs(bundle_dir)
    else:
        print("[testbeds] building bundle uptake package", flush=True)
        bundle_outputs = _build_bundle_uptake_package(deduped, corpus_df, bundle_dir)

    print("[testbeds] building adopter profiles package", flush=True)
    adopter_outputs = _build_adopter_profiles_package(
        adopters=deduped,
        bundle_outputs=bundle_outputs,
        authorships=authorships,
        sqlite_path=Path(args.openalex_sqlite),
        out_dir=adopter_dir,
        derived_openalex_dir=Path(args.derived_openalex_dir),
    )
    _write_manifest(
        adopter_dir,
        {
            "openalex_sqlite": str(Path(args.openalex_sqlite)),
            "derived_openalex_dir": str(Path(args.derived_openalex_dir)),
            "n_papers": int(adopter_outputs["paper_base"]["realizing_paper_id"].nunique()) if not adopter_outputs["paper_base"].empty else 0,
            "coverage_fields": adopter_outputs["coverage_df"].to_dict(orient="records"),
        },
    )
    print("[testbeds] complete", flush=True)


if __name__ == "__main__":
    main()
