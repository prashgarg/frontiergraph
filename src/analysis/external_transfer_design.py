from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.common import ensure_output_dir


def build_external_dataset_options() -> pd.DataFrame:
    rows = [
        {
            "dataset": "OpenAlex (economics-tagged works)",
            "edge_proxy": "Concept-claim links from abstracts/full text mapped to node codes",
            "coverage": "Global, broad disciplinary spread, yearly updates",
            "latency": "Low-to-moderate",
            "horizon_suitability": "3/5/10/15",
            "strengths": "Scale, metadata richness, temporal depth",
            "risks": "Noisy concept mapping, field-tag ambiguity",
            "identification_caveat": "Prediction gains may partly reflect metadata coverage differences",
        },
        {
            "dataset": "RePEc/IDEAS + NBER",
            "edge_proxy": "Working-paper to journal diffusion of claim links",
            "coverage": "Economics-focused, strong institutional curation",
            "latency": "Moderate",
            "horizon_suitability": "5/10/15",
            "strengths": "Field relevance, publication pipeline traceability",
            "risks": "Licensing and parser heterogeneity",
            "identification_caveat": "Working paper selection may induce composition shifts",
        },
        {
            "dataset": "IMF/World Bank/OECD working papers",
            "edge_proxy": "Policy-research claim diffusion edges",
            "coverage": "Policy-econ thematic domains",
            "latency": "Moderate-to-high",
            "horizon_suitability": "5/10/15",
            "strengths": "Policy salience and external validity for applied economics",
            "risks": "Domain bias and style heterogeneity",
            "identification_caveat": "Institution-specific author networks may affect edge formation",
        },
        {
            "dataset": "USPTO/PatentsView (linked to science)",
            "edge_proxy": "Technology-claim combination and follow-on citation realization",
            "coverage": "Long-run innovation outcomes",
            "latency": "High",
            "horizon_suitability": "10/15+",
            "strengths": "Best setting for supply-creates-demand tests",
            "risks": "Claim mapping complexity, legal text idiosyncrasies",
            "identification_caveat": "Patenting propensity varies strongly by sector and period",
        },
    ]
    return pd.DataFrame(rows)


def build_horizon_options() -> pd.DataFrame:
    rows = [
        {
            "horizon_set": "1/3/5",
            "field_rationale": "Fast-moving fields or broad STEM transfer checks",
            "pros": "Quick feedback loop, more cutoffs",
            "risks": "May undercount slow economics diffusion",
            "recommended_use": "Sensitivity check only for economics",
        },
        {
            "horizon_set": "3/5/10/15",
            "field_rationale": "Economics publication and diffusion cycles are slower",
            "pros": "Closer to substantive timing of field adoption",
            "risks": "Fewer eligible cutoffs at long horizons",
            "recommended_use": "Primary economics specification",
        },
    ]
    return pd.DataFrame(rows)


def _required_n(delta: float, std: float, alpha: float = 0.05, power: float = 0.80) -> float:
    if not np.isfinite(delta) or not np.isfinite(std) or std <= 0 or abs(delta) <= 1e-12:
        return float("inf")
    # Normal approximation for paired mean difference.
    z_alpha = 1.96 if math.isclose(alpha, 0.05) else 1.96
    z_beta = 0.84 if math.isclose(power, 0.80) else 0.84
    return ((z_alpha + z_beta) * std / abs(delta)) ** 2


def transfer_power_calibration(backtest_df: pd.DataFrame) -> pd.DataFrame:
    if backtest_df.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for horizon in sorted(backtest_df["horizon"].dropna().unique()):
        m = backtest_df[(backtest_df["model"] == "main") & (backtest_df["horizon"] == horizon)]
        p = backtest_df[(backtest_df["model"] == "pref_attach") & (backtest_df["horizon"] == horizon)]
        if m.empty or p.empty:
            continue
        joined = m[["cutoff_year_t", "recall_at_100", "mrr"]].merge(
            p[["cutoff_year_t", "recall_at_100", "mrr"]],
            on="cutoff_year_t",
            suffixes=("_main", "_pref"),
            how="inner",
        )
        if joined.empty:
            continue
        for metric in ["recall_at_100", "mrr"]:
            delta = joined[f"{metric}_main"] - joined[f"{metric}_pref"]
            mean_delta = float(delta.mean())
            std_delta = float(delta.std(ddof=1)) if len(delta) > 1 else float("nan")
            eff = float(mean_delta / std_delta) if np.isfinite(std_delta) and std_delta > 0 else np.nan
            n_req = _required_n(mean_delta, std_delta)
            rows.append(
                {
                    "horizon": int(horizon),
                    "metric": metric,
                    "n_cutoffs_observed": int(len(joined)),
                    "observed_mean_delta": mean_delta,
                    "observed_std_delta": std_delta,
                    "effect_size_d": eff,
                    "required_n_for_80pct_power": float(np.ceil(n_req)) if np.isfinite(n_req) else np.inf,
                    "feasible_with_current_n": bool(np.isfinite(n_req) and len(joined) >= n_req),
                }
            )
    return pd.DataFrame(rows)


