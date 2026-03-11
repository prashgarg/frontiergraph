from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.explain import build_explanation_tables
from src.features_motifs import compute_motif_features
from src.features_pairs import compute_underexplored_pairs
from src.features_paths import compute_path_features
from src.scoring import compute_candidate_scores
from src.utils import build_corpus_df, ensure_dir


DEFAULT_EXTRACTION_DB = (
    "data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite"
)
DEFAULT_ONTOLOGY_DB = "data/production/frontiergraph_ontology_v3/ontology_v3.sqlite"
DEFAULT_OUTPUT_ROOT = "data/production/frontiergraph_concept_v3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build strict and exploratory concept graph/app outputs from ontology v3.")
    parser.add_argument("--extraction-db", default=DEFAULT_EXTRACTION_DB)
    parser.add_argument("--ontology-db", default=DEFAULT_ONTOLOGY_DB)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def norm_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded if str(item).strip()]


def top_counts(values: list[str], limit: int = 3) -> list[dict[str, Any]]:
    counter = Counter(values)
    return [{"value": key, "count": int(count)} for key, count in counter.most_common(limit)]


def dominant_value(values: list[str], default: str = "unspecified") -> str:
    values = [v for v in values if v and v != "NA"]
    if not values:
        return default
    return Counter(values).most_common(1)[0][0]


def derive_weight(group: pd.DataFrame) -> float:
    base = float(len(group))
    if bool(group["uses_data"].fillna(0).astype(int).max()):
        base += 0.25
    if group["causal_presentation"].isin(["explicit_causal", "implicit_causal"]).any():
        base += 0.25
    if group["statistical_significance"].eq("significant").any():
        base += 0.10
    if (~group["evidence_method"].isin(["do_not_know", "other"])).any():
        base += 0.10
    return base


def derive_stability_row(row: pd.Series) -> float:
    claim_base = {
        "effect_present": 0.95,
        "conditional_effect": 0.82,
        "mixed_or_ambiguous": 0.62,
        "no_effect": 0.55,
        "question_only": 0.22,
        "other": 0.40,
    }.get(str(row.get("claim_status", "")), 0.40)
    explicitness_adj = {
        "result_only": 0.08,
        "question_and_result": 0.04,
        "background_claim": -0.18,
        "implied": -0.05,
        "question_only": -0.10,
    }.get(str(row.get("explicitness", "")), 0.0)
    tent_adj = {
        "certain": 0.05,
        "tentative": -0.05,
        "mixed_or_qualified": -0.08,
        "unclear": -0.10,
    }.get(str(row.get("tentativeness", "")), 0.0)
    causal_adj = {
        "explicit_causal": 0.05,
        "implicit_causal": 0.02,
        "noncausal": 0.0,
        "unclear": -0.03,
    }.get(str(row.get("causal_presentation", "")), 0.0)
    score = claim_base + explicitness_adj + tent_adj + causal_adj
    return float(max(0.0, min(1.0, score)))


