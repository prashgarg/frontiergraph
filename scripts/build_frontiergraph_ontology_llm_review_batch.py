from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


DEFAULT_ONTOLOGY_DB = "data/production/frontiergraph_ontology_v1/ontology_v1.sqlite"
DEFAULT_OUTPUT_DIR = "data/production/frontiergraph_ontology_v1/review_batches"
DEFAULT_SYSTEM_PROMPT = "prompts/frontiergraph_ontology_v1/system_prompt.md"
DEFAULT_SCHEMA = "prompts/frontiergraph_ontology_v1/schema.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build batch inputs for FrontierGraph ontology pair adjudication.")
    parser.add_argument("--ontology-db", default=DEFAULT_ONTOLOGY_DB)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--schema-path", default=DEFAULT_SCHEMA)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--max-output-tokens", type=int, default=4000)
    parser.add_argument("--limit", type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    system_prompt = Path(args.system_prompt).read_text(encoding="utf-8")
    schema = json.loads(Path(args.schema_path).read_text(encoding="utf-8"))

    conn = sqlite3.connect(args.ontology_db)
    rows = conn.execute(
        """
        SELECT
            cp.left_normalized_label,
            cp.right_normalized_label,
            cp.lexical_score,
            cp.signature_overlap_json,
            cp.neighbor_jaccard,
            cp.relationship_profile_similarity,
            cp.edge_role_profile_similarity,
            cp.country_overlap,
            cp.unit_overlap,
            cp.bucket_profile_similarity,
            cp.combined_score,
            cp.notes,
            ls.preferred_label,
            rs.preferred_label
        FROM candidate_pairs cp
        JOIN node_strings ls ON ls.normalized_label = cp.left_normalized_label
        JOIN node_strings rs ON rs.normalized_label = cp.right_normalized_label
        WHERE cp.decision_status = 'needs_llm_review'
        ORDER BY cp.combined_score DESC, cp.left_normalized_label, cp.right_normalized_label
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()
    conn.close()

    out_jsonl = output_dir / "ontology_llm_review_batch.jsonl"
    count = 0
    with out_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            (
                left_label,
                right_label,
                lexical_score,
                signature_overlap_json,
                neighbor_jaccard,
                relationship_profile_similarity,
                edge_role_profile_similarity,
                country_overlap,
                unit_overlap,
                bucket_profile_similarity,
                combined_score,
                notes,
                left_preferred,
                right_preferred,
            ) = row
            graph_evidence = {
                "neighbor_jaccard": neighbor_jaccard,
                "relationship_profile_similarity": relationship_profile_similarity,
                "edge_role_profile_similarity": edge_role_profile_similarity,
                "country_overlap": country_overlap,
                "unit_overlap": unit_overlap,
                "bucket_profile_similarity": bucket_profile_similarity,
                "combined_score": combined_score,
                "notes": notes,
            }
            lexical_evidence = {
                "lexical_score": lexical_score,
                "signature_overlap": json.loads(signature_overlap_json),
                "left_preferred_label": left_preferred,
                "right_preferred_label": right_preferred,
            }
            prompt = (
                f"Evaluate whether these two FrontierGraph node strings should map to the same canonical concept.\n\n"
                f"Left label:\n{left_label}\n\n"
                f"Right label:\n{right_label}\n\n"
                f"Lexical evidence:\n{json.dumps(lexical_evidence, ensure_ascii=False, indent=2)}\n\n"
                f"Graph/context evidence:\n{json.dumps(graph_evidence, ensure_ascii=False, indent=2)}\n\n"
                "Return only valid structured output matching the supplied schema.\n"
            )
            request = {
                "custom_id": f"ONTOLOGY__{left_label}__{right_label}",
                "method": "POST",
                "url": "/v1/responses",
                "body": {
                    "model": args.model,
                    "reasoning": {"effort": args.reasoning_effort},
                    "instructions": system_prompt,
                    "max_output_tokens": args.max_output_tokens,
                    "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "frontiergraph_ontology_pair_review_v1",
                            "strict": True,
                            "schema": schema,
                        }
                    },
                },
            }
            handle.write(json.dumps(request, ensure_ascii=False) + "\n")
            count += 1

    manifest = {
        "rows": count,
        "output_jsonl": str(out_jsonl),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "schema_path": str(args.schema_path),
        "system_prompt": str(args.system_prompt),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
