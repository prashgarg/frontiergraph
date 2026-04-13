from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

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

METHOD_TOKENS = {
    "analysis",
    "backtesting",
    "estimate",
    "estimated",
    "estimation",
    "estimations",
    "experiment",
    "experiments",
    "forecast",
    "forecasting",
    "indicator",
    "indicators",
    "measure",
    "measures",
    "measurement",
    "method",
    "methodology",
    "model",
    "models",
    "monte",
    "procedure",
    "score",
    "scores",
    "series",
    "simulation",
    "simulations",
    "theory",
    "var",
}

CONTEXT_TOKENS = {
    "aca",
    "act",
    "adults",
    "city",
    "countries",
    "country",
    "covid",
    "deaths",
    "families",
    "income",
    "obamacare",
    "pandemic",
    "patients",
    "region",
    "regions",
    "respondents",
    "sector",
    "sectors",
    "workers",
}

GENERIC_TARGET_PHRASES = {
    "cost efficiency",
    "crisis",
    "economic behavior",
    "economic conditions",
    "efficiency",
    "general equilibrium theory",
    "optimal decision",
    "production efficiency",
    "resource allocation",
    "sustainability",
    "technical progress",
}

GENERIC_CLUSTER_TOKENS = {
    "aggregate",
    "annual",
    "approach",
    "changes",
    "change",
    "conditions",
    "context",
    "current",
    "dynamics",
    "effect",
    "effects",
    "factors",
    "global",
    "gains",
    "likelihood",
    "level",
    "levels",
    "optimal",
    "optimality",
    "path",
    "paths",
    "plan",
    "plans",
    "policies",
    "policy",
    "probability",
    "probabilities",
    "rate",
    "rates",
    "rule",
    "rules",
    "structure",
    "total",
}

TRIVIAL_ALIAS_TOKENS = {
    "ation",
    "ations",
    "es",
    "s",
    "tax",
    "taxation",
    "taxes",
}

GENERIC_CHILD_BLACKLIST = {
    "aggregate",
    "annual",
    "changes",
    "change",
    "current",
    "data",
    "dynamics",
    "effects",
    "effect",
    "global",
    "hypothesis",
    "index",
    "indices",
    "level",
    "levels",
    "optimal",
    "policies",
    "policy",
    "prices",
    "price",
    "rate",
    "rates",
    "spreads",
    "structure",
    "total",
    "ekc",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a second-stage guardrail over flexible endpoints and promote guarded child concepts into v2.2.")
    parser.add_argument(
        "--regime-table",
        default="outputs/paper/62_flexible_endpoint_regime_study/flexible_endpoint_regime_table.csv",
    )
    parser.add_argument(
        "--mapping",
        default="data/ontology_v2/extraction_label_mapping_v2_1_canonicalized.parquet",
    )
    parser.add_argument(
        "--ontology-json",
        default="data/ontology_v2/ontology_v2_1_canonicalized.json",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paper/63_flexible_endpoint_guardrail",
    )
    parser.add_argument(
        "--guardrail-note",
        default="next_steps/flexible_endpoint_guardrail.md",
    )
    parser.add_argument(
        "--child-families-out",
        default="data/ontology_v2/ontology_v2_2_guardrailed_child_families.parquet",
    )
    parser.add_argument(
        "--ontology-out",
        default="data/ontology_v2/ontology_v2_2_guardrailed.json",
    )
    parser.add_argument(
        "--mapping-out",
        default="data/ontology_v2/extraction_label_mapping_v2_2_guardrailed.parquet",
    )
    parser.add_argument(
        "--build-note",
        default="data/ontology_v2/ontology_v2_2_guardrailed_note.md",
    )
    return parser.parse_args()


def normalize_label(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def tokenize(value: Any) -> list[str]:
    return normalize_label(value).split()


def parse_json_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(v).strip() for v in raw if str(v).strip()]
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(v).strip() for v in payload if str(v).strip()]


