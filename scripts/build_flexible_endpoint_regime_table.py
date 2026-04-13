from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parents[1]

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "per",
    "the",
    "to",
    "with",
}

MEASUREMENT_TOKENS = {
    "actual",
    "average",
    "determinants",
    "estimate",
    "estimates",
    "estimated",
    "factors",
    "heterogeneity",
    "hypothetical",
    "iterative",
    "marginal",
    "mean",
    "median",
    "measure",
    "measures",
    "question",
    "questions",
    "response",
    "responses",
    "stated",
    "survey",
    "surveys",
    "value",
    "values",
    "valuation",
    "valuations",
    "wtp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a broad flexible-endpoint regime study on the canonicalized+tuned v2.1 stack.")
    parser.add_argument(
        "--mapping",
        default="data/ontology_v2/extraction_label_mapping_v2_1_canonicalized.parquet",
    )
    parser.add_argument(
        "--frontier",
        default="outputs/paper/61_current_reranked_frontier_v2_1_canonicalized_search_tuned/current_reranked_frontier.parquet",
    )
    parser.add_argument(
        "--baseline-frontier",
        default="outputs/paper/53_current_reranked_frontier_v2_1/current_reranked_frontier.parquet",
    )
    parser.add_argument(
        "--canonicalization",
        default="data/ontology_v2/cross_source_canonicalization_applied_v2_1.csv",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/62_flexible_endpoint_regime_study",
    )
    parser.add_argument(
        "--note",
        default="next_steps/flexible_endpoint_regime_study.md",
    )
    return parser.parse_args()


def normalize_label(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def tokenize(text: str) -> list[str]:
    return normalize_label(text).split()


def build_modifier_phrase(label: str, target_label: str) -> str:
    norm_label = normalize_label(label)
    norm_target = normalize_label(target_label)
    if not norm_label:
        return ""
    if norm_target and norm_target in norm_label:
        norm_label = norm_label.replace(norm_target, " ")
    target_tokens = set(tokenize(target_label))
    tokens = [
        tok
        for tok in tokenize(norm_label)
        if len(tok) > 1
        and tok not in STOPWORDS
        and tok not in target_tokens
        and tok not in MEASUREMENT_TOKENS
    ]
    return " ".join(tokens)


def connected_components_from_similarity(sim: np.ndarray, threshold: float) -> list[list[int]]:
    n = sim.shape[0]
    adjacency: dict[int, set[int]] = defaultdict(set)
    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] >= threshold:
                adjacency[i].add(j)
                adjacency[j].add(i)

    visited: set[int] = set()
    components: list[list[int]] = []
    for i in range(n):
        if i in visited:
            continue
        stack = [i]
        visited.add(i)
        comp: list[int] = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in adjacency.get(cur, set()):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        components.append(sorted(comp))
    return components


def top_counts(df: pd.DataFrame, label_col: str, rank_col: str, top_k: int) -> pd.DataFrame:
    top = df.sort_values(rank_col).head(top_k).copy()
    counts = top[label_col].astype(str).map(normalize_label).value_counts().rename_axis("norm_label").reset_index(name=f"top{top_k}_count")
    return counts


def build_broad_endpoint_features(mapping: pd.DataFrame, frontier: pd.DataFrame, baseline_frontier: pd.DataFrame) -> pd.DataFrame:
    mapping_agg = (
        mapping.groupby(["onto_id", "onto_label"], as_index=False)
        .agg(
            mapped_rows=("label", "size"),
            mapped_total_freq=("freq", "sum"),
            mapped_distinct_labels=("label", pd.Series.nunique),
        )
        .rename(columns={"onto_id": "target_id", "onto_label": "target_label"})
    )

    frontier_counts = (
        frontier.groupby(["v", "v_label"], as_index=False)
        .agg(
            tuned_top20_count=("surface_rank", lambda s: int((s <= 20).sum())),
            tuned_top100_count=("surface_rank", lambda s: int((s <= 100).sum())),
            sink_score=("sink_score", "max"),
            sink_score_pct=("sink_score_pct", "max"),
        )
        .rename(columns={"v": "target_id", "v_label": "target_label"})
    )

    baseline_counts = (
        baseline_frontier.groupby(["v", "v_label"], as_index=False)
        .agg(
            baseline_top20_count=("reranker_rank", lambda s: int((s <= 20).sum())),
            baseline_top100_count=("reranker_rank", lambda s: int((s <= 100).sum())),
        )
    )
    baseline_counts["norm_label"] = baseline_counts["v_label"].map(normalize_label)
    baseline_counts = baseline_counts.groupby("norm_label", as_index=False).agg(
        baseline_top20_count=("baseline_top20_count", "sum"),
        baseline_top100_count=("baseline_top100_count", "sum"),
    )

    mapping_agg["norm_label"] = mapping_agg["target_label"].map(normalize_label)
    frontier_counts["norm_label"] = frontier_counts["target_label"].map(normalize_label)

    out = mapping_agg.merge(
        frontier_counts.drop(columns=["target_label"]),
        on=["target_id", "norm_label"],
        how="left",
    ).merge(
        baseline_counts,
        on="norm_label",
        how="left",
    )
    for col in [
        "tuned_top20_count",
        "tuned_top100_count",
        "baseline_top20_count",
        "baseline_top100_count",
    ]:
        out[col] = out[col].fillna(0).astype(int)
    for col in ["sink_score", "sink_score_pct"]:
        out[col] = out[col].fillna(0.0).astype(float)
    return out


