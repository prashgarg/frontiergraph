from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_PATH = ROOT / "data/ontology_v2/ontology_v2_2_guardrailed.json"
MAPPING_PATH = ROOT / "data/ontology_v2/extraction_label_mapping_v2_2_guardrailed.parquet"
EMBEDDINGS_PATH = ROOT / "data/ontology_v2/ontology_v2_label_only_embeddings.npy"
JEL_CODES_PATH = ROOT / "data/ontology_v2/jel_codes.csv"
OPENALEX_PATH = ROOT / "data/ontology_v2/openalex_paper_keywords.parquet"

OUT_CANDIDATES = ROOT / "data/ontology_v2/parent_child_candidate_pairs_v2_2.parquet"
OUT_SUMMARY = ROOT / "data/ontology_v2/parent_child_candidate_summary_v2_2.md"

STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "to", "with", "without", "within",
}

GENERIC_TOKENS = {
    "effect", "effects", "factor", "factors", "level", "levels", "measure",
    "measures", "rate", "rates", "relationship", "relationships", "system",
    "systems", "theory", "theories", "variable", "variables",
}


def normalize_text(text: str) -> str:
    text = str(text or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    norm = normalize_text(text)
    return [tok for tok in norm.split() if tok and tok not in STOPWORDS]


def contains_generic_only(tokens: list[str]) -> bool:
    return bool(tokens) and all(tok in GENERIC_TOKENS for tok in tokens)


def load_ontology() -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    with ONTOLOGY_PATH.open() as f:
        data = json.load(f)
    rows = data["concepts"] if isinstance(data, dict) and "concepts" in data else data
    ontology = pd.DataFrame(
        [
            {
                "onto_id": row.get("id", ""),
                "onto_label": row.get("label", ""),
                "onto_source": row.get("source", ""),
                "onto_domain": row.get("domain", ""),
                "description": row.get("description", ""),
                "parent_label": row.get("parent_label", "") or "",
                "root_label": row.get("root_label", "") or "",
            }
            for row in rows
        ]
    )
    ontology["norm_label"] = ontology["onto_label"].map(normalize_text)
    ontology["token_list"] = ontology["onto_label"].map(tokenize)
    ontology["token_count"] = ontology["token_list"].map(len)
    ontology["has_parent"] = ontology["parent_label"].astype(str).str.len().gt(0)
    return ontology, rows


def build_usage_features() -> pd.DataFrame:
    mapping = pd.read_parquet(MAPPING_PATH)
    keep_cols = ["onto_id", "onto_label", "onto_source"]
    for col in ["freq", "unique_papers", "unique_edge_instances", "directed_edge_instances"]:
        if col in mapping.columns:
            keep_cols.append(col)
    mapping = mapping[keep_cols].copy()
    if "freq" not in mapping.columns:
        mapping["freq"] = 1
    for col in ["unique_papers", "unique_edge_instances", "directed_edge_instances"]:
        if col not in mapping.columns:
            mapping[col] = 0
    grouped = (
        mapping.groupby(["onto_id", "onto_label", "onto_source"], as_index=False)
        .agg(
            mapping_rows=("onto_id", "size"),
            mapped_total_freq=("freq", "sum"),
            mapped_unique_papers=("unique_papers", "max"),
            mapped_unique_edges=("unique_edge_instances", "max"),
            mapped_directed_edges=("directed_edge_instances", "max"),
        )
    )
    return grouped


def build_parent_lookup(ontology: pd.DataFrame) -> dict[str, list[dict[str, str]]]:
    lookup: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ontology.itertuples(index=False):
        lookup[row.norm_label].append(
            {
                "onto_id": row.onto_id,
                "onto_label": row.onto_label,
                "onto_source": row.onto_source,
                "onto_domain": row.onto_domain,
            }
        )
    return lookup


def choose_label_match(matches: list[dict[str, str]], preferred_sources: tuple[str, ...] = ()) -> dict[str, str] | None:
    if not matches:
        return None
    if preferred_sources:
        ranked = sorted(
            matches,
            key=lambda m: (
                preferred_sources.index(m["onto_source"]) if m["onto_source"] in preferred_sources else len(preferred_sources),
                len(m["onto_label"]),
            ),
        )
        return ranked[0]
    return sorted(matches, key=lambda m: (len(m["onto_label"]), m["onto_label"]))[0]


def derive_jel_parent_titles() -> tuple[dict[str, str], dict[str, str]]:
    jel_codes = pd.read_csv(JEL_CODES_PATH)
    jel_codes["code"] = jel_codes["code"].astype(str).str.strip()
    jel_codes["description"] = jel_codes["description"].astype(str).str.strip()
    title_map = dict(zip(jel_codes["code"], jel_codes["description"]))
    parent_map: dict[str, str] = {}
    for code in jel_codes["code"]:
        if len(code) <= 1:
            continue
        if len(code) == 2:
            parent = code[:1]
        else:
            parent = code[:-1]
        if parent in title_map:
            parent_map[code] = title_map[parent]
    return title_map, parent_map


def derive_openalex_topic_parents() -> tuple[dict[str, str], dict[str, str]]:
    topic_rows = pd.read_parquet(
        OPENALEX_PATH,
        columns=["type", "item_id", "display_name", "field", "subfield", "domain"],
    )
    topic_rows = topic_rows[topic_rows["type"] == "topic"].copy()
    topic_rows["field"] = topic_rows["field"].fillna("").astype(str)
    topic_rows["subfield"] = topic_rows["subfield"].fillna("").astype(str)
    grouped = (
        topic_rows.groupby("item_id", as_index=False)
        .agg(
            display_name=("display_name", "first"),
            field=("field", "first"),
            subfield=("subfield", "first"),
            domain=("domain", "first"),
        )
    )
    subfield_parent = {}
    field_parent = {}
    for row in grouped.itertuples(index=False):
        if row.subfield:
            subfield_parent[row.item_id] = row.subfield
        if row.field:
            field_parent[row.item_id] = row.field
    return subfield_parent, field_parent


def build_structured_candidates(
    ontology: pd.DataFrame,
    parent_lookup: dict[str, list[dict[str, str]]],
) -> pd.DataFrame:
    jel_titles, jel_parent_titles = derive_jel_parent_titles()
    openalex_subfield, openalex_field = derive_openalex_topic_parents()
    records: list[dict[str, Any]] = []

    for row in ontology.itertuples(index=False):
        # Existing inherited parent label in ontology
        if row.parent_label:
            norm_parent = normalize_text(row.parent_label)
            match = choose_label_match(parent_lookup.get(norm_parent, []))
            records.append(
                {
                    "child_id": row.onto_id,
                    "child_label": row.onto_label,
                    "child_source": row.onto_source,
                    "candidate_parent_id": match["onto_id"] if match else "",
                    "candidate_parent_label": match["onto_label"] if match else row.parent_label,
                    "candidate_parent_source": match["onto_source"] if match else "",
                    "candidate_parent_domain": match["onto_domain"] if match else "",
                    "candidate_channel": "existing_parent_label",
                    "channel_rank": 1,
                    "structured_edge_type": "existing_parent_label",
                    "external_parent_label": row.parent_label,
                    "external_parent_code": "",
                    "confidence_prior": "weak",
                }
            )

        # JEL code hierarchy
        if row.onto_source == "jel" and row.onto_id.startswith("jel:"):
            parts = row.onto_id.split(":", 2)
            if len(parts) >= 3:
                code = parts[1]
                if code in jel_parent_titles:
                    parent_label = jel_parent_titles[code]
                    norm_parent = normalize_text(parent_label)
                    match = choose_label_match(parent_lookup.get(norm_parent, []), preferred_sources=("jel", "openalex_topic", "openalex_keyword", "wikipedia"))
                    records.append(
                        {
                            "child_id": row.onto_id,
                            "child_label": row.onto_label,
                            "child_source": row.onto_source,
                            "candidate_parent_id": match["onto_id"] if match else "",
                            "candidate_parent_label": match["onto_label"] if match else parent_label,
                            "candidate_parent_source": match["onto_source"] if match else "",
                            "candidate_parent_domain": match["onto_domain"] if match else "",
                            "candidate_channel": "jel_code_hierarchy",
                            "channel_rank": 1,
                            "structured_edge_type": "jel_code_parent",
                            "external_parent_label": parent_label,
                            "external_parent_code": code[:-1] if len(code) > 1 else "",
                            "confidence_prior": "strong",
                        }
                    )

        # OpenAlex topic hierarchy
        if row.onto_source == "openalex_topic":
            if row.onto_id in openalex_subfield:
                parent_label = openalex_subfield[row.onto_id]
                norm_parent = normalize_text(parent_label)
                match = choose_label_match(parent_lookup.get(norm_parent, []), preferred_sources=("openalex_topic", "jel", "openalex_keyword", "wikipedia"))
                records.append(
                    {
                        "child_id": row.onto_id,
                        "child_label": row.onto_label,
                        "child_source": row.onto_source,
                        "candidate_parent_id": match["onto_id"] if match else "",
                        "candidate_parent_label": match["onto_label"] if match else parent_label,
                        "candidate_parent_source": match["onto_source"] if match else "",
                        "candidate_parent_domain": match["onto_domain"] if match else "",
                        "candidate_channel": "openalex_topic_subfield",
                        "channel_rank": 1,
                        "structured_edge_type": "openalex_topic_subfield",
                        "external_parent_label": parent_label,
                        "external_parent_code": "",
                        "confidence_prior": "strong",
                    }
                )
            if row.onto_id in openalex_field:
                parent_label = openalex_field[row.onto_id]
                norm_parent = normalize_text(parent_label)
                match = choose_label_match(parent_lookup.get(norm_parent, []), preferred_sources=("openalex_topic", "jel", "openalex_keyword", "wikipedia"))
                records.append(
                    {
                        "child_id": row.onto_id,
                        "child_label": row.onto_label,
                        "child_source": row.onto_source,
                        "candidate_parent_id": match["onto_id"] if match else "",
                        "candidate_parent_label": match["onto_label"] if match else parent_label,
                        "candidate_parent_source": match["onto_source"] if match else "",
                        "candidate_parent_domain": match["onto_domain"] if match else "",
                        "candidate_channel": "openalex_topic_field",
                        "channel_rank": 2,
                        "structured_edge_type": "openalex_topic_field",
                        "external_parent_label": parent_label,
                        "external_parent_code": "",
                        "confidence_prior": "strong",
                    }
                )

    return pd.DataFrame.from_records(records)


def lexical_candidate_rows(
    ontology: pd.DataFrame,
    usage: pd.DataFrame,
    parent_lookup: dict[str, list[dict[str, str]]],
) -> pd.DataFrame:
    usage_lookup = usage.set_index("onto_id").to_dict("index")
    records: list[dict[str, Any]] = []
    for row in ontology.itertuples(index=False):
        tokens = list(row.token_list)
        if len(tokens) <= 1:
            continue
        seen_ids: set[str] = set()
        ranked: list[tuple[float, dict[str, str]]] = []
        for size in range(max(1, len(tokens) - 2), len(tokens)):
            for start in range(0, len(tokens) - size + 1):
                span = " ".join(tokens[start : start + size])
                if contains_generic_only(span.split()):
                    continue
                for match in parent_lookup.get(span, []):
                    if match["onto_id"] == row.onto_id:
                        continue
                    cand_tokens = tokenize(match["onto_label"])
                    if len(cand_tokens) >= row.token_count:
                        continue
                    if not cand_tokens or not set(cand_tokens).issubset(set(tokens)):
                        continue
                    support = usage_lookup.get(match["onto_id"], {}).get("mapped_total_freq", 0)
                    score = len(cand_tokens) / max(1, len(tokens)) + math.log1p(float(support)) / 20.0
                    ranked.append((score, match))
        ranked.sort(key=lambda x: x[0], reverse=True)
        kept = 0
        for score, cand in ranked:
            if cand["onto_id"] in seen_ids:
                continue
            seen_ids.add(cand["onto_id"])
            kept += 1
            records.append(
                {
                    "child_id": row.onto_id,
                    "child_label": row.onto_label,
                    "child_source": row.onto_source,
                    "candidate_parent_id": cand["onto_id"],
                    "candidate_parent_label": cand["onto_label"],
                    "candidate_parent_source": cand["onto_source"],
                    "candidate_parent_domain": cand["onto_domain"],
                    "candidate_channel": "lexical_ngram_parent",
                    "channel_rank": kept,
                    "lexical_parent_score": float(score),
                    "confidence_prior": "medium",
                }
            )
            if kept >= 4:
                break
    return pd.DataFrame.from_records(records)


def build_extended_embeddings(ontology: pd.DataFrame) -> np.ndarray:
    base = np.load(EMBEDDINGS_PATH)
    if len(ontology) <= len(base):
        return base[: len(ontology)]
    extra = len(ontology) - len(base)
    dim = base.shape[1]
    # For appended reviewed-family/child-family concepts we do a local lexical fallback.
    # They are few enough that the exact semantic quality here is not the main bottleneck.
    vocab = {}
    base_labels = [normalize_text(x) for x in ontology["onto_label"].iloc[: len(base)].tolist()]
    for label in base_labels:
        for tok in label.split():
            vocab.setdefault(tok, len(vocab))
    extra_arr = np.zeros((extra, dim), dtype=np.float32)
    for i, label in enumerate(ontology["onto_label"].iloc[len(base) :].tolist()):
        toks = tokenize(label)
        if not toks:
            continue
        vec = np.zeros(dim, dtype=np.float32)
        for tok in toks:
            h = hash(tok) % dim
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        extra_arr[i] = vec
    return np.vstack([base, extra_arr])


def semantic_candidate_rows(ontology: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    embeddings = build_extended_embeddings(ontology).astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    use_lookup = usage.set_index("onto_id").to_dict("index")
    top_k = 18
    batch = 4096
    records: list[dict[str, Any]] = []

    labels = ontology["onto_label"].tolist()
    ids = ontology["onto_id"].tolist()
    sources = ontology["onto_source"].tolist()
    domains = ontology["onto_domain"].tolist()
    token_counts = ontology["token_count"].tolist()
    token_lists = ontology["token_list"].tolist()

    for start in range(0, len(ontology), batch):
        q = embeddings[start : start + batch]
        sims, idxs = index.search(q, top_k)
        for offset, child_idx in enumerate(range(start, min(start + batch, len(ontology)))):
            child_tokens = set(token_lists[child_idx])
            child_support = use_lookup.get(ids[child_idx], {}).get("mapped_total_freq", 0)
            kept = 0
            for sim, cand_idx in zip(sims[offset], idxs[offset]):
                if cand_idx < 0 or cand_idx == child_idx:
                    continue
                if token_counts[cand_idx] >= token_counts[child_idx]:
                    continue
                parent_tokens = set(token_lists[cand_idx])
                if not parent_tokens:
                    continue
                shared = len(child_tokens & parent_tokens)
                if shared == 0 and sim < 0.78:
                    continue
                parent_support = use_lookup.get(ids[cand_idx], {}).get("mapped_total_freq", 0)
                support_ratio = (parent_support + 1) / (child_support + 1)
                if support_ratio < 0.5 and sim < 0.9:
                    continue
                kept += 1
                records.append(
                    {
                        "child_id": ids[child_idx],
                        "child_label": labels[child_idx],
                        "child_source": sources[child_idx],
                        "candidate_parent_id": ids[cand_idx],
                        "candidate_parent_label": labels[cand_idx],
                        "candidate_parent_source": sources[cand_idx],
                        "candidate_parent_domain": domains[cand_idx],
                        "candidate_channel": "semantic_broader_neighbor",
                        "channel_rank": kept,
                        "semantic_cosine": float(sim),
                        "shared_token_count": shared,
                        "support_ratio": float(support_ratio),
                        "confidence_prior": "medium",
                    }
                )
                if kept >= 4:
                    break
    return pd.DataFrame.from_records(records)


def add_usage_and_flags(candidates: pd.DataFrame, ontology: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    child_domain_lookup = ontology.set_index("onto_id")["onto_domain"].to_dict()
    ontology_flags = ontology[["onto_id", "has_parent", "parent_label", "root_label", "token_count", "norm_label"]].rename(
        columns={
            "onto_id": "child_id",
            "has_parent": "child_current_has_parent",
            "parent_label": "child_current_parent_label",
            "root_label": "child_current_root_label",
            "token_count": "child_token_count",
            "norm_label": "child_norm_label",
        }
    )
    out = candidates.merge(ontology_flags, on="child_id", how="left")
    parent_flags = ontology[["onto_id", "has_parent", "token_count", "norm_label"]].rename(
        columns={
            "onto_id": "candidate_parent_id",
            "has_parent": "parent_has_parent",
            "token_count": "parent_token_count",
            "norm_label": "parent_norm_label",
        }
    )
    out = out.merge(parent_flags, on="candidate_parent_id", how="left")

    child_usage = usage.rename(
        columns={
            "onto_id": "child_id",
            "mapping_rows": "child_mapping_rows",
            "mapped_total_freq": "child_mapped_total_freq",
            "mapped_unique_papers": "child_mapped_unique_papers",
            "mapped_unique_edges": "child_mapped_unique_edges",
            "mapped_directed_edges": "child_mapped_directed_edges",
        }
    )
    out = out.merge(child_usage.drop(columns=["onto_label", "onto_source"]), on="child_id", how="left")
    parent_usage = usage.rename(
        columns={
            "onto_id": "candidate_parent_id",
            "mapping_rows": "parent_mapping_rows",
            "mapped_total_freq": "parent_mapped_total_freq",
            "mapped_unique_papers": "parent_mapped_unique_papers",
            "mapped_unique_edges": "parent_mapped_unique_edges",
            "mapped_directed_edges": "parent_mapped_directed_edges",
        }
    )
    out = out.merge(parent_usage.drop(columns=["onto_label", "onto_source"]), on="candidate_parent_id", how="left")

    for col in [
        "child_mapping_rows",
        "child_mapped_total_freq",
        "child_mapped_unique_papers",
        "child_mapped_unique_edges",
        "child_mapped_directed_edges",
        "parent_mapping_rows",
        "parent_mapped_total_freq",
        "parent_mapped_unique_papers",
        "parent_mapped_unique_edges",
        "parent_mapped_directed_edges",
    ]:
        out[col] = out[col].fillna(0)

    out["parent_exists_in_ontology"] = out["candidate_parent_id"].astype(str).str.len().gt(0)
    out["same_source_pair"] = out["child_source"] == out["candidate_parent_source"]
    out["child_domain"] = out["child_id"].map(child_domain_lookup).fillna("")
    out["same_domain_pair"] = out["candidate_parent_domain"].fillna("") == out["child_domain"]
    out["token_drop"] = out["child_token_count"].fillna(0) - out["parent_token_count"].fillna(0)
    out["candidate_pair_key"] = out["child_id"].astype(str) + "->" + out["candidate_parent_id"].astype(str) + "|" + out["candidate_channel"].astype(str)
    return out


def dedupe_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    channel_priority = {
        "jel_code_hierarchy": 1,
        "openalex_topic_subfield": 1,
        "openalex_topic_field": 2,
        "existing_parent_label": 3,
        "lexical_ngram_parent": 4,
        "semantic_broader_neighbor": 5,
    }
    candidates = candidates.copy()
    candidates["channel_priority"] = candidates["candidate_channel"].map(channel_priority).fillna(99)
    candidates = candidates.sort_values(
        ["child_id", "candidate_parent_id", "channel_priority", "channel_rank"],
        ascending=[True, True, True, True],
    )
    return candidates.drop_duplicates(["child_id", "candidate_parent_id", "candidate_channel"])


def write_summary(path: Path, ontology: pd.DataFrame, candidates: pd.DataFrame) -> None:
    used_without_parent = int(((ontology["onto_id"].isin(candidates["child_id"])) & (~ontology["has_parent"])).sum())
    by_channel = candidates["candidate_channel"].value_counts().to_dict()
    structured = candidates[candidates["candidate_channel"].isin({"jel_code_hierarchy", "openalex_topic_subfield", "openalex_topic_field", "existing_parent_label"})]
    lines = [
        "# Parent-Child Candidate Pass v2.2",
        "",
        "This file summarizes the first full candidate-generation pass for ontology parent-child relations.",
        "",
        "## Scope",
        "",
        f"- ontology concepts considered: `{len(ontology):,}`",
        f"- concepts with existing parent labels: `{int(ontology['has_parent'].sum()):,}`",
        f"- concepts without parents: `{int((~ontology['has_parent']).sum()):,}`",
        "",
        "## Candidate Channels",
        "",
    ]
    for channel, count in sorted(by_channel.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- `{channel}`: `{count:,}`")
    lines.extend(
        [
            "",
            "## Structured Signals",
            "",
            f"- structured candidate rows: `{len(structured):,}`",
            f"- structured rows with ontology-resolved parent ids: `{int(structured['parent_exists_in_ontology'].sum()):,}`",
            f"- existing inherited parent-label rows: `{int((candidates['candidate_channel'] == 'existing_parent_label').sum()):,}`",
            f"- JEL code-hierarchy rows: `{int((candidates['candidate_channel'] == 'jel_code_hierarchy').sum()):,}`",
            f"- OpenAlex topic subfield rows: `{int((candidates['candidate_channel'] == 'openalex_topic_subfield').sum()):,}`",
            f"- OpenAlex topic field rows: `{int((candidates['candidate_channel'] == 'openalex_topic_field').sum()):,}`",
            "",
            "## Notes",
            "",
            "- JEL and OpenAlex topic hierarchy signals are imported as structured candidates rather than left implicit.",
            "- Existing parent labels, mostly from Wikidata and reviewed family nodes, are treated as weak priors rather than ground truth.",
            "- Semantic candidates use ontology label embeddings where available and a local lexical fallback for appended reviewed-family nodes.",
            "- Lexical candidates are generated from shorter contiguous label spans and filtered to avoid generic one-word parents when possible.",
        ]
    )
    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full-ontology parent-child candidate pairs for v2.2.")
    parser.add_argument("--out-candidates", default=str(OUT_CANDIDATES))
    parser.add_argument("--out-summary", default=str(OUT_SUMMARY))
    args = parser.parse_args()

    ontology, _ = load_ontology()
    usage = build_usage_features()
    parent_lookup = build_parent_lookup(ontology)

    print("[parent-child] building structured candidates...", flush=True)
    structured = build_structured_candidates(ontology, parent_lookup)
    print("[parent-child] building lexical candidates...", flush=True)
    lexical = lexical_candidate_rows(ontology, usage, parent_lookup)
    print("[parent-child] building semantic candidates...", flush=True)
    semantic = semantic_candidate_rows(ontology, usage)

    candidates = pd.concat([structured, lexical, semantic], ignore_index=True, sort=False)
    candidates = dedupe_candidates(candidates)
    candidates = add_usage_and_flags(candidates, ontology, usage)
    candidates = candidates.sort_values(["child_id", "channel_priority", "channel_rank", "candidate_parent_label"], ascending=[True, True, True, True])

    out_candidates = Path(args.out_candidates)
    out_candidates.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_parquet(out_candidates, index=False)

    out_summary = Path(args.out_summary)
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    write_summary(out_summary, ontology, candidates)

    print(f"Wrote candidates: {out_candidates}")
    print(f"Wrote summary: {out_summary}")
    print(f"Candidate rows: {len(candidates):,}")


if __name__ == "__main__":
    main()
