from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ARTIFACT_ORDER = ["low", "medium", "high"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze the filled method-v2 human usefulness pack v2."
    )
    parser.add_argument(
        "--filled-sheet",
        default="outputs/paper/129_method_v2_human_usefulness_pack_v2/human_usefulness_blinded_sheet_filled.csv",
        dest="filled_sheet",
    )
    parser.add_argument(
        "--key-csv",
        default="outputs/paper/129_method_v2_human_usefulness_pack_v2/human_usefulness_key.csv",
        dest="key_csv",
    )
    parser.add_argument(
        "--out",
        default="outputs/paper/130_method_v2_human_usefulness_analysis",
        dest="out_dir",
    )
    parser.add_argument(
        "--note",
        default="next_steps/method_v2_human_usefulness_analysis_note.md",
        dest="note_path",
    )
    return parser.parse_args()


def _ensure_dir(path: str | Path) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _normalize_artifact(series: pd.Series) -> pd.Series:
    clean = (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"nan": ""})
    )
    return clean.where(clean.isin(ARTIFACT_ORDER), other=pd.NA)


def _artifact_numeric(series: pd.Series) -> pd.Series:
    mapping = {"low": 1.0, "medium": 2.0, "high": 3.0}
    return series.map(mapping)


def _score_cols() -> list[str]:
    return ["readability_1to5", "interpretability_1to5", "usefulness_1to5"]


def _prepare_df(filled_path: str | Path, key_path: str | Path) -> pd.DataFrame:
    filled = pd.read_csv(filled_path)
    key = pd.read_csv(key_path)
    df = key.merge(filled, on="item_id", how="inner")
    for col in _score_cols():
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["artifact_risk_norm"] = _normalize_artifact(df["artifact_risk_low_medium_high"])
    df["artifact_risk_score"] = _artifact_numeric(df["artifact_risk_norm"])
    df["overall_mean_score"] = df[_score_cols()].mean(axis=1)
    return df


