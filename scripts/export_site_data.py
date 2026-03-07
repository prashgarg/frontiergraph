from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.opportunity_data import (
    JEL_FIELD_NAMES,
    PRESET_HELP,
    compute_priority_score,
    load_candidate_summary,
    recommendation_play,
    to_float,
    to_int,
    why_now,
)


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/processed/app_causalclaims.db"
SITE_ROOT = ROOT / "site"
GENERATED_DIR = SITE_ROOT / "src/generated"
PUBLIC_DATA_DIR = SITE_ROOT / "public/data"
PUBLIC_DOWNLOADS_DIR = SITE_ROOT / "public/downloads"
APP_URL = os.environ.get(
    "FRONTIERGRAPH_APP_URL",
    "https://economics-opportunity-ranker-beta-1058669339361.us-central1.run.app",
)
REPO_URL = os.environ.get("FRONTIERGRAPH_REPO_URL", "https://github.com/prashgarg/frontiergraph")
PUBLIC_DB_URL = os.environ.get("FRONTIERGRAPH_PUBLIC_DB_URL", "")
DB_FILENAME = "frontiergraph-economics-beta.db"
DB_SHA256 = "e755bcdc3b770fe139dfbbe870be3cc111b10fa95d50f6d6492c70e61c23cde8"


@dataclass(frozen=True)
class DiscoverySlice:
    slug: str
    title: str
    description: str
    preset: str
    link_query: str


DISCOVERY_SLICES = {
    "bridges": DiscoverySlice(
        slug="bridges",
        title="Cross-field bridges",
        description="Ideas with thin direct contact but strong evidence that separate literatures should connect.",
        preset="Bridge builder",
        link_query="?preset=Bridge%20builder&only_cross_field=true",
    ),
    "frontier": DiscoverySlice(
        slug="frontier",
        title="Frontier bets",
        description="The boldest graph-implied links, with emphasis on boundary and cross-field opportunities.",
        preset="Bold frontier",
        link_query="?preset=Bold%20frontier&only_cross_field=true",
    ),
    "fast-follow": DiscoverySlice(
        slug="fast-follow",
        title="Fast-follow ideas",
        description="Ideas that already have strong graph support and look most tractable right now.",
        preset="Fast follow",
        link_query="?preset=Fast%20follow",
    ),
    "underexplored": DiscoverySlice(
        slug="underexplored",
        title="Underexplored gaps",
        description="Areas where the graph suggests a direct link, but the literature still looks surprisingly thin.",
        preset="Underexplored",
        link_query="?preset=Underexplored",
    ),
}