def plot_power_requirements(power_df: pd.DataFrame, out_path: Path) -> None:
    if power_df.empty:
        return
    sub = power_df.copy()
    sub = sub[np.isfinite(sub["required_n_for_80pct_power"])]
    if sub.empty:
        return
    labels = [f"h{int(r.horizon)}-{r.metric}" for r in sub.itertuples(index=False)]
    vals = sub["required_n_for_80pct_power"].astype(float).tolist()
    plt.figure(figsize=(10, 5))
    plt.bar(labels, vals, color="tab:green")
    plt.ylabel("Required paired cutoffs for 80% power")
    plt.title("External Transfer Design: Approximate Sample Size Targets")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def write_protocol_markdown(
    options_df: pd.DataFrame,
    horizon_df: pd.DataFrame,
    power_df: pd.DataFrame,
    out_path: Path,
) -> None:
    lines = [
        "# Workstream 10: External Transfer Design Protocol",
        "",
        "## Core Claim Discipline",
        "- Internal evidence establishes predictive utility in the source corpus.",
        "- External exercise tests transferability, not guaranteed universal superiority.",
        "",
        "## Testable Hypotheses",
        "1. Main model preserves positive lift vs preferential attachment in at least one external economics corpus.",
        "2. Transfer performance is stronger at longer horizons (3/5/10/15) for economics.",
        "3. Patent-transfer setting can reveal boundary links whose demand appears only later (supply-creates-demand).",
        "",
        "## Dataset Options",
        options_df.to_markdown(index=False) if not options_df.empty else "- none",
        "",
        "## Horizon Design",
        horizon_df.to_markdown(index=False) if not horizon_df.empty else "- none",
        "",
        "## Power Calibration from Internal Variance",
        power_df.to_markdown(index=False) if not power_df.empty else "- unavailable",
        "",
        "## Execution Ladder",
        "1. Replicate internal protocol with fixed lockbox years and frozen weights.",
        "2. Port schema and mapping to one external economics corpus.",
        "3. Run paired main-vs-pref evaluation with pre-registered metrics.",
        "4. Extend to patent setting for supply-creates-demand boundary test.",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate external validation/transfer design artifacts.")
    parser.add_argument("--backtest", required=True, dest="backtest_path")
    parser.add_argument("--out", required=True, dest="out_dir")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_output_dir(args.out_dir)
    backtest_df = pd.read_parquet(args.backtest_path)
    options_df = build_external_dataset_options()
    horizon_df = build_horizon_options()
    power_df = transfer_power_calibration(backtest_df)
    power_fig = out_dir / "transfer_power_targets.png"
    plot_power_requirements(power_df, power_fig)
    protocol_md = out_dir / "protocol.md"
    write_protocol_markdown(options_df, horizon_df, power_df, protocol_md)

    options_csv = out_dir / "external_dataset_options.csv"
    horizon_csv = out_dir / "horizon_design_options.csv"
    power_csv = out_dir / "transfer_power_calibration.csv"

    options_df.to_csv(options_csv, index=False)
    horizon_df.to_csv(horizon_csv, index=False)
    power_df.to_csv(power_csv, index=False)

    print(f"Wrote: {options_csv}")
    print(f"Wrote: {horizon_csv}")
    print(f"Wrote: {power_csv}")
    print(f"Wrote: {protocol_md}")
    if power_fig.exists():
        print(f"Wrote figure: {power_fig}")


if __name__ == "__main__":
    main()