def _summary_by_group(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for group, sub in df.groupby("comparison_group", sort=True):
        row: dict[str, object] = {
            "comparison_group": group,
            "n_rows": int(len(sub)),
            "readability_mean": round(float(sub["readability_1to5"].mean()), 3),
            "interpretability_mean": round(float(sub["interpretability_1to5"].mean()), 3),
            "usefulness_mean": round(float(sub["usefulness_1to5"].mean()), 3),
            "overall_mean_score": round(float(sub["overall_mean_score"].mean()), 3),
            "artifact_risk_mean": round(float(sub["artifact_risk_score"].mean()), 3),
        }
        for level in ARTIFACT_ORDER:
            row[f"artifact_{level}_share"] = round(
                float((sub["artifact_risk_norm"] == level).mean()), 3
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _summary_by_group_horizon(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (group, horizon), sub in df.groupby(["comparison_group", "selection_horizon"], sort=True):
        rows.append(
            {
                "comparison_group": group,
                "selection_horizon": int(horizon),
                "n_rows": int(len(sub)),
                "readability_mean": round(float(sub["readability_1to5"].mean()), 3),
                "interpretability_mean": round(float(sub["interpretability_1to5"].mean()), 3),
                "usefulness_mean": round(float(sub["usefulness_1to5"].mean()), 3),
                "overall_mean_score": round(float(sub["overall_mean_score"].mean()), 3),
                "artifact_risk_mean": round(float(sub["artifact_risk_score"].mean()), 3),
            }
        )
    return pd.DataFrame(rows)


def _threshold_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for group, sub in df.groupby("comparison_group", sort=True):
        row: dict[str, object] = {"comparison_group": group, "n_rows": int(len(sub))}
        for col in _score_cols():
            prefix = col.replace("_1to5", "")
            row[f"{prefix}_ge4_share"] = round(float((sub[col] >= 4).mean()), 3)
            row[f"{prefix}_le2_share"] = round(float((sub[col] <= 2).mean()), 3)
        row["artifact_low_share"] = round(float((sub["artifact_risk_norm"] == "low").mean()), 3)
        row["artifact_high_share"] = round(float((sub["artifact_risk_norm"] == "high").mean()), 3)
        rows.append(row)
    return pd.DataFrame(rows)


def _top_examples(df: pd.DataFrame, group: str, ascending: bool) -> pd.DataFrame:
    sub = df[df["comparison_group"] == group].copy()
    sub = sub.sort_values(
        ["overall_mean_score", "artifact_risk_score", "interpretability_1to5", "readability_1to5"],
        ascending=[ascending, not ascending, ascending, ascending],
    )
    cols = [
        "item_id",
        "selection_horizon",
        "triplet",
        "readability_1to5",
        "interpretability_1to5",
        "usefulness_1to5",
        "artifact_risk_norm",
        "overall_mean_score",
    ]
    return sub[cols].head(5).reset_index(drop=True)


def _write_note(
    path: str | Path,
    df: pd.DataFrame,
    by_group: pd.DataFrame,
    by_group_horizon: pd.DataFrame,
    threshold_summary: pd.DataFrame,
) -> None:
    graph = by_group.loc[by_group["comparison_group"] == "graph_selected"].iloc[0]
    pref = by_group.loc[by_group["comparison_group"] == "pref_attach_selected"].iloc[0]
    graph_t = threshold_summary.loc[threshold_summary["comparison_group"] == "graph_selected"].iloc[0]
    pref_t = threshold_summary.loc[threshold_summary["comparison_group"] == "pref_attach_selected"].iloc[0]
    delta_overall = float(graph["overall_mean_score"] - pref["overall_mean_score"])
    delta_readability = float(graph["readability_mean"] - pref["readability_mean"])
    delta_usefulness = float(graph["usefulness_mean"] - pref["usefulness_mean"])
    delta_interp = float(graph["interpretability_mean"] - pref["interpretability_mean"])
    delta_artifact = float(pref["artifact_risk_mean"] - graph["artifact_risk_mean"])

    lines = [
        "# Method-v2 Human Usefulness Analysis",
        "",
        "## Status",
        "",
        "This note analyzes the filled human usefulness pack. The filled sheet is treated as read-only user input.",
        "",
        "## Main read",
        "",
        f"- total rated rows: `{len(df)}`",
        f"- graph-selected mean overall score: `{graph['overall_mean_score']:.3f}`",
        f"- preferential-attachment mean overall score: `{pref['overall_mean_score']:.3f}`",
        f"- overall-score gap (graph minus preferential attachment): `{delta_overall:.3f}`",
        f"- readability gap: `{delta_readability:.3f}`",
        f"- usefulness gap: `{delta_usefulness:.3f}`",
        f"- interpretability gap: `{delta_interp:.3f}`",
        f"- artifact-risk advantage (preferential attachment minus graph): `{delta_artifact:.3f}`",
        "",
        "The current human ratings are mixed rather than one-sided.",
        "",
        "- There is no overall mean-score gap.",
        "- Graph-selected items do modestly better on interpretability, usefulness, and artifact risk.",
        "- Preferential-attachment items do slightly better on readability.",
        "- The graph-selected set also has a larger share of high-usefulness ratings (`>=4`).",
        "",
        "## Horizon read",
        "",
    ]
    for horizon in sorted(df["selection_horizon"].unique()):
        sub = by_group_horizon[by_group_horizon["selection_horizon"] == horizon].copy()
        if len(sub) != 2:
            continue
        g = sub.loc[sub["comparison_group"] == "graph_selected"].iloc[0]
        p = sub.loc[sub["comparison_group"] == "pref_attach_selected"].iloc[0]
        lines.extend(
            [
                f"- `h={int(horizon)}`",
                f"  - graph overall mean: `{g['overall_mean_score']:.3f}`",
                f"  - pref-attach overall mean: `{p['overall_mean_score']:.3f}`",
                f"  - graph readability mean: `{g['readability_mean']:.3f}`",
                f"  - pref-attach readability mean: `{p['readability_mean']:.3f}`",
                f"  - graph interpretability mean: `{g['interpretability_mean']:.3f}`",
                f"  - pref-attach interpretability mean: `{p['interpretability_mean']:.3f}`",
                f"  - graph usefulness mean: `{g['usefulness_mean']:.3f}`",
                f"  - pref-attach usefulness mean: `{p['usefulness_mean']:.3f}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Threshold view",
            "",
            f"- graph usefulness `>=4` share: `{graph_t['usefulness_ge4_share']:.3f}`",
            f"- pref-attach usefulness `>=4` share: `{pref_t['usefulness_ge4_share']:.3f}`",
            f"- graph artifact-high share: `{graph_t['artifact_high_share']:.3f}`",
            f"- pref-attach artifact-high share: `{pref_t['artifact_high_share']:.3f}`",
            "",
            "## Paper use",
            "",
            "This is the external human usefulness check aligned to the appendix LLM usefulness object. The current result supports a cautious paper claim: graph-selected current-frontier objects look somewhat more interpretable and somewhat less artifact-like than preferential-attachment-selected objects, but the small pack does not support a blanket claim of a large overall human-rated advantage.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = _ensure_dir(args.out_dir)
    df = _prepare_df(args.filled_sheet, args.key_csv)
    by_group = _summary_by_group(df)
    by_group_horizon = _summary_by_group_horizon(df)
    threshold_summary = _threshold_summary(df)

    df.to_csv(out_dir / "human_usefulness_joined.csv", index=False)
    by_group.to_csv(out_dir / "summary_by_group.csv", index=False)
    by_group_horizon.to_csv(out_dir / "summary_by_group_horizon.csv", index=False)
    threshold_summary.to_csv(out_dir / "threshold_summary_by_group.csv", index=False)
    _top_examples(df, "graph_selected", ascending=False).to_csv(
        out_dir / "examples_graph_selected_best.csv", index=False
    )
    _top_examples(df, "graph_selected", ascending=True).to_csv(
        out_dir / "examples_graph_selected_worst.csv", index=False
    )
    _top_examples(df, "pref_attach_selected", ascending=False).to_csv(
        out_dir / "examples_pref_attach_best.csv", index=False
    )
    _top_examples(df, "pref_attach_selected", ascending=True).to_csv(
        out_dir / "examples_pref_attach_worst.csv", index=False
    )

    summary = {
        "n_rows": int(len(df)),
        "graph_selected_n": int((df["comparison_group"] == "graph_selected").sum()),
        "pref_attach_selected_n": int((df["comparison_group"] == "pref_attach_selected").sum()),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_note(args.note_path, df, by_group, by_group_horizon, threshold_summary)


if __name__ == "__main__":
    main()
