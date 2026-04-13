from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_DIR = ROOT / "data" / "ontology_v2"
OUTPUT_DIR = ROOT / "outputs" / "paper" / "54_v2_1_sink_diagnostic"

ONTOLOGY_V2_PATH = ONTOLOGY_DIR / "ontology_v2_final.json"
ONTOLOGY_V2_1_PATH = ONTOLOGY_DIR / "ontology_v2_1.json"
ONTOLOGY_EMB_PATH = ONTOLOGY_DIR / "ontology_v2_label_only_embeddings.npy"
MAPPING_V2_1_PATH = ONTOLOGY_DIR / "extraction_label_mapping_v2_1.parquet"
FRONTIER_PATH = ROOT / "outputs" / "paper" / "53_current_reranked_frontier_v2_1" / "current_reranked_frontier.parquet"

CANONICAL_TABLE_PATH = ONTOLOGY_DIR / "cross_source_canonicalization_candidates_v2_1.parquet"
CANONICAL_NOTE_PATH = ONTOLOGY_DIR / "cross_source_canonicalization_candidates_v2_1.md"
APPLIED_CANONICAL_TABLE_PATH = ONTOLOGY_DIR / "cross_source_canonicalization_applied_v2_1.csv"
APPLIED_CANONICAL_NOTE_PATH = ONTOLOGY_DIR / "cross_source_canonicalization_applied_v2_1.md"
SINK_TABLE_PATH = OUTPUT_DIR / "sink_targets.csv"
SINK_NOTE_PATH = OUTPUT_DIR / "summary.md"
ADJUSTED_FRONTIER_PATH = OUTPUT_DIR / "frontier_with_sink_penalty.parquet"
ADJUSTED_SUMMARY_PATH = OUTPUT_DIR / "frontier_with_sink_penalty_summary.csv"
DIVERSIFIED_FRONTIER_PATH = OUTPUT_DIR / "frontier_with_mild_sink_penalty_and_diversification.parquet"
DIVERSIFIED_SUMMARY_PATH = OUTPUT_DIR / "frontier_with_mild_sink_penalty_and_diversification_summary.csv"
SUBFAMILY_PATH = OUTPUT_DIR / "high_support_flexible_endpoint_subfamilies.csv"
SEMANTIC_SUBFAMILY_PATH = OUTPUT_DIR / "high_support_flexible_endpoint_subfamilies_semantic.csv"
SEMANTIC_SUBFAMILY_CLUSTER_PATH = OUTPUT_DIR / "high_support_flexible_endpoint_subfamilies_semantic_clusters.csv"