def choose_display_label(values: list[str], weights: list[int] | None = None) -> str:
    counter: Counter[str] = Counter()
    if weights is None:
        weights = [1] * len(values)
    for value, weight in zip(values, weights):
        text = str(value or "").strip()
        if text:
            counter[text] += int(weight)
    if not counter:
        return ""
    return sorted(counter.items(), key=lambda item: (-item[1], -sum(tok[:1].isupper() for tok in item[0].split()), item[0].lower()))[0][0]


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
        if len(tok) > 1 and tok not in STOPWORDS and tok not in target_tokens
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
        component: list[int] = []
        while stack:
            cur = stack.pop()
            component.append(cur)
            for nxt in adjacency.get(cur, set()):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        components.append(sorted(component))
    return components


def stable_child_id(parent_id: str, child_norm: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", child_norm).strip("-")[:48] or "child"
    digest = hashlib.sha1(f"{parent_id}::{child_norm}".encode("utf-8")).hexdigest()[:10]
    return f"FGV22CHILD:{slug}:{digest}"


def build_phrase_clusters(mapping: pd.DataFrame, candidate_targets: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target in candidate_targets.itertuples(index=False):
        sub = mapping[mapping["onto_id"] == target.target_id].copy()
        if sub.empty:
            continue
        phrase_rows: list[dict[str, Any]] = []
        for row in sub.itertuples(index=False):
            phrase = build_modifier_phrase(str(row.label), str(target.target_label))
            if not phrase:
                continue
            phrase_rows.append(
                {
                    "modifier_phrase": phrase,
                    "freq": int(row.freq),
                    "raw_label": str(row.label),
                }
            )
        if len(phrase_rows) < 10:
            continue
        phrase_df = pd.DataFrame(phrase_rows)
        grouped = (
            phrase_df.groupby("modifier_phrase", as_index=False)
            .agg(
                total_freq=("freq", "sum"),
                raw_labels=("raw_label", lambda s: json.dumps(list(pd.Series(s).head(10)), ensure_ascii=False)),
                raw_label_count=("raw_label", pd.Series.nunique),
            )
            .sort_values(["total_freq", "modifier_phrase"], ascending=[False, True])
            .reset_index(drop=True)
        )
        if len(grouped) < 4:
            continue
        X = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit_transform(grouped["modifier_phrase"].tolist())
        sim = cosine_similarity(X)
        components = connected_components_from_similarity(sim, threshold=0.35)
        total_freq = float(grouped["total_freq"].sum())
        for cluster_id, component in enumerate(sorted(components, key=lambda comp: -float(grouped.iloc[comp]["total_freq"].sum()))):
            cluster = grouped.iloc[component].copy().sort_values(["total_freq", "modifier_phrase"], ascending=[False, True])
            cluster_freq = int(cluster["total_freq"].sum())
            cluster_share = float(cluster_freq / total_freq) if total_freq else 0.0
            exemplar = str(cluster.iloc[0]["modifier_phrase"])
            example_labels: list[str] = []
            example_weights: list[int] = []
            for item in cluster.itertuples(index=False):
                labels = parse_json_list(item.raw_labels)
                for label in labels:
                    example_labels.append(label)
                    example_weights.append(int(item.total_freq))
            top_example_labels = list(dict.fromkeys(example_labels))[:10]
            rows.append(
                {
                    "target_id": str(target.target_id),
                    "target_label": str(target.target_label),
                    "norm_label": str(target.norm_label),
                    "cluster_id": int(cluster_id),
                    "cluster_freq": cluster_freq,
                    "cluster_share": cluster_share,
                    "cluster_size": int(len(cluster)),
                    "cluster_exemplar": exemplar,
                    "top_modifier_phrases": json.dumps(cluster["modifier_phrase"].head(8).tolist(), ensure_ascii=False),
                    "top_example_labels": json.dumps(top_example_labels, ensure_ascii=False),
                    "cluster_phrase_members": json.dumps(cluster["modifier_phrase"].tolist(), ensure_ascii=False),
                    "cluster_raw_label_count": int(cluster["raw_label_count"].sum()),
                    "cluster_display_label": choose_display_label(example_labels, example_weights),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["is_significant_cluster"] = (out["cluster_freq"] >= 50) & (out["cluster_share"] >= 0.08)
    return out


def classify_cluster_guardrail(target_label: str, row: pd.Series) -> tuple[str, str]:
    exemplar = str(row.get("cluster_exemplar", "")).strip()
    top_examples = parse_json_list(row.get("top_example_labels"))
    top_phrases = parse_json_list(row.get("top_modifier_phrases"))
    remainder_tokens: list[str] = []
    for label in top_examples[:5]:
        remainder_tokens.extend(tokenize(build_modifier_phrase(label, target_label)))
    if not remainder_tokens:
        remainder_tokens = tokenize(exemplar)
    token_set = set(remainder_tokens)
    full_text = " ".join([exemplar] + top_examples + top_phrases)
    full_token_set = set(tokenize(full_text))

    if exemplar in {"", "ation", "ations", "es", "s"}:
        return "alias_or_surface_cluster", "cluster remainder is only a morphological suffix or trivial alias fragment"
    if token_set and token_set.issubset(TRIVIAL_ALIAS_TOKENS):
        return "alias_or_surface_cluster", "cluster examples reduce to trivial pluralization or tax/taxation style surface forms"
    if re.search(r"\b(19|20)\d{2}\b", full_text):
        return "contextual_cluster", "cluster is anchored to a dated event or episode"
    if full_token_set & METHOD_TOKENS:
        return "method_or_measurement_cluster", "cluster is dominated by method, model, forecast, indicator, or measurement language"
    if full_token_set & CONTEXT_TOKENS:
        return "contextual_cluster", "cluster is dominated by population, place, sector, or event context language"
    exemplar_tokens = set(tokenize(exemplar))
    if exemplar_tokens and exemplar_tokens.issubset(GENERIC_CLUSTER_TOKENS):
        return "generic_modifier_cluster", "cluster exemplar is only a generic qualifier such as structure, level, policy, or probability"
    if token_set and token_set.issubset(GENERIC_CLUSTER_TOKENS):
        return "generic_modifier_cluster", "cluster modifier is only a generic qualifier such as level, change, structure, or policy"
    if (full_token_set & GENERIC_CLUSTER_TOKENS) and not (token_set - GENERIC_CLUSTER_TOKENS):
        return "generic_modifier_cluster", "cluster is driven by generic qualifier language without a narrower substantive family"
    if len([tok for tok in token_set if tok not in GENERIC_CLUSTER_TOKENS]) == 0:
        return "unclear_cluster", "cluster lacks enough non-generic modifier content"
    return "substantive_child_candidate", "cluster contains a narrower substantive modifier family that could justify a child concept"


def classify_endpoint_guardrail(target_label: str, significant_clusters: pd.DataFrame) -> tuple[str, str]:
    target_norm = normalize_label(target_label)
    target_tokens = set(tokenize(target_label))
    cluster_counts = Counter(significant_clusters["cluster_guardrail_category"].astype(str).tolist())
    substantive_count = int(cluster_counts.get("substantive_child_candidate", 0))
    method_count = int(cluster_counts.get("method_or_measurement_cluster", 0))
    context_count = int(cluster_counts.get("contextual_cluster", 0))
    generic_count = int(cluster_counts.get("generic_modifier_cluster", 0) + cluster_counts.get("alias_or_surface_cluster", 0))

    if target_norm in GENERIC_TARGET_PHRASES or (target_tokens & METHOD_TOKENS):
        if substantive_count >= 2:
            return "substantive_family_candidate", "despite a generic or methodological parent label, multiple significant clusters look like real child families"
        if target_tokens & METHOD_TOKENS:
            return "method_or_measurement_container", "target label is itself a method, model, or measurement container"
        return "generic_behavior_or_theory_container", "target label is a broad abstract container and lacks enough substantive child-family clusters"
    if target_tokens & CONTEXT_TOKENS:
        return "contextual_bucket", "target label names a population, place, event, or policy context rather than a stable substantive family"
    if context_count >= max(2, substantive_count + 1):
        return "contextual_bucket", "significant clusters are mostly contextual rather than narrower substantive families"
    if method_count >= max(2, substantive_count + 1):
        return "method_or_measurement_container", "significant clusters are mostly methodological or measurement-oriented"
    if substantive_count >= 2:
        return "substantive_family_candidate", "multiple significant clusters survive the guardrail and look like narrower substantive families"
    if substantive_count >= 1 and generic_count == 0:
        return "substantive_family_candidate", "at least one significant cluster is substantively narrower and the parent is not a generic or contextual container"
    if generic_count >= 1:
        return "generic_behavior_or_theory_container", "clusters are mostly generic modifiers or surface variants rather than clean child families"
    return "unclear", "endpoint needs stronger evidence before allowing ontology growth"


def build_guardrail_tables(regime: pd.DataFrame, mapping: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = regime[regime["suggested_regime"] == "study_subfamily_candidate"].copy()
    cluster_df = build_phrase_clusters(mapping, candidates[["target_id", "target_label", "norm_label"]])
    if cluster_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    categories: list[str] = []
    reasons: list[str] = []
    for row in cluster_df.itertuples(index=False):
        cat, reason = classify_cluster_guardrail(str(row.target_label), pd.Series(row._asdict()))
        categories.append(cat)
        reasons.append(reason)
    cluster_df["cluster_guardrail_category"] = categories
    cluster_df["cluster_guardrail_reason"] = reasons

    endpoint_rows: list[dict[str, Any]] = []
    for target in candidates.itertuples(index=False):
        sub = cluster_df[(cluster_df["target_id"] == str(target.target_id)) & (cluster_df["is_significant_cluster"])].copy()
        cat, reason = classify_endpoint_guardrail(str(target.target_label), sub)
        counts = Counter(sub["cluster_guardrail_category"].astype(str).tolist())
        endpoint_rows.append(
            {
                "target_id": str(target.target_id),
                "target_label": str(target.target_label),
                "mapped_total_freq": int(target.mapped_total_freq),
                "significant_cluster_count": int(getattr(target, "significant_cluster_count", 0)),
                "dominant_cluster_share": float(getattr(target, "dominant_cluster_share", 0.0)),
                "endpoint_guardrail_category": cat,
                "endpoint_guardrail_reason": reason,
                "significant_substantive_clusters": int(counts.get("substantive_child_candidate", 0)),
                "significant_generic_clusters": int(counts.get("generic_modifier_cluster", 0) + counts.get("alias_or_surface_cluster", 0)),
                "significant_method_clusters": int(counts.get("method_or_measurement_cluster", 0)),
                "significant_context_clusters": int(counts.get("contextual_cluster", 0)),
                "top_guardrailed_clusters_json": json.dumps(
                    sub.sort_values(["cluster_freq", "cluster_share"], ascending=[False, False])[
                        [
                            "cluster_id",
                            "cluster_freq",
                            "cluster_share",
                            "cluster_exemplar",
                            "cluster_guardrail_category",
                        ]
                    ].head(6).to_dict(orient="records"),
                    ensure_ascii=False,
                ),
            }
        )
    endpoint_df = pd.DataFrame(endpoint_rows).sort_values(
        ["endpoint_guardrail_category", "mapped_total_freq", "target_label"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    return endpoint_df, cluster_df


def existing_ontology_lookup(ontology_rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    by_norm: dict[str, dict[str, Any]] = {}
    label_norms: set[str] = set()
    for row in ontology_rows:
        label = str(row.get("label", "")).strip()
        norm = normalize_label(label)
        if not norm:
            continue
        by_norm.setdefault(
            norm,
            {
                "onto_id": str(row["id"]),
                "onto_label": label,
                "onto_source": str(row.get("source", "")),
                "onto_domain": str(row.get("domain", "")),
            },
        )
        label_norms.add(norm)
    return by_norm, label_norms


def pick_child_label(target_label: str, row: pd.Series, existing_norms: set[str]) -> tuple[str, str]:
    examples = parse_json_list(row.get("top_example_labels"))
    clean_examples: list[str] = []
    if examples:
        for example in examples[:10]:
            norm_example = normalize_label(example)
            if not norm_example:
                continue
            if any(ch in str(example) for ch in ["/", "(", ")", "[", "]"]):
                continue
            if len(tokenize(example)) > 8:
                continue
            remainder = tokenize(build_modifier_phrase(example, target_label))
            if not remainder:
                continue
            clean_examples.append(str(example).strip())
        for example in clean_examples:
            if normalize_label(example) in existing_norms:
                return example, normalize_label(example)
        if clean_examples:
            return clean_examples[0], normalize_label(clean_examples[0])
        for example in examples[:10]:
            if normalize_label(example) in existing_norms:
                return example, normalize_label(example)
        display = choose_display_label(examples[:8])
        if display:
            return display, normalize_label(display)
    exemplar = str(row.get("cluster_exemplar", "")).strip()
    if exemplar:
        target_norm = normalize_label(target_label)
        if target_norm:
            return f"{exemplar.title()} {target_label}", normalize_label(f"{exemplar} {target_norm}")
    return "", ""


def build_child_family_candidates(
    endpoint_df: pd.DataFrame,
    cluster_df: pd.DataFrame,
    ontology_rows: list[dict[str, Any]],
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    onto_lookup, existing_norms = existing_ontology_lookup(ontology_rows)
    parent_lookup = {
        str(row["id"]): {
            "parent_label": str(row.get("label", "")),
            "parent_domain": str(row.get("domain", "")),
        }
        for row in ontology_rows
    }
    allowed_parents = set(endpoint_df.loc[endpoint_df["endpoint_guardrail_category"] == "substantive_family_candidate", "target_id"].astype(str))
    rows: list[dict[str, Any]] = []
    endpoint_category_lookup = endpoint_df.set_index("target_id")["endpoint_guardrail_category"].to_dict()
    for row in cluster_df.itertuples(index=False):
        row_dict = row._asdict()
        target_id = str(row_dict["target_id"])
        target_label = str(row_dict["target_label"])
        target_norm = normalize_label(target_label)
        parent_meta = parent_lookup.get(target_id, {"parent_label": target_label, "parent_domain": ""})
        endpoint_category = str(endpoint_category_lookup.get(target_id, "unclear"))
        child_label, child_norm = pick_child_label(target_label, pd.Series(row_dict), existing_norms)
        existing = onto_lookup.get(child_norm) if child_norm else None
        tokens = set(tokenize(build_modifier_phrase(child_label, target_label)))
        promote = False
        action = "skip"
        reason = "cluster does not pass the guardrail"

        if target_id not in allowed_parents and existing is None:
            reason = "parent endpoint is not guardrailed as a substantive family candidate"
        elif not bool(row_dict["is_significant_cluster"]):
            reason = "cluster is below the significance threshold"
        elif str(row_dict["cluster_guardrail_category"]) != "substantive_child_candidate":
            reason = "cluster is not guardrailed as a substantive child candidate"
        elif not child_label or not child_norm:
            reason = "cluster does not yield a usable child label"
        elif len(tokenize(child_label)) == 1 and existing is None:
            reason = "single-token child labels are too weak to promote unless they already exist in the ontology"
        elif tokens and tokens.issubset(CONTEXT_TOKENS) and existing is None:
            reason = "context-only child labels are too brittle to promote as new ontology nodes"
        elif tokens and tokens.issubset(GENERIC_CHILD_BLACKLIST):
            reason = "candidate child label is only a generic modifier"
        elif existing is not None:
            promote = True
            action = "attach_existing_ontology_child"
            reason = "candidate child label already exists in the ontology and can be used directly"
        elif target_norm in GENERIC_TARGET_PHRASES:
            reason = "generic parent endpoints can attach existing children, but do not create new ontology rows in this guarded pass"
        elif int(row_dict["cluster_size"]) >= 2 or int(row_dict["cluster_freq"]) >= 100:
            promote = True
            action = "promote_new_child_family"
            reason = "cluster is substantively narrower and has enough support to justify a guarded child concept"
        else:
            reason = "cluster support is too narrow for a new child concept"

        child_id = existing["onto_id"] if existing is not None else (stable_child_id(target_id, child_norm) if child_norm else "")
        child_source = existing["onto_source"] if existing is not None else "frontiergraph_v2_2_guardrailed_child_family"
        child_domain = existing["onto_domain"] if existing is not None else (parent_meta["parent_domain"] or "other_valid")
        child_onto_label = existing["onto_label"] if existing is not None else child_label
        rows.append(
            {
                "parent_onto_id": target_id,
                "parent_onto_label": parent_meta["parent_label"],
                "parent_domain": parent_meta["parent_domain"],
                "cluster_id": int(row_dict["cluster_id"]),
                "cluster_freq": int(row_dict["cluster_freq"]),
                "cluster_share": float(row_dict["cluster_share"]),
                "cluster_size": int(row_dict["cluster_size"]),
                "cluster_exemplar": str(row_dict["cluster_exemplar"]),
                "cluster_guardrail_category": str(row_dict["cluster_guardrail_category"]),
                "cluster_guardrail_reason": str(row_dict["cluster_guardrail_reason"]),
                "top_modifier_phrases": str(row_dict["top_modifier_phrases"]),
                "top_example_labels": str(row_dict["top_example_labels"]),
                "cluster_phrase_members": str(row_dict["cluster_phrase_members"]),
                "cluster_raw_label_count": int(row_dict["cluster_raw_label_count"]),
                "child_label": child_label,
                "child_norm": child_norm,
                "child_id": child_id,
                "child_source": child_source,
                "child_domain": child_domain,
                "existing_exact_onto_id": existing["onto_id"] if existing is not None else None,
                "existing_exact_onto_label": existing["onto_label"] if existing is not None else None,
                "promotion_action": action,
                "promotion_reason": reason,
                "promote_to_v2_2": bool(promote),
                "promote_to_v2_1": bool(promote),
                "aliases_json": json.dumps(parse_json_list(row_dict["top_example_labels"])[:20], ensure_ascii=False),
                "description": (
                    f"Guardrailed child concept under {parent_meta['parent_label']} "
                    f"from a semantic modifier cluster with support {int(row_dict['cluster_freq'])}."
                ),
                "endpoint_guardrail_category": endpoint_category,
            }
        )

    out = pd.DataFrame(rows).sort_values(
        ["promote_to_v2_2", "promotion_action", "cluster_freq", "cluster_share"],
        ascending=[False, True, False, False],
    ).reset_index(drop=True)
    return out


def build_v2_2_ontology(base_rows: list[dict[str, Any]], child_candidates: pd.DataFrame) -> list[dict[str, Any]]:
    out = list(base_rows)
    new_children = child_candidates[
        (child_candidates["promote_to_v2_2"]) & (child_candidates["promotion_action"] == "promote_new_child_family")
    ].copy()
    for row in new_children.itertuples(index=False):
        out.append(
            {
                "id": str(row.child_id),
                "label": str(row.child_label),
                "description": str(row.description),
                "source": "frontiergraph_v2_2_guardrailed_child_family",
                "domain": str(row.child_domain or "other_valid"),
                "parent_label": str(row.parent_onto_label or ""),
                "root_label": str(row.parent_onto_label or ""),
                "_sources": [
                    {
                        "source": "frontiergraph_v2_2_guardrailed_child_family",
                        "id": str(row.child_id),
                        "label": str(row.child_label),
                    }
                ],
            }
        )
    return out


def build_mapping_v2_2(mapping: pd.DataFrame, child_candidates: pd.DataFrame) -> pd.DataFrame:
    out = mapping.copy()
    out["v2_2_mapping_action"] = "carry_forward_v2_1_mapping"
    out["v2_2_parent_onto_id"] = None
    out["v2_2_parent_onto_label"] = None
    out["v2_2_child_cluster_id"] = np.nan
    out["v2_2_child_label"] = None
    out["v2_2_original_onto_id"] = out["onto_id"]
    out["v2_2_original_onto_label"] = out["onto_label"]

    promoted = child_candidates[child_candidates["promote_to_v2_2"]].copy()
    if promoted.empty:
        return out

    for row in promoted.itertuples(index=False):
        phrase_members = set(parse_json_list(row.cluster_phrase_members))
        if not phrase_members:
            continue
        target_id = str(row.parent_onto_id)
        target_label = str(row.parent_onto_label)
        child_id = str(row.child_id)
        child_label = str(row.child_label)
        child_source = str(row.child_source)
        child_domain = str(row.child_domain)
        action = str(row.promotion_action)

        mask = out["onto_id"].astype(str).eq(target_id)
        if not mask.any():
            continue
        modifier_phrases = out.loc[mask, "label"].map(lambda x: build_modifier_phrase(str(x), target_label))
        member_mask = modifier_phrases.isin(phrase_members)
        if not member_mask.any():
            continue
        selected = out.loc[mask].index[member_mask.values]
        out.loc[selected, "onto_id"] = child_id
        out.loc[selected, "onto_label"] = child_label
        out.loc[selected, "onto_source"] = child_source
        out.loc[selected, "onto_domain"] = child_domain
        out.loc[selected, "matched_via"] = "v2_2_guardrailed_child_family"
        out.loc[selected, "match_kind"] = (
            "guardrailed_existing_child_concept" if action == "attach_existing_ontology_child" else "guardrailed_promoted_child_family"
        )
        out.loc[selected, "score"] = np.maximum(pd.to_numeric(out.loc[selected, "score"], errors="coerce").fillna(0.0), 0.96)
        out.loc[selected, "v2_2_mapping_action"] = action
        out.loc[selected, "v2_2_parent_onto_id"] = target_id
        out.loc[selected, "v2_2_parent_onto_label"] = target_label
        out.loc[selected, "v2_2_child_cluster_id"] = int(row.cluster_id)
        out.loc[selected, "v2_2_child_label"] = child_label

    return out


def write_guardrail_note(note_path: Path, endpoint_df: pd.DataFrame, cluster_df: pd.DataFrame, child_df: pd.DataFrame) -> None:
    endpoint_counts = endpoint_df["endpoint_guardrail_category"].value_counts()
    cluster_counts = cluster_df.loc[cluster_df["is_significant_cluster"], "cluster_guardrail_category"].value_counts()
    promoted = child_df[child_df["promote_to_v2_2"]].copy()

    lines = [
        "# Flexible Endpoint Guardrail",
        "",
        "This note adds a second-stage guardrail over the `study_subfamily_candidate` regime so that multi-cluster structure does not automatically become ontology growth.",
        "",
        "## Endpoint Guardrail Counts",
        "",
    ]
    for category, count in endpoint_counts.items():
        lines.append(f"- `{category}`: `{int(count):,}`")
    lines.extend(["", "## Significant Cluster Guardrail Counts", ""])
    for category, count in cluster_counts.items():
        lines.append(f"- `{category}`: `{int(count):,}`")
    lines.extend(
        [
            "",
            "## Child Promotion Results",
            "",
            f"- promoted or attached child clusters: `{int(len(promoted)):,}`",
            f"- new child families to add: `{int((promoted['promotion_action'] == 'promote_new_child_family').sum()):,}`",
            f"- existing ontology child attachments: `{int((promoted['promotion_action'] == 'attach_existing_ontology_child').sum()):,}`",
            f"- distinct parent endpoints with promoted children: `{int(promoted['parent_onto_label'].nunique()):,}`",
            "",
            "## Examples",
            "",
        ]
    )
    sample = promoted[
        [
            "parent_onto_label",
            "child_label",
            "promotion_action",
            "cluster_freq",
            "cluster_share",
            "promotion_reason",
        ]
    ].head(15)
    for row in sample.itertuples(index=False):
        lines.append(
            f"- `{row.parent_onto_label}` -> `{row.child_label}` | {row.promotion_action} | "
            f"freq={int(row.cluster_freq)} share={float(row.cluster_share):.3f} | {row.promotion_reason}"
        )
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_build_note(note_path: Path, ontology_rows: list[dict[str, Any]], mapping: pd.DataFrame, child_df: pd.DataFrame) -> None:
    promoted = child_df[child_df["promote_to_v2_2"]].copy()
    new_children = promoted[promoted["promotion_action"] == "promote_new_child_family"].copy()
    remapped = mapping["v2_2_mapping_action"] != "carry_forward_v2_1_mapping"
    lines = [
        "# Ontology v2.2 Guardrailed Build Note",
        "",
        f"- ontology rows: `{len(ontology_rows):,}`",
        f"- promoted child clusters: `{len(promoted):,}`",
        f"- new child ontology rows: `{len(new_children):,}`",
        f"- mapping rows remapped to child concepts: `{int(remapped.sum()):,}`",
        "",
        "## Mapping action counts",
        "",
    ]
    for action, count in mapping["v2_2_mapping_action"].value_counts().items():
        lines.append(f"- `{action}`: `{int(count):,}`")
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    guardrail_note = ROOT / args.guardrail_note
    guardrail_note.parent.mkdir(parents=True, exist_ok=True)
    child_out = ROOT / args.child_families_out
    child_out.parent.mkdir(parents=True, exist_ok=True)
    ontology_out = ROOT / args.ontology_out
    ontology_out.parent.mkdir(parents=True, exist_ok=True)
    mapping_out = ROOT / args.mapping_out
    mapping_out.parent.mkdir(parents=True, exist_ok=True)
    build_note = ROOT / args.build_note
    build_note.parent.mkdir(parents=True, exist_ok=True)

    regime = pd.read_csv(ROOT / args.regime_table)
    mapping = pd.read_parquet(ROOT / args.mapping)
    ontology_rows = json.loads((ROOT / args.ontology_json).read_text(encoding="utf-8"))

    endpoint_df, cluster_df = build_guardrail_tables(regime, mapping)
    child_df = build_child_family_candidates(endpoint_df, cluster_df, ontology_rows, mapping)
    ontology_v2_2 = build_v2_2_ontology(ontology_rows, child_df)
    mapping_v2_2 = build_mapping_v2_2(mapping, child_df)

    endpoint_df.to_csv(out_dir / "study_subfamily_guardrail.csv", index=False)
    cluster_df.to_csv(out_dir / "study_subfamily_cluster_guardrail.csv", index=False)
    child_df.to_csv(out_dir / "guardrailed_child_family_candidates.csv", index=False)

    child_df.to_parquet(child_out, index=False)
    ontology_out.write_text(json.dumps(ontology_v2_2, indent=2, ensure_ascii=False), encoding="utf-8")
    mapping_v2_2.to_parquet(mapping_out, index=False)

    write_guardrail_note(guardrail_note, endpoint_df, cluster_df, child_df)
    write_build_note(build_note, ontology_v2_2, mapping_v2_2, child_df)

    print(f"Wrote endpoint guardrail: {out_dir / 'study_subfamily_guardrail.csv'}")
    print(f"Wrote cluster guardrail: {out_dir / 'study_subfamily_cluster_guardrail.csv'}")
    print(f"Wrote child family candidates: {child_out}")
    print(f"Wrote ontology: {ontology_out}")
    print(f"Wrote mapping: {mapping_out}")


if __name__ == "__main__":
    main()
