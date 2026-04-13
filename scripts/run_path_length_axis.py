from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the path-length axis reproducibly for the research-allocation paper."
    )
    parser.add_argument(
        "--corpus",
        default="data/processed/research_allocation_v2_2_effective/hybrid_corpus.parquet",
        dest="corpus_path",
    )
    parser.add_argument("--config", default="config/config_causalclaims.yaml", dest="config_path")
    parser.add_argument(
        "--best-config",
        default="outputs/paper/03_model_search/best_config.yaml",
        dest="best_config_path",
    )
    parser.add_argument(
        "--base-adopted-configs",
        default="outputs/paper/83_quality_confirm_path_to_direct_effective/adopted_surface_backtest_configs.csv",
        dest="base_adopted_configs_path",
    )
    parser.add_argument(
        "--paper-meta",
        default="data/processed/research_allocation_v2_2_effective/hybrid_papers_funding.parquet",
        dest="paper_meta_path",
    )
    parser.add_argument("--years", default="1990,1995,2000,2005,2010,2015")
    parser.add_argument("--report-years", default="1990,1995,2000,2005,2010,2015", dest="report_years")
    parser.add_argument("--horizons", default="5,10,15")
    parser.add_argument("--pool-size", default="5000", dest="pool_size")
    parser.add_argument("--pool-sizes-reranker", default="5000", dest="pool_sizes_reranker")
    parser.add_argument("--path-lens", default="2,3,4,5", dest="path_lens")
    parser.add_argument("--candidate-family-mode", default="path_to_direct", dest="candidate_family_mode")
    parser.add_argument("--path-to-direct-scope", default="broad", dest="path_to_direct_scope")
    parser.add_argument("--feature-families", default="structural,composition,boundary_gap")
    parser.add_argument("--model-kinds", default="glm_logit,pairwise_logit")
    parser.add_argument("--alphas", default="0.01,0.05,0.10,0.20")
    parser.add_argument("--pairwise-negatives-per-positive", type=int, default=2)
    parser.add_argument("--pairwise-max-pairs-per-cutoff", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out-root",
        required=True,
        dest="out_root",
        help="Root directory that will contain one subdirectory per max_path_len.",
    )
    parser.add_argument(
        "--skip-reranker",
        action="store_true",
        help="Only run the widened benchmark with the base adopted configs.",
    )
    return parser.parse_args()


def _log(msg: str) -> None:
    print(msg, flush=True)


def _run(cmd: list[str], cwd: Path) -> None:
    _log(f"[axis] running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _copy_best_to_adopted(best_path: Path, adopted_path: Path) -> None:
    adopted_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_path, adopted_path)


