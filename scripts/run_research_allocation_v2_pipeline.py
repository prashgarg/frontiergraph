from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

from src.analysis.ranking_utils import candidate_cfg_from_config, main_ranking_for_cutoff
from src.utils import load_config, load_corpus


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "data" / "processed" / "research_allocation_v2" / "hybrid_corpus.parquet"
CONFIG_PATH = ROOT / "config" / "config_causalclaims.yaml"
OUTPUTS_ROOT = ROOT / "outputs" / "paper"
BACKTEST_PATH = ROOT / "outputs" / "tables" / "backtest_research_allocation_v2.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the research-allocation v2 paper pipeline on the large normalized benchmark.")
    parser.add_argument("--rebuild-corpus", action="store_true")
    parser.add_argument("--skip-corpus", action="store_true")
    parser.add_argument("--skip-backtest", action="store_true")
    parser.add_argument("--years", type=int, nargs="*", default=[1990, 2000, 2010, 2015])
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def write_config_variant(base_cfg: dict, candidate_kind: str, out_path: Path) -> Path:
    payload = dict(base_cfg)
    payload["filters"] = dict(payload.get("filters", {}))
    payload["filters"]["candidate_kind"] = candidate_kind
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    return out_path


def save_current_candidates(best_config_path: Path, out_path: Path) -> Path:
    corpus = load_corpus(CORPUS_PATH)
    cfg = load_config(CONFIG_PATH)
    best_cfg = candidate_cfg_from_config(cfg, best_config_path=best_config_path)
    cutoff_t = int(corpus["year"].max()) + 1
    ranking = main_ranking_for_cutoff(corpus, cutoff_t=cutoff_t, cfg=best_cfg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ranking.to_parquet(out_path, index=False)
    return out_path


def build_kind_summary(directed_eval_csv: Path, undirected_eval_csv: Path, out_csv: Path, out_md: Path) -> None:
    import pandas as pd

    directed = pd.read_csv(directed_eval_csv).assign(candidate_kind="directed_causal")
    undirected = pd.read_csv(undirected_eval_csv).assign(candidate_kind="undirected_noncausal")
    keep = ["candidate_kind", "model", "horizon", "metric", "mean", "ci_lo", "ci_hi", "n_cutoffs"]
    summary = pd.concat([directed[keep], undirected[keep]], ignore_index=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_csv, index=False)

    lines = ["# Candidate-kind split summary", ""]
    for kind in ["directed_causal", "undirected_noncausal"]:
        sub = summary[(summary["candidate_kind"] == kind) & (summary["model"].isin(["main", "pref_attach"])) & (summary["metric"].isin(["recall_at_100", "mrr"]))].copy()
        if sub.empty:
            continue
        lines.append(f"## {kind}")
        for row in sub.sort_values(["metric", "horizon", "model"]).itertuples(index=False):
            lines.append(
                f"- {row.metric}, h={int(row.horizon)}, {row.model}: mean={float(row.mean):.6f} "
                f"[{float(row.ci_lo):.6f}, {float(row.ci_hi):.6f}]"
            )
        lines.append("")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    years = [str(int(y)) for y in args.years]

    if args.rebuild_corpus or (not args.skip_corpus and not CORPUS_PATH.exists()):
        run([sys.executable, "scripts/build_research_allocation_v2_corpus.py"])

    OUTPUTS_ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
    tmp_cfg_dir = OUTPUTS_ROOT / "00_configs"
    directed_cfg = write_config_variant(load_config(CONFIG_PATH), "directed_causal", tmp_cfg_dir / "config_directed.yaml")
    undirected_cfg = write_config_variant(load_config(CONFIG_PATH), "undirected_noncausal", tmp_cfg_dir / "config_undirected.yaml")

    if not args.skip_backtest:
        run(
            [
                sys.executable,
                "src/backtest.py",
                "--corpus",
                str(CORPUS_PATH),
                "--out",
                str(BACKTEST_PATH),
                "--figdir",
                str(OUTPUTS_ROOT / "01_backtest"),
                "--config",
                str(directed_cfg),
                "--years",
                *years,
            ]
        )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.model_search",
            "--corpus",
            str(CORPUS_PATH),
            "--config",
            str(directed_cfg),
            "--out",
            str(OUTPUTS_ROOT / "03_model_search"),
            "--years",
            *years,
            "--horizons",
            "3,5,10,15",
            "--seed",
            str(args.seed),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.vintage_exercise",
            "--corpus",
            str(CORPUS_PATH),
            "--years",
            *years,
            "--h",
            "10",
            "--k_values",
            "50",
            "100",
            "500",
            "--config",
            str(directed_cfg),
            "--best_config",
            str(OUTPUTS_ROOT / "03_model_search" / "best_config.yaml"),
            "--out",
            str(OUTPUTS_ROOT / "04_vintage_exercise"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.eval_stats",
            "--backtest",
            str(BACKTEST_PATH),
            "--out",
            str(OUTPUTS_ROOT / "02_eval"),
            "--vintage_predictions",
            str(OUTPUTS_ROOT / "04_vintage_exercise" / "vintage_predictions.parquet"),
            "--vintage_realization",
            str(OUTPUTS_ROOT / "04_vintage_exercise" / "vintage_realization.parquet"),
            "--corpus",
            str(CORPUS_PATH),
        ]
    )

    current_candidates = save_current_candidates(
        OUTPUTS_ROOT / "03_model_search" / "best_config.yaml",
        OUTPUTS_ROOT / "04_vintage_exercise" / "current_candidates.parquet",
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.attention_allocation",
            "--corpus",
            str(CORPUS_PATH),
            "--config",
            str(directed_cfg),
            "--best_config",
            str(OUTPUTS_ROOT / "03_model_search" / "best_config.yaml"),
            "--years",
            *years,
            "--horizons",
            "3,5,10,15",
            "--out",
            str(OUTPUTS_ROOT / "07_attention_allocation"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.impact_weighted_eval",
            "--corpus",
            str(CORPUS_PATH),
            "--config",
            str(directed_cfg),
            "--best_config",
            str(OUTPUTS_ROOT / "03_model_search" / "best_config.yaml"),
            "--years",
            *years,
            "--horizons",
            "3,5,10,15",
            "--out",
            str(OUTPUTS_ROOT / "08_impact_weighted"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.gap_boundary",
            "--corpus",
            str(CORPUS_PATH),
            "--config",
            str(directed_cfg),
            "--best_config",
            str(OUTPUTS_ROOT / "03_model_search" / "best_config.yaml"),
            "--years",
            *years,
            "--horizons",
            "3,5,10,15",
            "--out",
            str(OUTPUTS_ROOT / "09_gap_boundary"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.headline_heterogeneity",
            "--corpus",
            str(CORPUS_PATH),
            "--paper_meta",
            str(ROOT / "data" / "processed" / "research_allocation_v2" / "hybrid_papers_funding.parquet"),
            "--config",
            str(directed_cfg),
            "--cutoff-start",
            "1980",
            "--cutoff-end",
            "2020",
            "--cutoff-step",
            "5",
            "--horizons",
            "3,5,10,15,20",
            "--candidate-kinds",
            "directed_causal",
            "undirected_noncausal",
            "--out",
            str(OUTPUTS_ROOT / "13_heterogeneity_atlas"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.path_evolution",
            "--corpus",
            str(CORPUS_PATH),
            "--paper_meta",
            str(ROOT / "data" / "processed" / "research_allocation_v2" / "hybrid_papers_funding.parquet"),
            "--cutoff-start",
            "1980",
            "--cutoff-end",
            "2020",
            "--cutoff-step",
            "5",
            "--horizons",
            "3,5,10,15,20",
            "--out",
            str(OUTPUTS_ROOT / "13_heterogeneity_atlas"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.field_heterogeneity",
            "--corpus",
            str(CORPUS_PATH),
            "--candidates",
            str(current_candidates),
            "--out",
            str(OUTPUTS_ROOT / "06_findings"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.external_transfer_design",
            "--backtest",
            str(BACKTEST_PATH),
            "--out",
            str(OUTPUTS_ROOT / "10_external_transfer_design"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.expert_validation_pack",
            "--corpus",
            str(CORPUS_PATH),
            "--candidates",
            str(current_candidates),
            "--out",
            str(OUTPUTS_ROOT / "11_expert_validation"),
        ]
    )

    run(
        [
            sys.executable,
            "-m",
            "src.analysis.prospective_challenge",
            "--corpus",
            str(CORPUS_PATH),
            "--config",
            str(directed_cfg),
            "--best_config",
            str(OUTPUTS_ROOT / "03_model_search" / "best_config.yaml"),
            "--anchor_year",
            "2016",
            "--horizons",
            "3,5,10",
            "--k_values",
            "100",
            "500",
            "--out",
            str(OUTPUTS_ROOT / "12_prospective_challenge"),
        ]
    )

    undirected_backtest = ROOT / "outputs" / "tables" / "backtest_research_allocation_v2_undirected.parquet"
    undirected_eval_dir = OUTPUTS_ROOT / "02_eval_kind_split" / "undirected"
    directed_eval_dir = OUTPUTS_ROOT / "02_eval_kind_split" / "directed"

    run(
        [
            sys.executable,
            "src/backtest.py",
            "--corpus",
            str(CORPUS_PATH),
            "--out",
            str(undirected_backtest),
            "--figdir",
            str(OUTPUTS_ROOT / "01_backtest_kind_split" / "undirected"),
            "--config",
            str(undirected_cfg),
        ]
    )
    run(
        [
            sys.executable,
            "-m",
            "src.analysis.eval_stats",
            "--backtest",
            str(BACKTEST_PATH),
            "--out",
            str(directed_eval_dir),
            "--corpus",
            str(CORPUS_PATH),
            "--candidate-kind",
            "directed_causal",
        ]
    )
    run(
        [
            sys.executable,
            "-m",
            "src.analysis.eval_stats",
            "--backtest",
            str(undirected_backtest),
            "--out",
            str(undirected_eval_dir),
            "--corpus",
            str(CORPUS_PATH),
            "--candidate-kind",
            "undirected_noncausal",
        ]
    )
    build_kind_summary(
        directed_eval_dir / "main_table_with_ci.csv",
        undirected_eval_dir / "main_table_with_ci.csv",
        OUTPUTS_ROOT / "02_eval" / "candidate_kind_summary.csv",
        OUTPUTS_ROOT / "02_eval" / "candidate_kind_summary.md",
    )

    run([sys.executable, "scripts/build_research_allocation_v2_funding.py"])
    run([sys.executable, "scripts/build_research_allocation_v2_credibility_audit.py"])

    run([sys.executable, "codex_run/generate_slides_assets.py"])


if __name__ == "__main__":
    main()