def query_scalar(conn: sqlite3.Connection, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def add_priority_columns(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    for preset in PRESET_HELP:
        column = preset_to_column(preset)
        working[column] = compute_priority_score(working, preset)
    working["balanced_rank"] = (
        working["balanced_score"].rank(method="first", ascending=False).astype(int)
    )
    return working


def preset_to_column(preset: str) -> str:
    return preset.lower().replace(" ", "_").replace("-", "_") + "_score"


def opportunity_record(row: pd.Series, priority_column: str = "balanced_score") -> dict[str, object]:
    preset_name = priority_column.replace("_score", "").replace("_", " ").title()
    if preset_name == "Balanced":
        preset_name = "Balanced"
    return {
        "opportunity": str(row["opportunity"]),
        "code_pair": str(row["code_pair"]),
        "source_field": str(row["source_field"]),
        "source_field_name": str(row["source_field_name"]),
        "target_field": str(row["target_field"]),
        "target_field_name": str(row["target_field_name"]),
        "novelty": str(row["novelty_label"]),
        "priority": round(to_float(row.get(priority_column, 0.0)), 3),
        "base_score": round(to_float(row.get("score", 0.0)), 3),
        "prior_contact": to_int(row.get("cooc_count", 0)),
        "mediators": to_int(row.get("mediator_count", 0)),
        "motifs": to_int(row.get("motif_count", 0)),
        "project_shape": recommendation_play(row),
        "why_now": why_now(row),
        "app_link": f"{APP_URL}?source_field={row['source_field']}&target_field={row['target_field']}&preset={preset_name.replace(' ', '%20')}",
    }


def export_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df[
        [
            "opportunity",
            "code_pair",
            "source_field_name",
            "target_field_name",
            "novelty_label",
            "balanced_score",
            "score",
            "cooc_count",
            "mediator_count",
            "motif_count",
        ]
    ].rename(
        columns={
            "source_field_name": "source_field",
            "target_field_name": "target_field",
            "novelty_label": "novelty",
            "balanced_score": "priority",
            "score": "base_score",
            "cooc_count": "prior_contact",
            "mediator_count": "mediators",
            "motif_count": "motifs",
        }
    )
    out.to_csv(path, index=False)


def top_for_slice(df: pd.DataFrame, slug: str, n: int = 18) -> pd.DataFrame:
    if slug == "bridges":
        subset = df[(df["cross_field"]) & (df["cooc_count"].fillna(0) <= 5)].copy()
        return subset.sort_values(["bridge_builder_score", "score"], ascending=[False, False]).head(n)
    if slug == "frontier":
        subset = df[df["cross_field"]].copy()
        return subset.sort_values(["bold_frontier_score", "score"], ascending=[False, False]).head(n)
    if slug == "fast-follow":
        subset = df[df["cooc_count"].fillna(0) > 0].copy()
        return subset.sort_values(["fast_follow_score", "score"], ascending=[False, False]).head(n)
    subset = df[df["cooc_count"].fillna(0) <= 12].copy()
    return subset.sort_values(["underexplored_score", "score"], ascending=[False, False]).head(n)


def field_summary(df: pd.DataFrame, code: str) -> dict[str, object]:
    touching = df[(df["source_field"] == code) | (df["target_field"] == code)].copy()
    targeting = df[df["target_field"] == code].copy().sort_values(
        ["balanced_score", "score"], ascending=[False, False]
    )
    originating = df[df["source_field"] == code].copy().sort_values(
        ["balanced_score", "score"], ascending=[False, False]
    )
    corridors = (
        touching.assign(corridor=touching["source_field"] + " -> " + touching["target_field"])
        .groupby(["corridor", "source_field_name", "target_field_name"], as_index=False)
        .agg(
            ideas=("balanced_score", "size"),
            mean_priority=("balanced_score", "mean"),
            boundary_share=("boundary_flag", "mean"),
        )
        .sort_values(["mean_priority", "ideas"], ascending=[False, False])
        .head(8)
    )

    csv_name = f"field-{code.lower()}.csv"
    export_csv(touching.sort_values(["balanced_score", "score"], ascending=[False, False]).head(200), PUBLIC_DATA_DIR / csv_name)

    examples_df = pd.concat([targeting.head(2), originating.head(2)], ignore_index=True).drop_duplicates(
        subset=["code_pair"]
    )

    return {
        "code": code,
        "name": JEL_FIELD_NAMES.get(code, code),
        "ideas": int(len(touching)),
        "median_priority": round(float(touching["balanced_score"].median()), 3) if not touching.empty else 0.0,
        "top_targeting": [opportunity_record(row) for _, row in targeting.head(12).iterrows()],
        "top_originating": [opportunity_record(row) for _, row in originating.head(12).iterrows()],
        "corridors": [
            {
                "corridor": str(row["corridor"]),
                "source_field_name": str(row["source_field_name"]),
                "target_field_name": str(row["target_field_name"]),
                "ideas": int(row["ideas"]),
                "mean_priority": round(float(row["mean_priority"]), 3),
                "boundary_share": round(float(row["boundary_share"]), 3),
            }
            for _, row in corridors.iterrows()
        ],
        "examples": [opportunity_record(row) for _, row in examples_df.iterrows()],
        "download_path": f"/data/{csv_name}",
        "app_link": f"{APP_URL}?target_field={code}&preset=Balanced",
    }


def build_site_data() -> dict[str, object]:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    candidates = add_priority_columns(load_candidate_summary(str(DB_PATH)))
    balanced = candidates.sort_values(["balanced_score", "score"], ascending=[False, False]).reset_index(drop=True)

    with sqlite3.connect(DB_PATH) as conn:
        metrics = {
            "nodes": query_scalar(conn, "SELECT COUNT(*) FROM nodes"),
            "papers": query_scalar(conn, "SELECT COUNT(*) FROM papers"),
            "candidates": query_scalar(conn, "SELECT COUNT(*) FROM candidates"),
            "candidate_paths": query_scalar(conn, "SELECT COUNT(*) FROM candidate_paths"),
            "candidate_papers": query_scalar(conn, "SELECT COUNT(*) FROM candidate_papers"),
        }

    discovery_payload: dict[str, object] = {}
    for slug, definition in DISCOVERY_SLICES.items():
        slice_df = top_for_slice(candidates, slug)
        export_csv(slice_df, PUBLIC_DATA_DIR / f"{slug}.csv")
        score_column = preset_to_column(definition.preset)
        discovery_payload[slug] = {
            "slug": slug,
            "title": definition.title,
            "description": definition.description,
            "preset": definition.preset,
            "app_link": f"{APP_URL}{definition.link_query}",
            "download_path": f"/data/{slug}.csv",
            "items": [opportunity_record(row, priority_column=score_column) for _, row in slice_df.iterrows()],
        }

    active_codes = sorted(set(candidates["source_field"]) | set(candidates["target_field"]))
    fields = {code: field_summary(candidates, code) for code in active_codes if code in JEL_FIELD_NAMES}
    fields_index = [
        {
            "code": code,
            "name": payload["name"],
            "ideas": payload["ideas"],
            "median_priority": payload["median_priority"],
            "download_path": payload["download_path"],
            "app_link": payload["app_link"],
        }
        for code, payload in fields.items()
    ]
    fields_index.sort(key=lambda item: (-item["median_priority"], item["code"]))
    export_csv(balanced.head(250), PUBLIC_DATA_DIR / "homepage-snapshot.csv")

    db_size = DB_PATH.stat().st_size
    manifest = {
        "filename": DB_FILENAME,
        "db_size_bytes": db_size,
        "db_size_gb": round(db_size / (1024 ** 3), 2),
        "sha256": DB_SHA256,
        "public_url": PUBLIC_DB_URL,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    (PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-beta.sha256.txt").write_text(
        f"{DB_SHA256}  {DB_FILENAME}\n",
        encoding="utf-8",
    )
    (PUBLIC_DOWNLOADS_DIR / "frontiergraph-economics-beta.manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app_url": APP_URL,
        "repo_url": REPO_URL,
        "metrics": metrics,
        "home": {
            "hero_example": opportunity_record(balanced.iloc[0]),
            "snapshot": [opportunity_record(row) for _, row in balanced.head(6).iterrows()],
        },
        "discover": discovery_payload,
        "fields_index": fields_index,
        "fields": fields,
        "downloads": {
            "repo_url": REPO_URL,
            "demo_data_path": "/downloads/demo-data",
            "beta_db": manifest,
            "checksum_path": "/downloads/frontiergraph-economics-beta.sha256.txt",
            "manifest_path": "/downloads/frontiergraph-economics-beta.manifest.json",
        },
    }


def main() -> None:
    site_data = build_site_data()
    (GENERATED_DIR / "site-data.json").write_text(json.dumps(site_data, indent=2), encoding="utf-8")
    print(f"Wrote {GENERATED_DIR / 'site-data.json'}")


if __name__ == "__main__":
    main()