def main() -> None:
    args = parse_args()
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "corpus_path": args.corpus_path,
        "config_path": args.config_path,
        "best_config_path": args.best_config_path,
        "base_adopted_configs_path": args.base_adopted_configs_path,
        "paper_meta_path": args.paper_meta_path,
        "years": args.years,
        "report_years": args.report_years,
        "horizons": args.horizons,
        "pool_size": args.pool_size,
        "pool_sizes_reranker": args.pool_sizes_reranker,
        "path_lens": args.path_lens,
        "candidate_family_mode": args.candidate_family_mode,
        "path_to_direct_scope": args.path_to_direct_scope,
        "feature_families": args.feature_families,
        "model_kinds": args.model_kinds,
        "alphas": args.alphas,
        "pairwise_negatives_per_positive": args.pairwise_negatives_per_positive,
        "pairwise_max_pairs_per_cutoff": args.pairwise_max_pairs_per_cutoff,
        "seed": args.seed,
        "skip_reranker": bool(args.skip_reranker),
    }
    (out_root / "axis_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    py = sys.executable
    path_lens = [int(x.strip()) for x in str(args.path_lens).split(",") if x.strip()]

    for max_path_len in path_lens:
        label = f"len_{max_path_len}"
        stage_root = out_root / label
        stage_root.mkdir(parents=True, exist_ok=True)
        feature_panel = stage_root / "feature_panel.parquet"
        benchmark_initial = stage_root / "benchmark_initial"
        reranker_tuning = stage_root / "reranker_tuning"
        adopted_configs = stage_root / "adopted_surface_backtest_configs.csv"
        benchmark_tuned = stage_root / "benchmark_tuned"

        _log(f"[axis] === max_path_len={max_path_len} ===")
        _run(
            [
                py,
                "scripts/run_effective_benchmark_widened.py",
                "--corpus",
                args.corpus_path,
                "--config",
                args.config_path,
                "--best-config",
                args.best_config_path,
                "--adopted-configs",
                args.base_adopted_configs_path,
                "--paper-meta",
                args.paper_meta_path,
                "--years",
                args.years,
                "--report-years",
                args.report_years,
                "--horizons",
                args.horizons,
                "--pool-size",
                str(args.pool_size),
                "--feature-panel",
                str(feature_panel),
                "--candidate-family-mode",
                args.candidate_family_mode,
                "--path-to-direct-scope",
                args.path_to_direct_scope,
                "--max-path-len",
                str(max_path_len),
                "--pairwise-negatives-per-positive",
                str(args.pairwise_negatives_per_positive),
                "--pairwise-max-pairs-per-cutoff",
                str(args.pairwise_max_pairs_per_cutoff),
                "--seed",
                str(args.seed),
                "--out",
                str(benchmark_initial),
            ],
            cwd=ROOT,
        )

        if args.skip_reranker:
            continue

        _run(
            [
                py,
                "scripts/run_learned_reranker_tuning.py",
                "--corpus",
                args.corpus_path,
                "--config",
                args.config_path,
                "--best_config",
                args.best_config_path,
                "--paper_meta",
                args.paper_meta_path,
                "--feature-panel",
                str(feature_panel),
                "--years",
                *[y.strip() for y in str(args.years).split(",") if y.strip()],
                "--horizons",
                args.horizons,
                "--pool_sizes",
                args.pool_sizes_reranker,
                "--feature_families",
                args.feature_families,
                "--model_kinds",
                args.model_kinds,
                "--alphas",
                args.alphas,
                "--candidate-family-mode",
                args.candidate_family_mode,
                "--path-to-direct-scope",
                args.path_to_direct_scope,
                "--max-path-len",
                str(max_path_len),
                "--pairwise_negatives_per_positive",
                str(args.pairwise_negatives_per_positive),
                "--pairwise_max_pairs_per_cutoff",
                str(args.pairwise_max_pairs_per_cutoff),
                "--seed",
                str(args.seed),
                "--out",
                str(reranker_tuning),
            ],
            cwd=ROOT,
        )

        best_path = reranker_tuning / "tuning_best_configs.csv"
        if not best_path.exists():
            raise FileNotFoundError(f"Missing tuned configs for max_path_len={max_path_len}: {best_path}")
        _copy_best_to_adopted(best_path, adopted_configs)

        _run(
            [
                py,
                "scripts/run_effective_benchmark_widened.py",
                "--corpus",
                args.corpus_path,
                "--config",
                args.config_path,
                "--best-config",
                args.best_config_path,
                "--adopted-configs",
                str(adopted_configs),
                "--paper-meta",
                args.paper_meta_path,
                "--years",
                args.years,
                "--report-years",
                args.report_years,
                "--horizons",
                args.horizons,
                "--pool-size",
                str(args.pool_size),
                "--feature-panel",
                str(feature_panel),
                "--candidate-family-mode",
                args.candidate_family_mode,
                "--path-to-direct-scope",
                args.path_to_direct_scope,
                "--max-path-len",
                str(max_path_len),
                "--pairwise-negatives-per-positive",
                str(args.pairwise_negatives_per_positive),
                "--pairwise-max-pairs-per-cutoff",
                str(args.pairwise_max_pairs_per_cutoff),
                "--seed",
                str(args.seed),
                "--out",
                str(benchmark_tuned),
            ],
            cwd=ROOT,
        )


if __name__ == "__main__":
    main()