def load_frames(
    extraction_db: Path,
    ontology_db: Path,
    mapping_table: str,
    mapping_variant: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    econ = sqlite3.connect(extraction_db)
    onto = sqlite3.connect(ontology_db)
    try:
        works = pd.read_sql_query(
            """
            SELECT custom_id, openalex_work_id, title, publication_year, bucket, source_display_name
            FROM works
            """,
            econ,
        )
        nodes = pd.read_sql_query(
            """
            SELECT custom_id, node_id, label, surface_forms_json, unit_of_analysis_json, start_year_json,
                   end_year_json, countries_json, context_note
            FROM nodes
            """,
            econ,
        )
        edges = pd.read_sql_query(
            """
            SELECT custom_id, edge_id, source_node_id, target_node_id, directionality, relationship_type,
                   causal_presentation, edge_role, claim_status, explicitness, condition_or_scope_text,
                   claim_text, evidence_text, sign, effect_size, statistical_significance,
                   evidence_method, evidence_method_other_description, nature_of_evidence, uses_data,
                   sources_of_exogenous_variation, tentativeness
            FROM edges
            """,
            econ,
        )
        mappings = pd.read_sql_query(
            f"""
            SELECT m.custom_id, m.node_id, m.normalized_label, m.concept_id, m.mapping_source, m.confidence,
                   hc.preferred_label AS concept_label, hc.aliases_json, hc.instance_support,
                   hc.distinct_paper_support, hc.review_status
            FROM {mapping_table} m
            LEFT JOIN head_concepts hc ON hc.concept_id = m.concept_id
            """,
            onto,
        )
        context_table = "context_fingerprints_hard" if mapping_variant == "hard" else "context_fingerprints_soft"
        contexts = pd.read_sql_query(
            f"""
            SELECT concept_id, context_fingerprint, count_support, countries_json, unit_of_analysis_json,
                   year_range_json, context_notes_json
            FROM {context_table}
            """,
            onto,
        )
    finally:
        econ.close()
        onto.close()
    return works, nodes, edges, mappings, contexts


def build_concept_frames(
    works: pd.DataFrame,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    mappings: pd.DataFrame,
    contexts: pd.DataFrame,
    mapping_variant: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    node_map = mappings[mappings["concept_id"].notna()].copy()
    mapped_nodes = nodes.merge(node_map, how="inner", on=["custom_id", "node_id"])
    mapped_nodes = mapped_nodes.merge(works, how="left", on="custom_id")

    src_nodes = mapped_nodes.rename(
        columns={
            "node_id": "source_node_id",
            "concept_id": "source_concept_id",
            "concept_label": "source_concept_label",
            "countries_json": "source_countries_json",
            "unit_of_analysis_json": "source_units_json",
            "context_note": "source_context_note",
        }
    )
    dst_nodes = mapped_nodes.rename(
        columns={
            "node_id": "target_node_id",
            "concept_id": "target_concept_id",
            "concept_label": "target_concept_label",
            "countries_json": "target_countries_json",
            "unit_of_analysis_json": "target_units_json",
            "context_note": "target_context_note",
        }
    )

    concept_edge_instances = (
        edges.merge(
            src_nodes[
                [
                    "custom_id",
                    "source_node_id",
                    "source_concept_id",
                    "source_concept_label",
                    "source_countries_json",
                    "source_units_json",
                    "source_context_note",
                ]
            ],
            how="inner",
            on=["custom_id", "source_node_id"],
        )
        .merge(
            dst_nodes[
                [
                    "custom_id",
                    "target_node_id",
                    "target_concept_id",
                    "target_concept_label",
                    "target_countries_json",
                    "target_units_json",
                    "target_context_note",
                ]
            ],
            how="inner",
            on=["custom_id", "target_node_id"],
        )
        .merge(works, how="left", on="custom_id")
    )
    concept_edge_instances = concept_edge_instances[
        concept_edge_instances["source_concept_id"] != concept_edge_instances["target_concept_id"]
    ].copy()
    concept_edge_instances["derived_stability"] = concept_edge_instances.apply(derive_stability_row, axis=1)

    concept_nodes = (
        mapped_nodes.groupby(["concept_id", "concept_label"], as_index=False)
        .agg(
            instance_support=("node_id", "size"),
            distinct_paper_support=("custom_id", "nunique"),
            mean_confidence=("confidence", "mean"),
            low_confidence_share=("confidence", lambda s: float((pd.to_numeric(s, errors="coerce").fillna(0.0) < 0.80).mean())),
            mapping_sources_json=("mapping_source", lambda s: json.dumps(top_counts([str(v) for v in s if v], limit=5), ensure_ascii=False)),
            source_bucket_values=("bucket", lambda s: json.dumps(top_counts([str(v) for v in s if v], limit=3), ensure_ascii=False)),
            top_countries=("countries_json", lambda s: json.dumps(top_counts([c for value in s for c in norm_json_list(value)], limit=3), ensure_ascii=False)),
            top_units=("unit_of_analysis_json", lambda s: json.dumps(top_counts([u for value in s for u in norm_json_list(value)], limit=3), ensure_ascii=False)),
            representative_contexts=("context_note", lambda s: json.dumps(top_counts([str(v) for v in s if v and v != "NA"], limit=3), ensure_ascii=False)),
            aliases_json=("label", lambda s: json.dumps(sorted(set(str(v) for v in s if str(v).strip())), ensure_ascii=False)),
        )
        .rename(columns={"concept_id": "code", "concept_label": "label"})
    )

    context_lookup = (
        contexts.sort_values(["concept_id", "count_support"], ascending=[True, False])
        .groupby("concept_id", as_index=False)
        .head(3)
        .groupby("concept_id")
        .agg(
            representative_contexts_json=("context_notes_json", lambda s: json.dumps([json.loads(v) for v in s if v], ensure_ascii=False)),
            representative_years_json=("year_range_json", lambda s: json.dumps([json.loads(v) for v in s if v], ensure_ascii=False)),
        )
        .reset_index()
    )
    concept_nodes = concept_nodes.merge(context_lookup, how="left", left_on="code", right_on="concept_id").drop(columns=["concept_id"], errors="ignore")
    concept_nodes["bucket_hint"] = concept_nodes["source_bucket_values"].apply(
        lambda value: json.loads(value)[0]["value"] if value and json.loads(value) else "mixed"
    )
    concept_nodes["mapping_variant"] = mapping_variant

    grouped_edges = []
    grouped = concept_edge_instances.groupby(["custom_id", "source_concept_id", "target_concept_id"], sort=False)
    for (custom_id, source_concept_id, target_concept_id), group in grouped:
        first = group.iloc[0]
        grouped_edges.append(
            {
                "paper_id": custom_id,
                "year": int(first["publication_year"] or 0),
                "title": str(first["title"] or ""),
                "authors": "",
                "venue": str(first["source_display_name"] or ""),
                "source": str(first["bucket"] or ""),
                "src_code": str(source_concept_id),
                "dst_code": str(target_concept_id),
                "relation_type": dominant_value(group["relationship_type"].astype(str).tolist(), default="other"),
                "evidence_type": dominant_value(group["evidence_method"].astype(str).tolist(), default="do_not_know"),
                "is_causal": bool(group["causal_presentation"].isin(["explicit_causal", "implicit_causal"]).any()),
                "weight": derive_weight(group),
                "stability": float(group["derived_stability"].mean()),
            }
        )
    concept_edges_for_corpus = pd.DataFrame(grouped_edges)
    papers_df = (
        works.rename(
            columns={
                "custom_id": "paper_id",
                "publication_year": "year",
                "source_display_name": "venue",
                "bucket": "source",
            }
        )[["paper_id", "year", "title", "venue", "source"]]
        .assign(authors="")
        .drop_duplicates(subset=["paper_id"])
    )
    nodes_df = concept_nodes[["code", "label"]].drop_duplicates(subset=["code"])
    corpus_df = build_corpus_df(nodes_df, papers_df, concept_edges_for_corpus)
    return concept_nodes, concept_edge_instances, concept_edges_for_corpus, corpus_df


def build_concept_graph_outputs(concept_edge_instances: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    concept_edges = (
        concept_edge_instances.groupby(["source_concept_id", "target_concept_id"], as_index=False)
        .agg(
            support_count=("edge_id", "size"),
            distinct_papers=("custom_id", "nunique"),
            avg_stability=("derived_stability", "mean"),
        )
    )

    profile_rows = []
    context_rows = []
    exemplar_rows = []
    for (source_concept_id, target_concept_id), group in concept_edge_instances.groupby(["source_concept_id", "target_concept_id"], sort=False):
        profile_rows.append(
            {
                "source_concept_id": source_concept_id,
                "target_concept_id": target_concept_id,
                "directionality_json": json.dumps(Counter(group["directionality"].astype(str)).most_common(), ensure_ascii=False),
                "relationship_type_json": json.dumps(Counter(group["relationship_type"].astype(str)).most_common(), ensure_ascii=False),
                "causal_presentation_json": json.dumps(Counter(group["causal_presentation"].astype(str)).most_common(), ensure_ascii=False),
                "edge_role_json": json.dumps(Counter(group["edge_role"].astype(str)).most_common(), ensure_ascii=False),
                "claim_status_json": json.dumps(Counter(group["claim_status"].astype(str)).most_common(), ensure_ascii=False),
            }
        )
        countries: list[str] = []
        units: list[str] = []
        for value in group["source_countries_json"]:
            countries.extend(norm_json_list(value))
        for value in group["target_countries_json"]:
            countries.extend(norm_json_list(value))
        for value in group["source_units_json"]:
            units.extend(norm_json_list(value))
        for value in group["target_units_json"]:
            units.extend(norm_json_list(value))
        context_rows.append(
            {
                "source_concept_id": source_concept_id,
                "target_concept_id": target_concept_id,
                "dominant_countries_json": json.dumps(top_counts(countries, limit=5), ensure_ascii=False),
                "dominant_units_json": json.dumps(top_counts(units, limit=5), ensure_ascii=False),
                "dominant_years_json": json.dumps(top_counts([str(y) for y in group["publication_year"].dropna().astype(int)], limit=5), ensure_ascii=False),
                "context_note_examples_json": json.dumps(
                    top_counts(
                        [
                            str(v)
                            for v in list(group["source_context_note"].fillna("")) + list(group["target_context_note"].fillna(""))
                            if v and v != "NA"
                        ],
                        limit=5,
                    ),
                    ensure_ascii=False,
                ),
            }
        )
        exemplar_subset = (
            group[["custom_id", "title", "publication_year", "bucket", "evidence_text"]]
            .drop_duplicates(subset=["custom_id"])
            .sort_values(["publication_year", "custom_id"], ascending=[False, True])
            .head(5)
        )
        for rank, row in enumerate(exemplar_subset.itertuples(index=False), start=1):
            exemplar_rows.append(
                {
                    "source_concept_id": source_concept_id,
                    "target_concept_id": target_concept_id,
                    "rank": rank,
                    "paper_id": row.custom_id,
                    "title": row.title,
                    "year": int(row.publication_year or 0),
                    "bucket": row.bucket,
                    "evidence_text": row.evidence_text,
                }
            )

    return concept_edges, pd.DataFrame(profile_rows), pd.DataFrame(context_rows), pd.DataFrame(exemplar_rows)


def build_concept_app_db(
    concept_nodes: pd.DataFrame,
    corpus_df: pd.DataFrame,
    concept_edges_for_corpus: pd.DataFrame,
    concept_edges: pd.DataFrame,
    concept_edge_profiles: pd.DataFrame,
    concept_edge_contexts: pd.DataFrame,
    concept_edge_exemplars: pd.DataFrame,
    output_root: Path,
    view_name: str,
    app_mode: str,
    ontology_version: str,
) -> tuple[Path, dict[str, int]]:
    artifact_root = output_root / "artifacts" / view_name
    ensure_dir(artifact_root)
    corpus_path = artifact_root / f"concept_corpus_{view_name}.parquet"
    pairs_path = artifact_root / f"concept_pairs_{view_name}.parquet"
    paths_path = artifact_root / f"concept_paths_{view_name}.parquet"
    motifs_path = artifact_root / f"concept_motifs_{view_name}.parquet"
    candidates_path = artifact_root / f"concept_candidates_{view_name}.parquet"
    app_db_path = output_root / f"concept_{view_name}_app.sqlite"

    corpus_df.to_parquet(corpus_path, index=False)
    pairs_df = compute_underexplored_pairs(corpus_df, tau=2)
    paths_df = compute_path_features(corpus_df, max_len=2, top_k_paths=10, top_k_mediators=10, max_neighbors_per_mediator=150)
    motifs_df = compute_motif_features(corpus_df, top_k_mediators=10, max_neighbors_per_mediator=150)
    candidates_df = compute_candidate_scores(pairs_df, paths_df, motifs_df)
    explanation_tables = build_explanation_tables(corpus_df, candidates_df, top_k_papers_per_edge=3)

    pairs_df.to_parquet(pairs_path, index=False)
    paths_df.to_parquet(paths_path, index=False)
    motifs_df.to_parquet(motifs_path, index=False)
    candidates_df.to_parquet(candidates_path, index=False)

    node_details = concept_nodes.rename(
        columns={
            "code": "concept_id",
            "label": "preferred_label",
            "source_bucket_values": "bucket_profile_json",
        }
    )[
        [
            "concept_id",
            "preferred_label",
            "aliases_json",
            "instance_support",
            "distinct_paper_support",
            "mean_confidence",
            "low_confidence_share",
            "mapping_sources_json",
            "bucket_profile_json",
            "bucket_hint",
            "top_countries",
            "top_units",
            "representative_contexts_json",
            "representative_years_json",
            "mapping_variant",
        ]
    ]

    candidates_aug = candidates_df.merge(
        node_details.add_prefix("u_"),
        how="left",
        left_on="u",
        right_on="u_concept_id",
    ).merge(
        node_details.add_prefix("v_"),
        how="left",
        left_on="v",
        right_on="v_concept_id",
    )

    if app_db_path.exists():
        app_db_path.unlink()
    conn = sqlite3.connect(app_db_path)
    try:
        concept_nodes[["code", "label", "bucket_hint"]].to_sql("nodes", conn, if_exists="replace", index=False)
        corpus_df[["paper_id", "year", "title", "authors", "venue", "source"]].drop_duplicates(subset=["paper_id"]).to_sql(
            "papers", conn, if_exists="replace", index=False
        )
        concept_edges_for_corpus[
            ["paper_id", "year", "src_code", "dst_code", "relation_type", "evidence_type", "is_causal", "weight", "stability"]
        ].to_sql("edges", conn, if_exists="replace", index=False)
        candidates_aug.to_sql("candidates", conn, if_exists="replace", index=False)
        pairs_df.to_sql("underexplored_pairs", conn, if_exists="replace", index=False)
        explanation_tables["candidate_mediators"].to_sql("candidate_mediators", conn, if_exists="replace", index=False)
        explanation_tables["candidate_paths"].to_sql("candidate_paths", conn, if_exists="replace", index=False)
        explanation_tables["candidate_supporting_papers"].to_sql("candidate_papers", conn, if_exists="replace", index=False)
        explanation_tables["candidate_neighborhoods"].to_sql("candidate_neighborhoods", conn, if_exists="replace", index=False)
        explanation_tables["candidate_supporting_papers"].to_sql("candidate_supporting_papers", conn, if_exists="replace", index=False)
        node_details.to_sql("node_details", conn, if_exists="replace", index=False)
        concept_edges.to_sql("concept_edges", conn, if_exists="replace", index=False)
        concept_edge_profiles.to_sql("concept_edge_profiles", conn, if_exists="replace", index=False)
        concept_edge_contexts.to_sql("concept_edge_contexts", conn, if_exists="replace", index=False)
        concept_edge_exemplars.to_sql("concept_edge_exemplars", conn, if_exists="replace", index=False)
        pd.DataFrame(
            [
                {"key": "app_mode", "value": app_mode},
                {"key": "ontology_version", "value": ontology_version},
                {"key": "graph_view", "value": view_name},
            ]
        ).to_sql("app_meta", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_code ON nodes(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_u ON candidates(u)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_v ON candidates(v)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_score ON candidates(score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_node_details_concept ON node_details(concept_id)")
        conn.commit()
    finally:
        conn.close()

    return app_db_path, {
        "corpus_rows": int(len(corpus_df)),
        "candidate_rows": int(len(candidates_df)),
        "concept_nodes": int(len(concept_nodes)),
        "concept_edges": int(len(concept_edges)),
    }


def build_view(
    extraction_db: Path,
    ontology_db: Path,
    output_root: Path,
    mapping_table: str,
    mapping_variant: str,
    app_mode: str,
    ontology_version: str,
) -> dict[str, Any]:
    works, nodes, edges, mappings, contexts = load_frames(
        extraction_db=extraction_db,
        ontology_db=ontology_db,
        mapping_table=mapping_table,
        mapping_variant=mapping_variant,
    )
    concept_nodes, concept_edge_instances, concept_edges_for_corpus, corpus_df = build_concept_frames(
        works=works,
        nodes=nodes,
        edges=edges,
        mappings=mappings,
        contexts=contexts,
        mapping_variant=mapping_variant,
    )
    concept_edges, concept_edge_profiles, concept_edge_contexts, concept_edge_exemplars = build_concept_graph_outputs(concept_edge_instances)

    graph_db_path = output_root / f"concept_graph_{mapping_variant}.sqlite"
    if graph_db_path.exists():
        graph_db_path.unlink()
    graph_conn = sqlite3.connect(graph_db_path)
    try:
        concept_nodes.to_sql("concept_nodes", graph_conn, if_exists="replace", index=False)
        concept_edge_instances.to_sql("concept_edge_instances", graph_conn, if_exists="replace", index=False)
        concept_edges.to_sql("concept_edges", graph_conn, if_exists="replace", index=False)
        concept_edge_profiles.to_sql("concept_edge_profiles", graph_conn, if_exists="replace", index=False)
        concept_edge_contexts.to_sql("concept_edge_contexts", graph_conn, if_exists="replace", index=False)
        concept_edge_exemplars.to_sql("concept_edge_exemplars", graph_conn, if_exists="replace", index=False)
        graph_conn.commit()
    finally:
        graph_conn.close()

    app_db_path, stats = build_concept_app_db(
        concept_nodes=concept_nodes,
        corpus_df=corpus_df,
        concept_edges_for_corpus=concept_edges_for_corpus,
        concept_edges=concept_edges,
        concept_edge_profiles=concept_edge_profiles,
        concept_edge_contexts=concept_edge_contexts,
        concept_edge_exemplars=concept_edge_exemplars,
        output_root=output_root,
        view_name=mapping_variant,
        app_mode=app_mode,
        ontology_version=ontology_version,
    )
    return {
        "graph_db": str(graph_db_path),
        "app_db": str(app_db_path),
        "counts": {
            "works": int(len(works)),
            "mapped_node_instances": int(len(mappings[mappings["concept_id"].notna()])),
            "concept_edge_instances": int(len(concept_edge_instances)),
            **stats,
        },
    }


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    ensure_dir(output_root)

    hard = build_view(
        extraction_db=Path(args.extraction_db),
        ontology_db=Path(args.ontology_db),
        output_root=output_root,
        mapping_table="instance_mappings_hard",
        mapping_variant="hard",
        app_mode="concept_strict",
        ontology_version="v3",
    )
    soft = build_view(
        extraction_db=Path(args.extraction_db),
        ontology_db=Path(args.ontology_db),
        output_root=output_root,
        mapping_table="instance_mappings_soft",
        mapping_variant="exploratory",
        app_mode="concept_exploratory",
        ontology_version="v3",
    )

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ontology_db": args.ontology_db,
        "extraction_db": args.extraction_db,
        "views": {
            "hard": hard,
            "exploratory": soft,
        },
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
