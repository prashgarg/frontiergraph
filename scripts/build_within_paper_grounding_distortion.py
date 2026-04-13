from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"
OUT_DIR = ROOT / "outputs" / "paper" / "48_within_paper_grounding_distortion"
NOTE_PATH = ROOT / "next_steps" / "within_paper_grounding_distortion_note.md"

GROUNDING_PATH = DATA_DIR / "extraction_label_grounding_v2_reviewed_round2.parquet"


def load_grounding_module():
    path = ROOT / "scripts" / "build_ontology_v2_open_world_grounding.py"
    spec = importlib.util.spec_from_file_location("grounding_distortion_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_maps(df: pd.DataFrame, normalize_label):
    direct_075: dict[str, str | None] = {}
    direct_075_label: dict[str, str | None] = {}
    reviewed_existing: dict[str, str | None] = {}
    reviewed_existing_label: dict[str, str | None] = {}
    reviewed_with_family: dict[str, str | None] = {}
    reviewed_with_family_label: dict[str, str | None] = {}

    for _, row in df.iterrows():
        label = str(row["label"])
        rank1_score = float(row.get("rank1_score") or 0.0)
        direct_id = str(row["onto_id"]) if pd.notna(row.get("onto_id")) and rank1_score >= 0.75 else None
        direct_label = str(row["onto_label"]) if direct_id else None

        overlay_decision = str(row.get("final_decision") or "")
        overlay_target_id = str(row["proposed_onto_id_y"]) if pd.notna(row.get("proposed_onto_id_y")) else None
        overlay_target_label = str(row["proposed_onto_label_y"]) if pd.notna(row.get("proposed_onto_label_y")) else None
        family_label = str(row.get("proposed_new_concept_family_label") or "").strip() or label
        family_id = f"family::{normalize_label(family_label)}" if family_label else None

        direct_075[label] = direct_id
        direct_075_label[label] = direct_label

        if direct_id:
            reviewed_existing[label] = direct_id
            reviewed_existing_label[label] = direct_label
            reviewed_with_family[label] = direct_id
            reviewed_with_family_label[label] = direct_label
        elif overlay_decision in {"accept_existing_broad", "accept_existing_alias"} and overlay_target_id:
            reviewed_existing[label] = overlay_target_id
            reviewed_existing_label[label] = overlay_target_label
            reviewed_with_family[label] = overlay_target_id
            reviewed_with_family_label[label] = overlay_target_label
        elif overlay_decision == "promote_new_concept_family" and family_id:
            reviewed_existing[label] = None
            reviewed_existing_label[label] = None
            reviewed_with_family[label] = family_id
            reviewed_with_family_label[label] = family_label
        else:
            reviewed_existing[label] = None
            reviewed_existing_label[label] = None
            reviewed_with_family[label] = None
            reviewed_with_family_label[label] = None

    return {
        "direct_075": direct_075,
        "reviewed_existing": reviewed_existing,
        "reviewed_with_family": reviewed_with_family,
    }


def parse_papers(extractions_path: Path, normalize_label):
    with gzip.open(extractions_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            rec = json.loads(line)
            output = rec.get("output", {})
            if not isinstance(output, dict):
                continue

            paper_id = str(rec.get("custom_id") or rec.get("openalex_work_id") or "")
            year_raw = rec.get("publication_year")
            year = int(year_raw) if year_raw not in (None, "") else None

            node_to_label: dict[str, str] = {}
            labels_in_paper: set[str] = set()
            for node in output.get("nodes", []):
                label = normalize_label(str(node.get("label", "")).strip())
                node_id = str(node.get("node_id", "")).strip()
                if not label or not node_id:
                    continue
                node_to_label[node_id] = label
                labels_in_paper.add(label)

            raw_edges: set[tuple[str, str, str]] = set()
            for edge in output.get("edges", []):
                source_label = node_to_label.get(str(edge.get("source_node_id", "")).strip())
                target_label = node_to_label.get(str(edge.get("target_node_id", "")).strip())
                if not source_label or not target_label:
                    continue
                directionality = str(edge.get("directionality", "")).strip().lower()
                edge_kind = "directed" if directionality == "directed" else "undirected"
                raw_edges.add((source_label, target_label, edge_kind))

            yield {
                "paper_id": paper_id,
                "year": year,
                "labels": sorted(labels_in_paper),
                "edges": sorted(raw_edges),
            }


def two_step_paths(raw_edges: list[tuple[str, str, str]]) -> set[tuple[str, str, str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for source, target, edge_kind in raw_edges:
        adjacency[source].add(target)
        if edge_kind == "undirected":
            adjacency[target].add(source)

    paths: set[tuple[str, str, str]] = set()
    for mid, predecessors in adjacency.items():
        for left in predecessors:
            for right in adjacency.get(mid, set()):
                if left == right or left == mid or right == mid:
                    continue
                paths.add((left, mid, right))
    return paths


def summarize_variant(labels: list[str], raw_edges: list[tuple[str, str, str]], mapping: dict[str, str | None]) -> dict[str, float | int]:
    attached_labels = [label for label in labels if mapping.get(label)]
    grounded_nodes = [mapping[label] for label in attached_labels]
    node_collision_count = len(attached_labels) - len(set(grounded_nodes))

    attached_edge_count = 0
    grounded_edges: set[tuple[str, str, str]] = set()
    self_loop_count = 0
    for source, target, edge_kind in raw_edges:
        source_target = mapping.get(source)
        target_target = mapping.get(target)
        if not source_target or not target_target:
            continue
        attached_edge_count += 1
        grounded_edge = (source_target, target_target, edge_kind)
        grounded_edges.add(grounded_edge)
        if source != target and source_target == target_target:
            self_loop_count += 1
    edge_collision_count = attached_edge_count - len(grounded_edges)

    raw_paths = two_step_paths(raw_edges)
    attached_path_count = 0
    collapsed_path_count = 0
    for left, mid, right in raw_paths:
        left_target = mapping.get(left)
        mid_target = mapping.get(mid)
        right_target = mapping.get(right)
        if not left_target or not mid_target or not right_target:
            continue
        attached_path_count += 1
        if len({left_target, mid_target, right_target}) < 3:
            collapsed_path_count += 1

    return {
        "raw_unique_labels": len(labels),
        "attached_raw_labels": len(attached_labels),
        "unique_grounded_nodes": len(set(grounded_nodes)),
        "node_collision_count": node_collision_count,
        "raw_unique_edges": len(raw_edges),
        "attached_raw_edges": attached_edge_count,
        "unique_grounded_edges": len(grounded_edges),
        "edge_collision_count": edge_collision_count,
        "self_loop_count": self_loop_count,
        "raw_two_step_paths": len(raw_paths),
        "attached_two_step_paths": attached_path_count,
        "collapsed_two_step_paths": collapsed_path_count,
    }


def build_outputs():
    module = load_grounding_module()
    grounding = pd.read_parquet(
        GROUNDING_PATH,
        columns=[
            "label",
            "onto_id",
            "onto_label",
            "rank1_score",
            "final_decision",
            "proposed_onto_id_y",
            "proposed_onto_label_y",
            "proposed_new_concept_family_label",
        ],
    )
    maps = build_maps(grounding, module.normalize_label)

    paper_rows = []
    for paper in parse_papers(module.EXTRACTIONS_PATH, module.normalize_label):
        row = {"paper_id": paper["paper_id"], "year": paper["year"]}
        for variant_name, mapping in maps.items():
            stats = summarize_variant(paper["labels"], paper["edges"], mapping)
            for key, value in stats.items():
                row[f"{variant_name}__{key}"] = value
        paper_rows.append(row)

    paper_df = pd.DataFrame(paper_rows)

    summary_rows = []
    for variant_name in maps:
        attached_labels = int(paper_df[f"{variant_name}__attached_raw_labels"].sum())
        attached_edges = int(paper_df[f"{variant_name}__attached_raw_edges"].sum())
        attached_paths = int(paper_df[f"{variant_name}__attached_two_step_paths"].sum())
        node_collisions = int(paper_df[f"{variant_name}__node_collision_count"].sum())
        edge_collisions = int(paper_df[f"{variant_name}__edge_collision_count"].sum())
        self_loops = int(paper_df[f"{variant_name}__self_loop_count"].sum())
        path_collapses = int(paper_df[f"{variant_name}__collapsed_two_step_paths"].sum())
        summary_rows.append(
            {
                "variant": variant_name,
                "papers": len(paper_df),
                "papers_with_node_collision": int((paper_df[f"{variant_name}__node_collision_count"] > 0).sum()),
                "papers_with_edge_collision": int((paper_df[f"{variant_name}__edge_collision_count"] > 0).sum()),
                "papers_with_self_loop": int((paper_df[f"{variant_name}__self_loop_count"] > 0).sum()),
                "papers_with_path_collapse": int((paper_df[f"{variant_name}__collapsed_two_step_paths"] > 0).sum()),
                "attached_raw_labels": attached_labels,
                "node_collision_count": node_collisions,
                "node_collision_rate": (node_collisions / attached_labels) if attached_labels else 0.0,
                "attached_raw_edges": attached_edges,
                "edge_collision_count": edge_collisions,
                "edge_collision_rate": (edge_collisions / attached_edges) if attached_edges else 0.0,
                "self_loop_count": self_loops,
                "self_loop_rate": (self_loops / attached_edges) if attached_edges else 0.0,
                "attached_two_step_paths": attached_paths,
                "collapsed_two_step_paths": path_collapses,
                "path_collapse_rate": (path_collapses / attached_paths) if attached_paths else 0.0,
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    return paper_df, summary_df


def write_markdown(summary_df: pd.DataFrame) -> str:
    label_map = {
        "direct_075": "Direct threshold only (`>=0.75`)",
        "reviewed_existing": "Reviewed overlay, existing-concept attachments only",
        "reviewed_with_family": "Reviewed overlay plus synthetic family nodes",
    }
    lines = [
        "# Within-Paper Grounding Distortion",
        "",
        "This diagnostic measures how much a global grounding layer collapses distinct within-paper nodes and edges.",
        "",
        "| Variant | Papers with node collision | Node collision rate | Papers with edge collision | Edge collision rate | Papers with self loop | Self-loop rate | Papers with path collapse | Path collapse rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in summary_df.iterrows():
        lines.append(
            f"| {label_map.get(row['variant'], row['variant'])} | "
            f"{int(row['papers_with_node_collision']):,} | {row['node_collision_rate']:.3f} | "
            f"{int(row['papers_with_edge_collision']):,} | {row['edge_collision_rate']:.3f} | "
            f"{int(row['papers_with_self_loop']):,} | {row['self_loop_rate']:.3f} | "
            f"{int(row['papers_with_path_collapse']):,} | {row['path_collapse_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- node collision means two distinct raw labels in the same paper map to the same grounded node",
            "- edge collision means distinct raw edges collapse onto the same grounded edge",
            "- self loops are edges that become source=target after grounding",
            "- path collapse is a proxy for local structural compression in two-step paths",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paper_df, summary_df = build_outputs()
    paper_df.to_parquet(OUT_DIR / "paper_level.parquet", index=False)
    summary_df.to_csv(OUT_DIR / "summary.csv", index=False)
    markdown = write_markdown(summary_df)
    (OUT_DIR / "summary.md").write_text(markdown, encoding="utf-8")
    NOTE_PATH.write_text(markdown, encoding="utf-8")
    print("Within-paper grounding distortion artifacts written.")
    print(f"Papers: {len(paper_df):,}")


if __name__ == "__main__":
    main()