SOURCE_PRIORITY = {
    "jel": 0,
    "openalex_topic": 1,
    "openalex_keyword": 2,
    "wikidata": 3,
    "wikipedia": 4,
    "frontiergraph_v2_1_reviewed_family": 5,
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
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

TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_label(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(normalize_label(text))


def source_rank(source: str) -> int:
    return SOURCE_PRIORITY.get(str(source), 99)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def load_base_concepts() -> list[dict]:
    return json.load(open(ONTOLOGY_V2_PATH, encoding="utf-8"))


def load_v2_1_concepts() -> list[dict]:
    return json.load(open(ONTOLOGY_V2_1_PATH, encoding="utf-8"))


def build_cross_source_canonicalization() -> pd.DataFrame:
    concepts = load_base_concepts()
    embs = np.load(ONTOLOGY_EMB_PATH, mmap_mode="r")
    assert len(concepts) == embs.shape[0]

    groups: dict[str, list[int]] = defaultdict(list)
    for i, concept in enumerate(concepts):
        groups[normalize_label(concept.get("label", ""))].append(i)

    rows: list[dict] = []
    cluster_id = 0
    for norm_label, indices in groups.items():
        if len(indices) < 2:
            continue
        sources = {concepts[i].get("source") for i in indices}
        if len(sources) < 2:
            continue
        cluster_id += 1
        members = [concepts[i] for i in indices]
        canonical = sorted(
            members,
            key=lambda c: (
                source_rank(c.get("source")),
                len(str(c.get("label", ""))),
                str(c.get("id", "")),
            ),
        )[0]
        canonical_idx = next(i for i in indices if concepts[i]["id"] == canonical["id"])
        canonical_vec = np.asarray(embs[canonical_idx], dtype=np.float32)
        for i in indices:
            concept = concepts[i]
            if concept["id"] == canonical["id"]:
                continue
            rows.append(
                {
                    "cluster_id": cluster_id,
                    "norm_label": norm_label,
                    "canonical_id": canonical["id"],
                    "canonical_label": canonical.get("label"),
                    "canonical_source": canonical.get("source"),
                    "member_id": concept["id"],
                    "member_label": concept.get("label"),
                    "member_source": concept.get("source"),
                    "cosine_to_canonical": cosine(canonical_vec, np.asarray(embs[i], dtype=np.float32)),
                }
            )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(
        ["norm_label", "canonical_source", "member_source", "member_label"],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)
    return df


def build_applied_canonicalization(canonical_df: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    if canonical_df.empty:
        return canonical_df.copy()

    support = (
        mapping.groupby(["onto_id", "onto_label"], as_index=False)
        .agg(
            mapped_rows=("label", "size"),
            mapped_total_freq=("freq", "sum"),
            mapped_distinct_labels=("label", pd.Series.nunique),
        )
        .rename(columns={"onto_id": "concept_id", "onto_label": "concept_label"})
    )

    df = canonical_df.copy()
    df["label_token_count"] = df["norm_label"].str.split().str.len()
    df["alphabetic_label"] = df["norm_label"].str.contains(r"[a-z]", regex=True)
    df = df.merge(
        support.add_prefix("canonical_"),
        left_on="canonical_id",
        right_on="canonical_concept_id",
        how="left",
    )
    df = df.merge(
        support.add_prefix("member_"),
        left_on="member_id",
        right_on="member_concept_id",
        how="left",
    )
    df["canonical_mapped_total_freq"] = df["canonical_mapped_total_freq"].fillna(0).astype(int)
    df["member_mapped_total_freq"] = df["member_mapped_total_freq"].fillna(0).astype(int)
    df["canonicalization_confidence"] = np.select(
        [
            df["cosine_to_canonical"] >= 0.96,
            df["cosine_to_canonical"] >= 0.93,
            df["cosine_to_canonical"] >= 0.90,
        ],
        ["very_high", "high", "medium"],
        default="low",
    )
    df["apply_now"] = (
        (df["cosine_to_canonical"] >= 0.90)
        & (df["label_token_count"] >= 1)
        & df["alphabetic_label"]
        & ~df["canonical_source"].isin({"frontiergraph_v2_1_reviewed_family"})
        & ~df["member_source"].isin({"frontiergraph_v2_1_reviewed_family"})
    )
    df = df[df["apply_now"]].copy()
    if df.empty:
        return df
    df["canonicalization_reason"] = (
        "normalized label duplicate; cosine>=0.90; source-priority canonical retained"
    )
    keep_cols = [
        "cluster_id",
        "norm_label",
        "canonical_id",
        "canonical_label",
        "canonical_source",
        "member_id",
        "member_label",
        "member_source",
        "cosine_to_canonical",
        "canonicalization_confidence",
        "canonical_mapped_total_freq",
        "member_mapped_total_freq",
        "canonicalization_reason",
    ]
    return df[keep_cols].sort_values(
        ["member_mapped_total_freq", "canonical_mapped_total_freq", "cosine_to_canonical", "norm_label"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def compute_sink_targets(frontier: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "target_direct_in_degree",
        "target_support_in_degree",
        "target_incident_count",
        "target_evidence_diversity",
        "target_venue_diversity",
        "target_source_diversity",
    ]
    target_base_cols = ["v", "v_label"] + metric_cols
    targets = frontier[target_base_cols].drop_duplicates("v").copy()
    for col in metric_cols:
        targets[f"{col}_pct"] = targets[col].rank(method="average", pct=True)
    targets["sink_score"] = targets[[f"{c}_pct" for c in metric_cols]].mean(axis=1)
    targets["sink_score_pct"] = targets["sink_score"].rank(method="average", pct=True)

    for horizon in sorted(frontier["horizon"].dropna().unique()):
        sub = frontier[frontier["horizon"] == horizon]
        top20_counts = sub[sub["reranker_rank"] <= 20].groupby("v").size()
        top100_counts = sub[sub["reranker_rank"] <= 100].groupby("v").size()
        targets[f"top20_h{int(horizon)}"] = targets["v"].map(top20_counts).fillna(0).astype(int)
        targets[f"top100_h{int(horizon)}"] = targets["v"].map(top100_counts).fillna(0).astype(int)
    top20_counts = frontier[frontier["reranker_rank"] <= 20].groupby("v").size()
    top100_counts = frontier[frontier["reranker_rank"] <= 100].groupby("v").size()
    targets["top20_overall"] = targets["v"].map(top20_counts).fillna(0).astype(int)
    targets["top100_overall"] = targets["v"].map(top100_counts).fillna(0).astype(int)
    return targets.sort_values(["sink_score", "top100_overall"], ascending=[False, False]).reset_index(drop=True)


def build_mapping_aggregates(mapping: pd.DataFrame) -> pd.DataFrame:
    agg = (
        mapping.groupby(["onto_id", "onto_label"], as_index=False)
        .agg(
            mapped_rows=("label", "size"),
            mapped_total_freq=("freq", "sum"),
            mapped_distinct_labels=("label", pd.Series.nunique),
        )
        .rename(columns={"onto_id": "v", "onto_label": "v_label"})
    )
    return agg


def head_tokens_for_label(label: str) -> list[str]:
    return [t for t in tokenize(label) if t not in STOPWORDS]


def modifier_tokens(label: str, head_tokens: set[str]) -> list[str]:
    tokens = [t for t in tokenize(label) if t not in STOPWORDS and t not in head_tokens]
    return tokens


def endpoint_subfamily_diagnostics(mapping: pd.DataFrame, sink_targets: pd.DataFrame) -> pd.DataFrame:
    candidate_targets = sink_targets[
        (sink_targets["sink_score_pct"] >= 0.99)
    ][["v", "v_label", "sink_score", "sink_score_pct", "top100_overall"]].copy()

    rows: list[dict] = []
    for target in candidate_targets.itertuples(index=False):
        sub = mapping[mapping["onto_id"] == target.v].copy()
        if sub.empty:
            continue
        total_freq = int(sub["freq"].sum())
        if total_freq < 100:
            continue
        head = set(head_tokens_for_label(str(target.v_label)))
        if not head:
            continue

        modifier_counter: Counter[str] = Counter()
        measurement_freq = 0
        topical_freq = 0
        direct_phrase_freq = 0
        modifier_label_rows = 0
        raw_rows = 0

        pair_counter: Counter[tuple[str, str]] = Counter()
        for row in sub.itertuples(index=False):
            raw_rows += 1
            label = str(row.label)
            tokens = tokenize(label)
            token_set = set(tokens)
            freq = int(row.freq)
            if head.issubset(token_set) or normalize_label(str(target.v_label)) in normalize_label(label):
                direct_phrase_freq += freq
            mods = modifier_tokens(label, head)
            filtered_mods = [m for m in mods if m not in MEASUREMENT_TOKENS]
            if filtered_mods:
                topical_freq += freq
                modifier_label_rows += 1
                for m in filtered_mods:
                    modifier_counter[m] += freq
                uniq = sorted(set(filtered_mods))
                for i in range(len(uniq)):
                    for j in range(i + 1, len(uniq)):
                        pair_counter[(uniq[i], uniq[j])] += freq
            elif mods:
                measurement_freq += freq

        if not modifier_counter:
            continue

        total_mod_freq = sum(modifier_counter.values())
        probs = np.array([v / total_mod_freq for v in modifier_counter.values()], dtype=float)
        entropy = float(-(probs * np.log2(probs)).sum()) if len(probs) else 0.0

        adjacency: dict[str, set[str]] = defaultdict(set)
        for (a, b), weight in pair_counter.items():
            if weight >= 3:
                adjacency[a].add(b)
                adjacency[b].add(a)

        visited: set[str] = set()
        components: list[list[str]] = []
        top_tokens = {tok for tok, wt in modifier_counter.most_common(20) if wt >= 3}
        for token in top_tokens:
            if token in visited:
                continue
            stack = [token]
            comp: list[str] = []
            visited.add(token)
            while stack:
                cur = stack.pop()
                comp.append(cur)
                for nxt in adjacency.get(cur, set()):
                    if nxt in top_tokens and nxt not in visited:
                        visited.add(nxt)
                        stack.append(nxt)
            components.append(sorted(comp))

        orphan_tokens = sorted(top_tokens - {t for comp in components for t in comp})
        components.extend([[t] for t in orphan_tokens])
        components = sorted(components, key=lambda comp: -sum(modifier_counter[t] for t in comp))[:8]

        rows.append(
            {
                "target_id": target.v,
                "target_label": target.v_label,
                "sink_score": float(target.sink_score),
                "sink_score_pct": float(target.sink_score_pct),
                "top100_overall": int(target.top100_overall),
                "mapped_rows": int(len(sub)),
                "mapped_total_freq": total_freq,
                "direct_phrase_freq": direct_phrase_freq,
                "direct_phrase_share": float(direct_phrase_freq / max(total_freq, 1)),
                "measurement_only_freq": measurement_freq,
                "measurement_only_share": float(measurement_freq / max(total_freq, 1)),
                "topic_modifier_freq": topical_freq,
                "topic_modifier_share": float(topical_freq / max(total_freq, 1)),
                "modifier_entropy": entropy,
                "modifier_label_rows": int(modifier_label_rows),
                "top_modifier_tokens": json.dumps(modifier_counter.most_common(15), ensure_ascii=False),
                "modifier_components": json.dumps(components, ensure_ascii=False),
                "recommended_split": bool(topical_freq >= 25 and entropy >= 2.0 and len(components) >= 3),
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(
            ["recommended_split", "sink_score", "top100_overall", "mapped_total_freq"],
            ascending=[False, False, False, False],
        ).reset_index(drop=True)
    return out


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


def semantic_endpoint_subfamilies(
    mapping: pd.DataFrame,
    sink_targets: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_targets = sink_targets[
        (sink_targets["sink_score_pct"] >= 0.99) | (sink_targets["top100_overall"] >= 10)
    ][["v", "v_label", "sink_score", "sink_score_pct", "top100_overall"]].copy()

    endpoint_rows: list[dict] = []
    cluster_rows: list[dict] = []
    for target in candidate_targets.itertuples(index=False):
        sub = mapping[mapping["onto_id"] == target.v].copy()
        if sub.empty:
            continue

        phrases: list[str] = []
        freqs: list[int] = []
        raw_labels: list[str] = []
        for row in sub.itertuples(index=False):
            phrase = build_modifier_phrase(str(row.label), str(target.v_label))
            if not phrase:
                continue
            phrases.append(phrase)
            freqs.append(int(row.freq))
            raw_labels.append(str(row.label))

        if len(phrases) < 10:
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
                    "target_id": target.v,
                    "target_label": target.v_label,
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
        endpoint_rows.append(
            {
                "target_id": target.v,
                "target_label": target.v_label,
                "sink_score": float(target.sink_score),
                "sink_score_pct": float(target.sink_score_pct),
                "top100_overall": int(target.top100_overall),
                "modifier_phrase_rows": int(len(phrase_df)),
                "modifier_total_freq": int(total_freq),
                "semantic_cluster_count": int(len(cluster_summaries)),
                "significant_cluster_count": int(len(significant_clusters)),
                "semantic_cluster_entropy": cluster_entropy,
                "recommended_split_semantic": bool(len(significant_clusters) >= 2 and cluster_entropy >= 1.2),
                "top_semantic_clusters": json.dumps(cluster_summaries[:6], ensure_ascii=False),
            }
        )

    endpoint_df = pd.DataFrame(endpoint_rows)
    if not endpoint_df.empty:
        endpoint_df = endpoint_df.sort_values(
            ["recommended_split_semantic", "top100_overall", "sink_score", "modifier_total_freq"],
            ascending=[False, False, False, False],
        ).reset_index(drop=True)
    cluster_df = pd.DataFrame(cluster_rows)
    if not cluster_df.empty:
        cluster_df = cluster_df.sort_values(
            ["target_label", "cluster_freq", "cluster_exemplar"],
            ascending=[True, False, True],
        ).reset_index(drop=True)
    return endpoint_df, cluster_df


def apply_soft_sink_penalty(frontier: pd.DataFrame, sink_targets: pd.DataFrame) -> pd.DataFrame:
    df = frontier.copy()
    sink_map = sink_targets.set_index("v")[["sink_score", "sink_score_pct"]]
    df = df.join(sink_map, on="v")
    out_frames: list[pd.DataFrame] = []
    for horizon, sub in df.groupby("horizon", sort=False):
        g = sub.copy()
        n = len(g)
        g["reranker_pct"] = 1.0 - (g["reranker_rank"].astype(float) - 1.0) / max(n - 1, 1)
        g["sink_excess"] = ((g["sink_score_pct"].astype(float) - 0.98) / 0.02).clip(lower=0.0, upper=1.0)
        g["sink_penalty"] = 0.0125 * g["sink_excess"]
        g["adjusted_priority"] = g["reranker_pct"] - g["sink_penalty"]
        g = g.sort_values(["adjusted_priority", "reranker_pct"], ascending=[False, False]).reset_index(drop=True)
        g["adjusted_reranker_rank"] = g.index + 1
        out_frames.append(g)
    out = pd.concat(out_frames, ignore_index=True)
    return out


def apply_mild_sink_penalty_and_diversification(frontier: pd.DataFrame, sink_targets: pd.DataFrame) -> pd.DataFrame:
    df = frontier.copy()
    sink_map = sink_targets.set_index("v")[["sink_score", "sink_score_pct"]]
    df = df.join(sink_map, on="v")
    out_frames: list[pd.DataFrame] = []
    diversify_k = 300
    for _, sub in df.groupby("horizon", sort=False):
        g = sub.copy().reset_index(drop=True)
        n = len(g)
        g["reranker_pct"] = 1.0 - (g["reranker_rank"].astype(float) - 1.0) / max(n - 1, 1)
        g["mild_sink_excess"] = ((g["sink_score_pct"].astype(float) - 0.995) / 0.005).clip(lower=0.0, upper=1.0)
        g["mild_sink_penalty"] = 0.006 * g["mild_sink_excess"]
        g["base_priority"] = g["reranker_pct"] - g["mild_sink_penalty"]
        g = g.sort_values(["base_priority", "reranker_score"], ascending=[False, False]).reset_index(drop=True)

        top = g.head(diversify_k).copy()
        rest = g.iloc[diversify_k:].copy()
        selected_rows: list[pd.Series] = []
        target_counts: Counter[str] = Counter()
        top = top.copy()
        while not top.empty:
            penalties = top["v"].map(lambda target: 0.0045 * math.log1p(target_counts[target]) + 0.0015 * max(target_counts[target] - 1, 0))
            top = top.assign(
                diversification_penalty=penalties.astype(float),
                diversified_priority=top["base_priority"] - penalties.astype(float),
            )
            chosen_idx = top.sort_values(
                ["diversified_priority", "base_priority", "reranker_score"],
                ascending=[False, False, False],
            ).index[0]
            chosen = top.loc[chosen_idx]
            selected_rows.append(chosen)
            target_counts[str(chosen["v"])] += 1
            top = top.drop(index=chosen_idx)

        selected_df = pd.DataFrame(selected_rows)
        if rest.empty:
            out = selected_df.copy()
        else:
            rest = rest.assign(diversification_penalty=0.0, diversified_priority=rest["base_priority"])
            out = pd.concat([selected_df, rest], ignore_index=True)

        out = out.reset_index(drop=True)
        out["diversified_reranker_rank"] = out.index + 1
        out_frames.append(out)

    return pd.concat(out_frames, ignore_index=True)


def summarize_adjusted_frontier(frontier: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for label in ["Willingness to pay", "Carbon dioxide", "R&D", "Total factor productivity", "Green innovation"]:
        sub = frontier[frontier["v_label"] == label]
        rows.append(
            {
                "target_label": label,
                "top20_overall": int((sub["adjusted_reranker_rank"] <= 20).sum()),
                "top100_overall": int((sub["adjusted_reranker_rank"] <= 100).sum()),
                "top20_h5": int(((sub["horizon"] == 5) & (sub["adjusted_reranker_rank"] <= 20)).sum()),
                "top100_h5": int(((sub["horizon"] == 5) & (sub["adjusted_reranker_rank"] <= 100)).sum()),
                "top20_h10": int(((sub["horizon"] == 10) & (sub["adjusted_reranker_rank"] <= 20)).sum()),
                "top100_h10": int(((sub["horizon"] == 10) & (sub["adjusted_reranker_rank"] <= 100)).sum()),
            }
        )

    def endpoint_concentration_metric(df: pd.DataFrame, rank_col: str, k: int) -> tuple[int, int, float]:
        top = df[df[rank_col] <= k]
        counts = top["v_label"].value_counts(normalize=True)
        hhi = float((counts ** 2).sum()) if not counts.empty else 0.0
        return int(top["v_label"].nunique()), int(top.shape[0]), hhi

    for name, rank_col in [("baseline", "reranker_rank"), ("adjusted", "adjusted_reranker_rank")]:
        for k in [20, 100]:
            unique_targets, n_rows, hhi = endpoint_concentration_metric(frontier, rank_col, k)
            rows.append(
                {
                    "target_label": f"{name}_overall_top{k}",
                    "top20_overall": unique_targets if k == 20 else np.nan,
                    "top100_overall": unique_targets if k == 100 else np.nan,
                    "top20_h5": hhi if k == 20 else np.nan,
                    "top100_h5": hhi if k == 100 else np.nan,
                    "top20_h10": n_rows if k == 20 else np.nan,
                    "top100_h10": n_rows if k == 100 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def summarize_diversified_frontier(frontier: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    focus_targets = [
        "Willingness to pay",
        "Economic Growth",
        "R&D",
        "Carbon dioxide",
        "Total factor productivity",
        "Green innovation",
    ]
    for label in focus_targets:
        sub = frontier[frontier["v_label"] == label]
        rows.append(
            {
                "target_label": label,
                "baseline_top20": int((sub["reranker_rank"] <= 20).sum()),
                "baseline_top100": int((sub["reranker_rank"] <= 100).sum()),
                "diversified_top20": int((sub["diversified_reranker_rank"] <= 20).sum()),
                "diversified_top100": int((sub["diversified_reranker_rank"] <= 100).sum()),
            }
        )

    for name, rank_col in [("baseline", "reranker_rank"), ("diversified", "diversified_reranker_rank")]:
        for k in [20, 100]:
            top = frontier[frontier[rank_col] <= k]
            counts = top["v_label"].value_counts(normalize=True)
            hhi = float((counts ** 2).sum()) if not counts.empty else 0.0
            rows.append(
                {
                    "target_label": f"{name}_overall_top{k}",
                    "baseline_top20": int(top["v_label"].nunique()) if k == 20 else np.nan,
                    "baseline_top100": int(top["v_label"].nunique()) if k == 100 else np.nan,
                    "diversified_top20": hhi if k == 20 else np.nan,
                    "diversified_top100": hhi if k == 100 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def write_markdown(
    canonical_df: pd.DataFrame,
    applied_canonical_df: pd.DataFrame,
    sink_df: pd.DataFrame,
    adjusted_frontier: pd.DataFrame,
    subfamily_df: pd.DataFrame,
    diversified_frontier: pd.DataFrame,
    semantic_subfamily_df: pd.DataFrame,
) -> None:
    lines: list[str] = [
        "# v2.1 Sink / Canonicalization Diagnostic",
        "",
    ]

    if not canonical_df.empty:
        lines.extend(
            [
                "## Cross-Source Canonicalization",
                "",
                f"- candidate duplicate member rows: `{len(canonical_df):,}`",
                f"- duplicate norm-label clusters: `{canonical_df['cluster_id'].nunique():,}`",
                "",
                "Top examples:",
            ]
        )
        top = canonical_df.head(20)
        for row in top.itertuples(index=False):
            lines.append(
                f"- `{row.norm_label}`: canonical `{row.canonical_label}` ({row.canonical_source}) vs "
                f"`{row.member_label}` ({row.member_source}), cosine `{float(row.cosine_to_canonical):.3f}`"
            )

    lines.extend(["", "## Applied Canonicalization (Clearest Pairs First)", ""])
    if applied_canonical_df.empty:
        lines.append("No applied canonicalization pairs passed the conservative filter.")
    else:
        lines.append(f"- applied duplicate member rows: `{len(applied_canonical_df):,}`")
        lines.append(f"- applied duplicate norm-label clusters: `{applied_canonical_df['cluster_id'].nunique():,}`")
        lines.append("")
        for row in applied_canonical_df.head(20).itertuples(index=False):
            lines.append(
                f"- `{row.norm_label}`: canonical `{row.canonical_label}` ({row.canonical_source}) <- "
                f"`{row.member_label}` ({row.member_source}), cosine `{float(row.cosine_to_canonical):.3f}`, "
                f"member support `{int(row.member_mapped_total_freq):,}`"
            )

    lines.extend(["", "## Top Sink Endpoints", ""])
    top_sink = sink_df.head(20)
    for row in top_sink.itertuples(index=False):
        lines.append(
            f"- `{row.v_label}` | sink_score `{float(row.sink_score):.3f}` | top100 `{int(row.top100_overall)}` "
            f"| in-degree `{int(row.target_direct_in_degree)}` | support-in `{int(row.target_support_in_degree)}`"
        )

    lines.extend(["", "## WTP Before/After Soft Sink Penalty", ""])
    for horizon in [5, 10]:
        sub = adjusted_frontier[(adjusted_frontier["v_label"] == "Willingness to pay") & (adjusted_frontier["horizon"] == horizon)]
        before20 = int((sub["reranker_rank"] <= 20).sum())
        before100 = int((sub["reranker_rank"] <= 100).sum())
        after20 = int((sub["adjusted_reranker_rank"] <= 20).sum())
        after100 = int((sub["adjusted_reranker_rank"] <= 100).sum())
        lines.append(f"- h={horizon}: top20 `{before20} -> {after20}`, top100 `{before100} -> {after100}`")

    lines.extend(["", "## WTP Before/After Mild Sink Penalty + Diversification", ""])
    for horizon in [5, 10]:
        sub = diversified_frontier[
            (diversified_frontier["v_label"] == "Willingness to pay") & (diversified_frontier["horizon"] == horizon)
        ]
        before20 = int((sub["reranker_rank"] <= 20).sum())
        before100 = int((sub["reranker_rank"] <= 100).sum())
        after20 = int((sub["diversified_reranker_rank"] <= 20).sum())
        after100 = int((sub["diversified_reranker_rank"] <= 100).sum())
        lines.append(f"- h={horizon}: top20 `{before20} -> {after20}`, top100 `{before100} -> {after100}`")

    lines.extend(["", "## High-Support Flexible Endpoints", ""])
    if subfamily_df.empty:
        lines.append("No endpoints met the prototype split criteria.")
    else:
        for row in subfamily_df.head(20).itertuples(index=False):
            lines.append(
                f"- `{row.target_label}` | split={bool(row.recommended_split)} | top100 `{int(row.top100_overall)}` | "
                f"topic-modifier-share `{float(row.topic_modifier_share):.3f}` | entropy `{float(row.modifier_entropy):.3f}` | "
                f"components `{row.modifier_components}`"
            )

    lines.extend(["", "## Semantic Modifier-Cluster Split Prototype", ""])
    if semantic_subfamily_df.empty:
        lines.append("No endpoints met the semantic split prototype criteria.")
    else:
        for row in semantic_subfamily_df.head(12).itertuples(index=False):
            lines.append(
                f"- `{row.target_label}` | split={bool(row.recommended_split_semantic)} | top100 `{int(row.top100_overall)}` | "
                f"semantic-clusters `{int(row.semantic_cluster_count)}` | significant-clusters `{int(row.significant_cluster_count)}` | "
                f"cluster-entropy `{float(row.semantic_cluster_entropy):.3f}` | "
                f"top-clusters `{row.top_semantic_clusters}`"
            )

    SINK_NOTE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    canon_lines = [
        "# Cross-Source Canonicalization Candidates",
        "",
        "These are obvious cross-source duplicates identified by normalized label identity.",
        "",
    ]
    if canonical_df.empty:
        canon_lines.append("No candidate duplicates found.")
    else:
        for row in canonical_df.head(100).itertuples(index=False):
            canon_lines.append(
                f"- `{row.norm_label}`: canonical `{row.canonical_label}` ({row.canonical_source}) <- "
                f"`{row.member_label}` ({row.member_source}), cosine `{float(row.cosine_to_canonical):.3f}`"
            )
    CANONICAL_NOTE_PATH.write_text("\n".join(canon_lines) + "\n", encoding="utf-8")

    applied_lines = [
        "# Applied Cross-Source Canonicalization",
        "",
        "These pairs passed the conservative application filter: normalized-label duplicate, cosine >= 0.90, and non-family sources.",
        "",
    ]
    if applied_canonical_df.empty:
        applied_lines.append("No applied canonicalization pairs found.")
    else:
        for row in applied_canonical_df.head(100).itertuples(index=False):
            applied_lines.append(
                f"- `{row.norm_label}`: canonical `{row.canonical_label}` ({row.canonical_source}) <- "
                f"`{row.member_label}` ({row.member_source}), cosine `{float(row.cosine_to_canonical):.3f}`, "
                f"member support `{int(row.member_mapped_total_freq):,}`"
            )
    APPLIED_CANONICAL_NOTE_PATH.write_text("\n".join(applied_lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    canonical_df = build_cross_source_canonicalization()
    canonical_df.to_parquet(CANONICAL_TABLE_PATH, index=False)

    mapping = pd.read_parquet(MAPPING_V2_1_PATH)
    frontier = pd.read_parquet(FRONTIER_PATH)
    applied_canonical_df = build_applied_canonicalization(canonical_df, mapping)
    applied_canonical_df.to_csv(APPLIED_CANONICAL_TABLE_PATH, index=False)

    sink_df = compute_sink_targets(frontier)
    sink_df = sink_df.merge(build_mapping_aggregates(mapping), on=["v", "v_label"], how="left")
    sink_df.to_csv(SINK_TABLE_PATH, index=False)

    adjusted_frontier = apply_soft_sink_penalty(frontier, sink_df)
    adjusted_frontier.to_parquet(ADJUSTED_FRONTIER_PATH, index=False)

    adjusted_summary = summarize_adjusted_frontier(adjusted_frontier)
    adjusted_summary.to_csv(ADJUSTED_SUMMARY_PATH, index=False)

    subfamily_df = endpoint_subfamily_diagnostics(mapping, sink_df)
    subfamily_df.to_csv(SUBFAMILY_PATH, index=False)

    diversified_frontier = apply_mild_sink_penalty_and_diversification(frontier, sink_df)
    diversified_frontier.to_parquet(DIVERSIFIED_FRONTIER_PATH, index=False)

    diversified_summary = summarize_diversified_frontier(diversified_frontier)
    diversified_summary.to_csv(DIVERSIFIED_SUMMARY_PATH, index=False)

    semantic_subfamily_df, semantic_subfamily_clusters = semantic_endpoint_subfamilies(mapping, sink_df)
    semantic_subfamily_df.to_csv(SEMANTIC_SUBFAMILY_PATH, index=False)
    semantic_subfamily_clusters.to_csv(SEMANTIC_SUBFAMILY_CLUSTER_PATH, index=False)

    write_markdown(
        canonical_df,
        applied_canonical_df,
        sink_df,
        adjusted_frontier,
        subfamily_df,
        diversified_frontier,
        semantic_subfamily_df,
    )

    print(f"Wrote canonical candidates: {CANONICAL_TABLE_PATH}")
    print(f"Wrote applied canonicalization table: {APPLIED_CANONICAL_TABLE_PATH}")
    print(f"Wrote sink table: {SINK_TABLE_PATH}")
    print(f"Wrote adjusted frontier: {ADJUSTED_FRONTIER_PATH}")
    print(f"Wrote diversified frontier: {DIVERSIFIED_FRONTIER_PATH}")
    print(f"Wrote subfamily diagnostics: {SUBFAMILY_PATH}")
    print(f"Wrote semantic subfamily diagnostics: {SEMANTIC_SUBFAMILY_PATH}")
    print(f"Wrote summary note: {SINK_NOTE_PATH}")


if __name__ == "__main__":
    main()
