from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from src.adapters.base import AdapterResult
from src.adapters.generic_csv_adapter import GenericCSVAdapter


def _pick_col(columns: list[str], candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def _normalize_edges_columns(df: pd.DataFrame) -> pd.DataFrame | None:
    cols = list(df.columns)
    jel_src_col = _pick_col(cols, ["jel_source", "jel_cause"])
    jel_dst_col = _pick_col(cols, ["jel_sink", "jel_effect"])
    src_col = _pick_col(
        cols,
        [
            "src_code",
            "source_code",
            "src",
            "from_code",
            "from",
            "cause_code",
            "cause",
            "antecedent",
            "node_from",
        ],
    )
    dst_col = _pick_col(
        cols,
        [
            "dst_code",
            "target_code",
            "dst",
            "to_code",
            "to",
            "effect_code",
            "effect",
            "consequent",
            "node_to",
        ],
    )
    if not src_col or not dst_col:
        return None
    paper_col = _pick_col(cols, ["paper_id", "id", "doc_id", "record_id", "nber_id", "paper"])
    year_col = _pick_col(cols, ["year", "pub_year", "publication_year"])
    relation_col = _pick_col(cols, ["relation_type", "relation", "edge_type", "claim_type"])
    evidence_col = _pick_col(cols, ["evidence_type", "evidence", "method", "causal_inference_method", "method_family", "method_class"])
    causal_col = _pick_col(cols, ["is_causal", "causal", "iscausal", "is_method_causal_inference", "is_causal_relationship", "is_causal_relationship_flag"])
    weight_col = _pick_col(cols, ["weight", "edge_weight", "count"])
    stability_col = _pick_col(cols, ["stability", "overlap", "edge_overlap", "confidence"])

    out = pd.DataFrame()
    out["paper_id"] = df[paper_col].astype(str) if paper_col else [f"P_{i}" for i in range(len(df))]
    out["year"] = pd.to_numeric(df[year_col], errors="coerce").fillna(0).astype(int) if year_col else 0
    if jel_src_col and jel_dst_col:
        out["src_code"] = df[jel_src_col].astype(str)
        out["dst_code"] = df[jel_dst_col].astype(str)
    else:
        out["src_code"] = df[src_col].astype(str)
        out["dst_code"] = df[dst_col].astype(str)
    out["relation_type"] = df[relation_col].astype(str) if relation_col else "unspecified"
    out["evidence_type"] = df[evidence_col].astype(str) if evidence_col else "unspecified"
    out["is_causal"] = df[causal_col] if causal_col else False
    out["weight"] = pd.to_numeric(df[weight_col], errors="coerce").fillna(1.0) if weight_col else 1.0
    out["stability"] = pd.to_numeric(df[stability_col], errors="coerce") if stability_col else pd.NA
    return out


def _normalize_papers_columns(df: pd.DataFrame) -> pd.DataFrame | None:
    cols = list(df.columns)
    paper_col = _pick_col(cols, ["paper_id", "id", "doc_id", "record_id", "nber_id", "paper"])
    year_col = _pick_col(cols, ["year", "pub_year", "publication_year"])
    if not paper_col or not year_col:
        return None
    title_col = _pick_col(cols, ["title", "paper_title"])
    authors_col = _pick_col(cols, ["authors", "author_names", "author"])
    venue_col = _pick_col(cols, ["venue", "journal", "outlet"])
    source_col = _pick_col(cols, ["source", "dataset"])

    out = pd.DataFrame()
    out["paper_id"] = df[paper_col].astype(str)
    out["year"] = pd.to_numeric(df[year_col], errors="coerce").fillna(0).astype(int)
    out["title"] = df[title_col].astype(str) if title_col else ""
    out["authors"] = df[authors_col].astype(str) if authors_col else ""
    out["venue"] = df[venue_col].astype(str) if venue_col else ""
    out["source"] = df[source_col].astype(str) if source_col else "causalclaims"
    return out


def _normalize_nodes_columns(df: pd.DataFrame) -> pd.DataFrame | None:
    cols = list(df.columns)
    code_col = _pick_col(cols, ["code", "node_code", "concept_code", "id"])
    if not code_col:
        return None
    label_col = _pick_col(cols, ["label", "name", "concept", "node_label"])
    out = pd.DataFrame()
    out["code"] = df[code_col].astype(str)
    out["label"] = df[label_col].astype(str) if label_col else out["code"]
    return out


def _nodes_from_jel_columns(df: pd.DataFrame) -> pd.DataFrame | None:
    cols = set(df.columns)
    if not {"jel_cause", "jel_effect", "cause", "effect"}.issubset(cols):
        return None
    src = (
        df[["jel_cause", "cause"]]
        .dropna()
        .rename(columns={"jel_cause": "code", "cause": "label"})
        .astype({"code": str, "label": str})
    )
    dst = (
        df[["jel_effect", "effect"]]
        .dropna()
        .rename(columns={"jel_effect": "code", "effect": "label"})
        .astype({"code": str, "label": str})
    )
    both = pd.concat([src, dst], ignore_index=True)
    if both.empty:
        return None
    nodes = (
        both.groupby(["code", "label"], as_index=False)
        .size()
        .sort_values(["code", "size"], ascending=[True, False])
        .drop_duplicates(subset=["code"])
    )[["code", "label"]]
    return nodes


class CausalClaimsAdapter:
    REPO_URL = "https://github.com/prashgarg/CausalClaimsInEconomics"

    def __init__(self, external_dir: str | Path, demo_dir: str | Path):
        self.external_dir = Path(external_dir) / "CausalClaimsInEconomics"
        self.demo_dir = Path(demo_dir)
        self.logs: list[str] = []

    def load(self) -> AdapterResult:
        try:
            repo_dir = self._ensure_repo()
            loaded = self._load_from_repo(repo_dir)
            if loaded is not None:
                self.logs.append(f"Loaded CausalClaims data from {repo_dir}")
                return loaded
            self.logs.append("CausalClaims data not parseable; falling back to demo data.")
        except Exception as exc:  # noqa: BLE001
            self.logs.append(f"CausalClaims adapter failed: {exc}. Falling back to demo data.")
        demo = GenericCSVAdapter(self.demo_dir).load()
        self.logs.append(f"Loaded fallback demo data from {self.demo_dir}")
        return demo

    def _ensure_repo(self) -> Path:
        if self.external_dir.exists():
            self.logs.append(f"Using existing external repo: {self.external_dir}")
            return self.external_dir

        self.external_dir.parent.mkdir(parents=True, exist_ok=True)
        clone_cmd = ["git", "clone", self.REPO_URL, str(self.external_dir)]
        proc = subprocess.run(clone_cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            self.logs.append(f"Cloned {self.REPO_URL} into {self.external_dir}")
            return self.external_dir

        self.logs.append(f"Clone failed: {proc.stderr.strip()[:240]}")
        sibling_local = Path("..") / "CausalClaims"
        if sibling_local.exists():
            self.logs.append(f"Using sibling local fallback repository: {sibling_local.resolve()}")
            return sibling_local.resolve()
        raise RuntimeError("Could not clone CausalClaimsInEconomics and no local fallback path found.")

    def _load_from_repo(self, repo_dir: Path) -> AdapterResult | None:
        parquet_result = self._load_from_parquet(repo_dir)
        if parquet_result is not None:
            return parquet_result
        self._run_materialization(repo_dir)
        parquet_result = self._load_from_parquet(repo_dir)
        if parquet_result is not None:
            return parquet_result
        return self._load_from_jsonl(repo_dir)

    def _run_materialization(self, repo_dir: Path) -> None:
        patterns = [
            "**/materialize_analysis_data.py",
            "**/*materialize*analysis*.py",
            "**/*join*analysis*data*.py",
        ]
        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(repo_dir.glob(pattern))
        unique_scripts: list[Path] = []
        seen: set[Path] = set()
        for script in candidates:
            if ".venv" in script.parts or "__pycache__" in script.parts:
                continue
            resolved = script.resolve()
            if resolved not in seen:
                unique_scripts.append(script)
                seen.add(resolved)
        for script in unique_scripts[:6]:
            cmd = [sys.executable, str(script)]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=str(script.parent),
            )
            msg = f"Ran {script}: rc={proc.returncode}"
            if proc.returncode != 0:
                msg += f", err={proc.stderr.strip()[:200]}"
            self.logs.append(msg)

    def _load_from_parquet(self, repo_dir: Path) -> AdapterResult | None:
        claims_bundle = self._load_claims_papers_bundle(repo_dir)
        if claims_bundle is not None:
            return claims_bundle

        parquet_files = [p for p in repo_dir.rglob("*.parquet") if ".venv" not in p.parts]
        if not parquet_files:
            self.logs.append("No parquet files found in external repo.")
            return None

        best_edges: pd.DataFrame | None = None
        best_papers: pd.DataFrame | None = None
        best_nodes: pd.DataFrame | None = None

        for p in parquet_files:
            try:
                df = pd.read_parquet(p)
            except Exception:  # noqa: BLE001
                continue
            edges_try = _normalize_edges_columns(df)
            if edges_try is not None and (best_edges is None or len(edges_try) > len(best_edges)):
                best_edges = edges_try
            papers_try = _normalize_papers_columns(df)
            if papers_try is not None and (best_papers is None or len(papers_try) > len(best_papers)):
                best_papers = papers_try
            nodes_try = _nodes_from_jel_columns(df)
            if nodes_try is None:
                nodes_try = _normalize_nodes_columns(df)
            if nodes_try is not None and (best_nodes is None or len(nodes_try) > len(best_nodes)):
                best_nodes = nodes_try

        if best_edges is None:
            self.logs.append("Parquet files found but no edge-like table detected.")
            return None
        if best_papers is None:
            best_papers = self._derive_papers_from_edges(best_edges)
        if best_nodes is None:
            best_nodes = self._derive_nodes_from_edges(best_edges)
        return AdapterResult(nodes_df=best_nodes, papers_df=best_papers, edges_df=best_edges)

    def _load_claims_papers_bundle(self, repo_dir: Path) -> AdapterResult | None:
        claims_candidates = [p for p in repo_dir.rglob("claims.parquet") if ".venv" not in p.parts]
        papers_candidates = [p for p in repo_dir.rglob("papers.parquet") if ".venv" not in p.parts]
        if not claims_candidates or not papers_candidates:
            return None

        # Prefer colocated claims/papers under the same derived-data directory.
        best_pair: tuple[Path, Path] | None = None
        best_claim_rows = -1
        for claims_path in claims_candidates:
            for papers_path in papers_candidates:
                if claims_path.parent != papers_path.parent:
                    continue
                try:
                    claims_df = pd.read_parquet(claims_path, columns=["paper_id"])
                except Exception:  # noqa: BLE001
                    continue
                n_rows = len(claims_df)
                if n_rows > best_claim_rows:
                    best_claim_rows = n_rows
                    best_pair = (claims_path, papers_path)
        if best_pair is None:
            return None

        claims_path, papers_path = best_pair
        claims_df = pd.read_parquet(claims_path)
        papers_df_raw = pd.read_parquet(papers_path)
        required_claim_cols = {"paper_id", "source", "sink"}
        if not required_claim_cols.issubset(set(claims_df.columns)):
            self.logs.append("claims.parquet found but missing required source/sink columns.")
            return None

        src_code_col = "jel_source" if "jel_source" in claims_df.columns else "source"
        dst_code_col = "jel_sink" if "jel_sink" in claims_df.columns else "sink"
        is_causal_col = (
            "is_causal_relationship_flag"
            if "is_causal_relationship_flag" in claims_df.columns
            else ("is_causal_relationship" if "is_causal_relationship" in claims_df.columns else None)
        )
        evidence_col = "method_family" if "method_family" in claims_df.columns else (
            "method_class" if "method_class" in claims_df.columns else None
        )
        stability_col = "method_confidence" if "method_confidence" in claims_df.columns else None

        edge_df = pd.DataFrame(
            {
                "paper_id": claims_df["paper_id"].astype(str),
                "src_code": claims_df[src_code_col].astype(str),
                "dst_code": claims_df[dst_code_col].astype(str),
                "relation_type": "claim",
                "evidence_type": claims_df[evidence_col].astype(str) if evidence_col else "unspecified",
                "is_causal": claims_df[is_causal_col] if is_causal_col else False,
                "weight": 1.0,
                "stability": pd.to_numeric(claims_df[stability_col], errors="coerce") if stability_col else pd.NA,
            }
        )
        edge_df = edge_df[
            edge_df["src_code"].notna()
            & edge_df["dst_code"].notna()
            & (edge_df["src_code"].astype(str).str.len() > 0)
            & (edge_df["dst_code"].astype(str).str.len() > 0)
        ].copy()

        if "paper_id" not in papers_df_raw.columns:
            return None
        papers = pd.DataFrame(
            {
                "paper_id": papers_df_raw["paper_id"].astype(str),
                "year": pd.to_numeric(papers_df_raw["year"], errors="coerce").fillna(0).astype(int)
                if "year" in papers_df_raw.columns
                else 0,
                "title": papers_df_raw["title"].astype(str) if "title" in papers_df_raw.columns else "",
                "authors": papers_df_raw["authors"].astype(str) if "authors" in papers_df_raw.columns else "",
                "venue": papers_df_raw["journal"].astype(str) if "journal" in papers_df_raw.columns else "",
                "source": "causalclaims",
            }
        ).drop_duplicates(subset=["paper_id"])

        edge_df = edge_df.merge(papers[["paper_id", "year"]], on="paper_id", how="left")
        edge_df["year"] = pd.to_numeric(edge_df["year"], errors="coerce").fillna(0).astype(int)
        edge_df = edge_df[
            [
                "paper_id",
                "year",
                "src_code",
                "dst_code",
                "relation_type",
                "evidence_type",
                "is_causal",
                "weight",
                "stability",
            ]
        ]

        # Build node labels from most frequent surface forms for each code.
        src_labels = (
            claims_df.assign(src_code=claims_df[src_code_col].astype(str), src_label=claims_df["source"].astype(str))
            .groupby(["src_code", "src_label"], as_index=False)
            .size()
            .sort_values(["src_code", "size"], ascending=[True, False])
            .drop_duplicates(subset=["src_code"])
            .rename(columns={"src_code": "code", "src_label": "label"})[["code", "label"]]
        )
        dst_labels = (
            claims_df.assign(dst_code=claims_df[dst_code_col].astype(str), dst_label=claims_df["sink"].astype(str))
            .groupby(["dst_code", "dst_label"], as_index=False)
            .size()
            .sort_values(["dst_code", "size"], ascending=[True, False])
            .drop_duplicates(subset=["dst_code"])
            .rename(columns={"dst_code": "code", "dst_label": "label"})[["code", "label"]]
        )
        nodes = pd.concat([src_labels, dst_labels], ignore_index=True).drop_duplicates(subset=["code"])
        nodes["label"] = nodes["label"].fillna(nodes["code"]).astype(str)

        self.logs.append(f"Loaded claims/papers bundle from {claims_path.parent}")
        self.logs.append(
            f"Claims bundle rows: edges={len(edge_df)}, papers={papers['paper_id'].nunique()}, nodes={len(nodes)}"
        )
        return AdapterResult(nodes_df=nodes, papers_df=papers, edges_df=edge_df)

    def _load_from_jsonl(self, repo_dir: Path) -> AdapterResult | None:
        jsonl_files = [p for p in repo_dir.rglob("*.jsonl") if ".venv" not in p.parts]
        if not jsonl_files:
            return None
        best_edges: pd.DataFrame | None = None
        for path in jsonl_files:
            try:
                df = pd.read_json(path, lines=True)
            except Exception:  # noqa: BLE001
                continue
            edges = _normalize_edges_columns(df)
            if edges is not None and (best_edges is None or len(edges) > len(best_edges)):
                best_edges = edges
        if best_edges is None:
            return None
        papers = self._derive_papers_from_edges(best_edges)
        nodes = self._derive_nodes_from_edges(best_edges)
        self.logs.append(f"Loaded edge-like claims from JSONL fallback: {len(best_edges)} rows")
        return AdapterResult(nodes_df=nodes, papers_df=papers, edges_df=best_edges)

    @staticmethod
    def _derive_papers_from_edges(edges_df: pd.DataFrame) -> pd.DataFrame:
        papers = (
            edges_df[["paper_id", "year"]]
            .drop_duplicates()
            .assign(title="", authors="", venue="", source="causalclaims")
        )
        return papers

    @staticmethod
    def _derive_nodes_from_edges(edges_df: pd.DataFrame) -> pd.DataFrame:
        src = pd.DataFrame({"code": edges_df["src_code"].astype(str), "label": edges_df["src_code"].astype(str)})
        dst = pd.DataFrame({"code": edges_df["dst_code"].astype(str), "label": edges_df["dst_code"].astype(str)})
        return pd.concat([src, dst], ignore_index=True).drop_duplicates(subset=["code"])