def build_canonicalization_summary(canonicalization: pd.DataFrame) -> pd.DataFrame:
    out = (
        canonicalization.assign(norm_label=canonicalization["canonical_label"].map(normalize_label))
        .groupby(["canonical_id", "canonical_label", "norm_label"], as_index=False)
        .agg(
            canonical_member_count=("member_id", "size"),
            canonical_member_sources=("member_source", lambda s: json.dumps(sorted(set(map(str, s))), ensure_ascii=False)),
            canonical_member_labels=("member_label", lambda s: json.dumps(sorted(set(map(str, s)))[:10], ensure_ascii=False)),
        )
        .rename(columns={"canonical_id": "target_id", "canonical_label": "target_label"})
    )
    return out


def broad_flexibility_screen(mapping: pd.DataFrame, endpoint_features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    candidates = endpoint_features[endpoint_features["mapped_total_freq"] >= 300].copy()
    for target in candidates.itertuples(index=False):
        sub = mapping[mapping["onto_id"] == target.target_id].copy()
        if sub.empty:
            continue
        total_freq = int(sub["freq"].sum())
        modifier_counter: Counter[str] = Counter()
        phrase_counter: Counter[str] = Counter()
        modifier_label_rows = 0
        direct_phrase_freq = 0
        measurement_only_freq = 0
        topic_modifier_freq = 0
        for row in sub.itertuples(index=False):
            label = str(row.label)
            freq = int(row.freq)
            norm_label = normalize_label(label)
            norm_target = normalize_label(str(target.target_label))
            if norm_target and norm_target in norm_label:
                direct_phrase_freq += freq
            phrase = build_modifier_phrase(label, str(target.target_label))
            if phrase:
                modifier_label_rows += 1
                topic_modifier_freq += freq
                phrase_counter[phrase] += freq
                for token in phrase.split():
                    modifier_counter[token] += freq
            else:
                remainder_tokens = [
                    tok
                    for tok in tokenize(norm_label.replace(norm_target, " "))
                    if len(tok) > 1 and tok not in STOPWORDS
                ]
                if remainder_tokens:
                    measurement_only_freq += freq
        if phrase_counter:
            probs = np.array([v / max(sum(phrase_counter.values()), 1) for v in phrase_counter.values()], dtype=float)
            phrase_entropy = float(-(probs * np.log2(probs)).sum()) if len(probs) else 0.0
        else:
            phrase_entropy = 0.0
        rows.append(
            {
                "target_id": target.target_id,
                "target_label": target.target_label,
                "norm_label": target.norm_label,
                "mapped_rows": int(target.mapped_rows),
                "mapped_total_freq": total_freq,
                "mapped_distinct_labels": int(target.mapped_distinct_labels),
                "baseline_top20_count": int(target.baseline_top20_count),
                "baseline_top100_count": int(target.baseline_top100_count),
                "tuned_top20_count": int(target.tuned_top20_count),
                "tuned_top100_count": int(target.tuned_top100_count),
                "sink_score": float(target.sink_score),
                "sink_score_pct": float(target.sink_score_pct),
                "modifier_phrase_rows": int(modifier_label_rows),
                "modifier_phrase_unique": int(len(phrase_counter)),
                "modifier_total_freq": int(sum(phrase_counter.values())),
                "modifier_phrase_entropy": float(phrase_entropy),
                "direct_phrase_freq": int(direct_phrase_freq),
                "direct_phrase_share": float(direct_phrase_freq / max(total_freq, 1)),
                "measurement_only_freq": int(measurement_only_freq),
                "measurement_only_share": float(measurement_only_freq / max(total_freq, 1)),
                "topic_modifier_freq": int(topic_modifier_freq),
                "topic_modifier_share": float(topic_modifier_freq / max(total_freq, 1)),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["study_universe_flag"] = (
        (out["sink_score_pct"] >= 0.90)
        | (out["tuned_top100_count"] > 0)
        | (
            (out["mapped_total_freq"] >= 500)
            & (out["modifier_phrase_rows"] >= 150)
            & (out["modifier_phrase_entropy"] >= 4.0)
        )
    )
    return out.sort_values(
        ["study_universe_flag", "sink_score_pct", "tuned_top100_count", "mapped_total_freq"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


def detailed_semantic_split_study(mapping: pd.DataFrame, broad_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    study_targets = broad_df[broad_df["study_universe_flag"]].copy()
    endpoint_rows: list[dict] = []
    cluster_rows: list[dict] = []

    for target in study_targets.itertuples(index=False):
        sub = mapping[mapping["onto_id"] == target.target_id].copy()
        phrases: list[str] = []
        freqs: list[int] = []
        raw_labels: list[str] = []
        for row in sub.itertuples(index=False):
            phrase = build_modifier_phrase(str(row.label), str(target.target_label))
            if not phrase:
                continue
            phrases.append(phrase)
            freqs.append(int(row.freq))
            raw_labels.append(str(row.label))
        if len(phrases) < 10:
            endpoint_rows.append(
                {
                    "target_id": target.target_id,
                    "target_label": target.target_label,
                    "norm_label": target.norm_label,
                    "semantic_cluster_count": 0,
                    "significant_cluster_count": 0,
                    "semantic_cluster_entropy": 0.0,
                    "dominant_cluster_share": 1.0,
                    "second_cluster_share": 0.0,
                    "recommended_split_semantic": False,
                    "top_semantic_clusters": "[]",
                }
            )
            continue

        phrase_df = pd.DataFrame({"modifier_phrase": phrases, "freq": freqs, "raw_label": raw_labels})
        phrase_df = (
            phrase_df.groupby("modifier_phrase", as_index=False)
            .agg(
                total_freq=("freq", "sum"),
                example_labels=("raw_label", lambda s: json.dumps(list(pd.Series(s).head(5)), ensure_ascii=False)),
            )
            .sort_values(["total_freq", "modifier_phrase"], ascending=[False, True])
            .reset_index(drop=True)
        )
        phrase_df = phrase_df[phrase_df["modifier_phrase"].str.len() > 0].copy()
        if len(phrase_df) < 4:
            endpoint_rows.append(
                {
                    "target_id": target.target_id,
                    "target_label": target.target_label,
                    "norm_label": target.norm_label,
                    "semantic_cluster_count": int(len(phrase_df)),
                    "significant_cluster_count": 0,
                    "semantic_cluster_entropy": 0.0,
                    "dominant_cluster_share": 1.0,
                    "second_cluster_share": 0.0,
                    "recommended_split_semantic": False,
                    "top_semantic_clusters": "[]",
                }
            )
            continue

        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        X = vectorizer.fit_transform(phrase_df["modifier_phrase"].tolist())
        sim = cosine_similarity(X)
        components = connected_components_from_similarity(sim, threshold=0.35)

        cluster_summaries: list[dict] = []
        total_freq = float(phrase_df["total_freq"].sum())
        for comp_id, comp in enumerate(sorted(components, key=lambda c: -float(phrase_df.iloc[c]["total_freq"].sum()))):
            cluster = phrase_df.iloc[comp].copy()
            cluster_freq = int(cluster["total_freq"].sum())
            cluster_share = float(cluster_freq / total_freq) if total_freq else 0.0
            exemplar = cluster.sort_values(["total_freq", "modifier_phrase"], ascending=[False, True]).iloc[0]
            top_phrases = cluster.sort_values(["total_freq", "modifier_phrase"], ascending=[False, True])[
                "modifier_phrase"
            ].head(5).tolist()
            cluster_rows.append(
                {
                    "target_id": target.target_id,
                    "target_label": target.target_label,
                    "norm_label": target.norm_label,
                    "cluster_id": comp_id,
                    "cluster_freq": cluster_freq,
                    "cluster_share": cluster_share,
                    "cluster_size": int(len(cluster)),
                    "cluster_exemplar": exemplar["modifier_phrase"],
                    "top_modifier_phrases": json.dumps(top_phrases, ensure_ascii=False),
                    "top_example_labels": exemplar["example_labels"],
                }
            )
            cluster_summaries.append(
                {
                    "cluster_id": comp_id,
                    "cluster_freq": cluster_freq,
                    "cluster_share": cluster_share,
                    "cluster_size": int(len(cluster)),
                    "cluster_exemplar": exemplar["modifier_phrase"],
                    "top_modifier_phrases": top_phrases,
                }
            )

        cluster_summaries = sorted(cluster_summaries, key=lambda x: (-x["cluster_freq"], x["cluster_exemplar"]))
        significant_clusters = [c for c in cluster_summaries if c["cluster_freq"] >= 50 and c["cluster_share"] >= 0.08]
        cluster_probs = np.array([c["cluster_freq"] / total_freq for c in cluster_summaries], dtype=float)
        cluster_entropy = float(-(cluster_probs * np.log2(cluster_probs)).sum()) if len(cluster_probs) else 0.0
        dominant_cluster_share = float(cluster_summaries[0]["cluster_share"]) if cluster_summaries else 1.0
        second_cluster_share = float(cluster_summaries[1]["cluster_share"]) if len(cluster_summaries) > 1 else 0.0
        endpoint_rows.append(
            {
                "target_id": target.target_id,
                "target_label": target.target_label,
                "norm_label": target.norm_label,
                "semantic_cluster_count": int(len(cluster_summaries)),
                "significant_cluster_count": int(len(significant_clusters)),
                "semantic_cluster_entropy": cluster_entropy,
                "dominant_cluster_share": dominant_cluster_share,
                "second_cluster_share": second_cluster_share,
                "recommended_split_semantic": bool(
                    len(significant_clusters) >= 2 and cluster_entropy >= 1.2 and dominant_cluster_share <= 0.75
                ),
                "top_semantic_clusters": json.dumps(cluster_summaries[:6], ensure_ascii=False),
            }
        )

    endpoint_df = pd.DataFrame(endpoint_rows)
    cluster_df = pd.DataFrame(cluster_rows)
    return endpoint_df, cluster_df


def assign_regime(row: pd.Series) -> str:
    split_candidate = bool(row.get("recommended_split_semantic", False))
    canonical_members = int(row.get("canonical_member_count", 0) or 0)
    tuned_top100 = int(row.get("tuned_top100_count", 0) or 0)
    tuned_top20 = int(row.get("tuned_top20_count", 0) or 0)
    if split_candidate:
        return "study_subfamily_candidate"
    if canonical_members > 0 and (tuned_top100 >= 3 or tuned_top20 >= 1):
        return "canonicalize_and_regularize"
    if canonical_members > 0:
        return "canonicalize_only"
    if tuned_top100 >= 3 or tuned_top20 >= 1:
        return "regularize_only"
    return "monitor"


def regime_reason(row: pd.Series) -> str:
    if row["suggested_regime"] == "study_subfamily_candidate":
        return "multiple significant modifier clusters survive after canonicalization"
    if row["suggested_regime"] == "canonicalize_and_regularize":
        return "duplicate identity plus persistent target-side concentration"
    if row["suggested_regime"] == "canonicalize_only":
        return "duplicate identity without persistent frontier concentration"
    if row["suggested_regime"] == "regularize_only":
        return "broad valid endpoint remains concentration-prone after tuning"
    return "broad endpoint does not currently justify stronger intervention"


def main() -> None:
    args = parse_args()
    mapping = pd.read_parquet(args.mapping)
    frontier = pd.read_parquet(args.frontier)
    baseline_frontier = pd.read_parquet(args.baseline_frontier)
    canonicalization = pd.read_csv(args.canonicalization)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    note_path = Path(args.note)
    note_path.parent.mkdir(parents=True, exist_ok=True)

    broad_features = build_broad_endpoint_features(mapping, frontier, baseline_frontier)
    broad_screen = broad_flexibility_screen(mapping, broad_features)
    semantic_endpoints, semantic_clusters = detailed_semantic_split_study(mapping, broad_screen)
    canonical_summary = build_canonicalization_summary(canonicalization)

    regime_table = (
        broad_screen.merge(
            canonical_summary.drop(columns=["target_label"]),
            on=["target_id", "norm_label"],
            how="left",
        ).merge(
            semantic_endpoints.drop(columns=["target_label"]),
            on=["target_id", "norm_label"],
            how="left",
        )
    )
    for col in ["canonical_member_count", "semantic_cluster_count", "significant_cluster_count"]:
        regime_table[col] = regime_table[col].fillna(0).astype(int)
    for col in ["semantic_cluster_entropy", "dominant_cluster_share", "second_cluster_share"]:
        regime_table[col] = regime_table[col].fillna(0.0).astype(float)
    regime_table["recommended_split_semantic"] = regime_table["recommended_split_semantic"].fillna(False).astype(bool)
    regime_table["suggested_regime"] = regime_table.apply(assign_regime, axis=1)
    regime_table["regime_reason"] = regime_table.apply(regime_reason, axis=1)
    regime_table = regime_table.sort_values(
        ["study_universe_flag", "suggested_regime", "sink_score_pct", "tuned_top100_count", "mapped_total_freq"],
        ascending=[False, True, False, False, False],
    ).reset_index(drop=True)

    broad_screen.to_csv(out_dir / "broad_endpoint_screen.csv", index=False)
    regime_table.to_csv(out_dir / "flexible_endpoint_regime_table.csv", index=False)
    semantic_endpoints.to_csv(out_dir / "flexible_endpoint_semantic_summary.csv", index=False)
    semantic_clusters.to_csv(out_dir / "flexible_endpoint_semantic_clusters.csv", index=False)

    study = regime_table[regime_table["study_universe_flag"]].copy()
    regime_counts = study["suggested_regime"].value_counts().to_dict()
    lines = [
        "# Flexible Endpoint Regime Study",
        "",
        "This study is intended to learn reusable endpoint regimes rather than hand-patch individual ontology nodes.",
        "",
        "## Coverage",
        "",
        f"- broad screen endpoints (`mapped_total_freq >= 300`): `{len(broad_screen):,}`",
        f"- study-universe endpoints: `{int(study['study_universe_flag'].sum()):,}`",
        "",
        "## Regime counts within study universe",
        "",
    ]
    for regime, count in regime_counts.items():
        lines.append(f"- `{regime}`: `{int(count):,}`")
    lines.extend(["", "## Representative examples", ""])
    for regime in [
        "canonicalize_and_regularize",
        "canonicalize_only",
        "regularize_only",
        "study_subfamily_candidate",
        "monitor",
    ]:
        sub = study[study["suggested_regime"] == regime].head(8)
        if sub.empty:
            continue
        lines.append(f"### {regime}")
        for row in sub.itertuples(index=False):
            lines.append(
                f"- `{row.target_label}` | sink_pct={float(row.sink_score_pct):.3f}, tuned_top100={int(row.tuned_top100_count)}, canonical_members={int(row.canonical_member_count)}, significant_clusters={int(row.significant_cluster_count)}, dominant_cluster_share={float(row.dominant_cluster_share):.3f}"
            )
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "- `canonicalize_and_regularize` captures duplicate-identity endpoints that remain flexible sinks after tuning.",
            "- `regularize_only` captures broad valid endpoints that are concentration-prone but not clearly multi-family.",
            "- `study_subfamily_candidate` is a learning label, not an automatic promotion instruction.",
            "- endpoints stay in `monitor` when they are broad but do not yet show a structural reason for stronger intervention.",
            "",
            "## Caution",
            "",
            "This table is intended to guide generalized ontology policy, not to justify endpoint-specific patches.",
            "Any later promotion of child families should require a separate rule-based review over the `study_subfamily_candidate` regime.",
        ]
    )
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote broad screen: {out_dir / 'broad_endpoint_screen.csv'}")
    print(f"Wrote regime table: {out_dir / 'flexible_endpoint_regime_table.csv'}")
    print(f"Wrote semantic summary: {out_dir / 'flexible_endpoint_semantic_summary.csv'}")
    print(f"Wrote semantic clusters: {out_dir / 'flexible_endpoint_semantic_clusters.csv'}")
    print(f"Wrote note: {note_path}")


if __name__ == "__main__":
    main()
