#!/usr/bin/env python3
"""Build Frontier Graph AI-mentions time-series and branded charts."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import pandas as pd


DEFAULT_EXTRACTION_DB = Path(
    "data/production/frontiergraph_extraction_v2/fwci_core150_adj150/merged/fwci_core150_adj150_extractions.sqlite"
)
DEFAULT_OPENALEX_DB = Path("data/processed/openalex/published_enriched/openalex_published_enriched.sqlite")
DEFAULT_ANALYSIS_DIR = Path("outputs/analysis")
DEFAULT_FIGURES_DIR = Path("outputs/figures")

CHATGPT_RELEASE = pd.Timestamp("2022-11-30")

BACKGROUND = "#FAF7F2"
TEXT = "#152238"
GRID = "#DED8CF"
AXIS = "#9A8F84"
MONTHLY = "#79D3E1"
ROLLING = "#24539A"
CORE = "#24539A"
ADJACENT = "#138B8F"
ACCENT = "#295D5F"
SUBTEXT = "#5D5A56"

@dataclass(frozen=True)
class TermSpec:
    label: str
    pattern: str


TERM_SPECS = [
    TermSpec("artificial intelligence", r"\bartificial intelligence\b"),
    TermSpec("large language model", r"\blarge language models?\b"),
    TermSpec("generative ai", r"\bgenerative ai\b"),
    TermSpec("generative artificial intelligence", r"\bgenerative artificial intelligence\b"),
    TermSpec("chatgpt", r"\bchatgpt\b"),
    TermSpec("deep learning", r"\bdeep learning\b"),
    TermSpec("neural network", r"\bneural networks?\b"),
    TermSpec("bert", r"\bbert\b"),
    TermSpec("transformer", r"\btransformers?\b"),
    TermSpec("gpt model family", r"\bgpt(?:[- ]?(?:2|3|4|4o|4\.5|5))\b"),
]


VARIANT_DESCRIPTIONS = {
    "all": "Full Frontier Graph screened corpus",
    "core": "Core economics journals in the screened corpus",
    "adjacent": "Adjacent journals in the screened corpus",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction-db", type=Path, default=DEFAULT_EXTRACTION_DB)
    parser.add_argument("--openalex-db", type=Path, default=DEFAULT_OPENALEX_DB)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    parser.add_argument("--plot-start", default="2015-01-01")
    parser.add_argument("--plot-end", default=None)
    return parser.parse_args()


def build_regex() -> re.Pattern[str]:
    return re.compile("|".join(spec.pattern for spec in TERM_SPECS), re.I)


def month_range(counter: Counter[str]) -> pd.DatetimeIndex:
    return pd.date_range(min(counter), max(counter), freq="MS")


def build_series_frame(totals: Counter[str], mentions: Counter[str]) -> pd.DataFrame:
    months = month_range(totals)
    df = pd.DataFrame({"month": months})
    df["month_str"] = df["month"].dt.strftime("%Y-%m")
    df["paper_count"] = df["month_str"].map(totals).fillna(0).astype(int)
    df["mention_count"] = df["month_str"].map(mentions).fillna(0).astype(int)
    df["share_pct"] = 0.0
    nonzero = df["paper_count"] > 0
    df.loc[nonzero, "share_pct"] = (
        df.loc[nonzero, "mention_count"] / df.loc[nonzero, "paper_count"] * 100
    )
    df["rolling_12m_pct"] = df["share_pct"].rolling(window=12, min_periods=1).mean()
    return df


def trim_partial_last_month(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    if len(df) < 7:
        return df, False
    last_count = int(df.iloc[-1]["paper_count"])
    prior_median = float(df.iloc[-7:-1]["paper_count"].median())
    if prior_median > 0 and last_count < 0.5 * prior_median:
        return df.iloc[:-1].copy(), True
    return df, False


def load_variant_series(
    extraction_db_path: Path, openalex_db_path: Path, pattern: re.Pattern[str]
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, int | bool]]]:
    conn = sqlite3.connect(extraction_db_path)
    conn.execute("ATTACH DATABASE ? AS oa", (str(openalex_db_path),))
    cursor = conn.execute(
        """
        SELECT
            oa.publication_date,
            fg.bucket,
            fg.source_display_name,
            fg.title,
            fg.abstract
        FROM works AS fg
        LEFT JOIN oa.works_base AS oa
          ON fg.openalex_work_id = oa.work_id
        WHERE oa.publication_date IS NOT NULL
          AND oa.publication_date != ''
          AND COALESCE(oa.is_retracted, 0) = 0
          AND COALESCE(oa.is_paratext, 0) = 0
        ORDER BY oa.publication_date
        """
    )

    totals = defaultdict(Counter)
    mentions = defaultdict(Counter)
    stats = {
        "all": Counter(),
        "core": Counter(),
        "adjacent": Counter(),
    }

    for publication_date, bucket, source_display_name, title, abstract_text in cursor:
        month = str(publication_date)[:7]
        if len(month) != 7:
            continue
        text = f"{title or ''} {abstract_text or ''}"
        is_match = bool(pattern.search(text))

        variants = ["all"]
        if bucket in ("core", "adjacent"):
            variants.append(bucket)

        for variant in variants:
            totals[variant][month] += 1
            stats[variant]["rows_seen"] += 1
            if is_match:
                mentions[variant][month] += 1
                stats[variant]["rows_matched"] += 1

    conn.close()

    frames: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict[str, int | bool]] = {}
    for variant in ["all", "core", "adjacent"]:
        df = build_series_frame(totals[variant], mentions[variant])
        trimmed_df, trimmed = trim_partial_last_month(df)
        frames[variant] = df
        metadata[variant] = {
            "rows_seen": int(stats[variant]["rows_seen"]),
            "rows_matched": int(stats[variant]["rows_matched"]),
            "plot_trimmed_partial_last_month": trimmed,
            "plot_end_month": trimmed_df.iloc[-1]["month"].strftime("%Y-%m-%d"),
        }
    return frames, metadata


def write_series_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["month", "paper_count", "mention_count", "share_pct", "rolling_12m_pct"])
        for row in df.itertuples(index=False):
            writer.writerow(
                [
                    row.month.strftime("%Y-%m-%d"),
                    int(row.paper_count),
                    int(row.mention_count),
                    float(row.share_pct),
                    float(row.rolling_12m_pct),
                ]
            )


def style_axis(ax: plt.Axes, *, ymax: float) -> None:
    ax.set_facecolor(BACKGROUND)
    ax.grid(axis="y", color=GRID, linewidth=1.0)
    ax.grid(axis="x", visible=False)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.spines["bottom"].set_linewidth(1.1)
    ax.tick_params(axis="both", colors="#6A625C", labelsize=12, length=0)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(0, ymax)


def filtered_plot_df(df: pd.DataFrame, plot_start: str, plot_end: str | None) -> tuple[pd.DataFrame, bool]:
    trimmed_df, trimmed = trim_partial_last_month(df)
    filtered = trimmed_df[trimmed_df["month"] >= pd.Timestamp(plot_start)].copy()
    if plot_end:
        filtered = filtered[filtered["month"] <= pd.Timestamp(plot_end)]
    return filtered, trimmed


def add_branding(fig: plt.Figure) -> None:
    fig.lines.append(
        Line2D(
            [0.065, 0.14],
            [0.95, 0.95],
            transform=fig.transFigure,
            color=ACCENT,
            linewidth=4.5,
            solid_capstyle="round",
        )
    )


def save_figure(fig: plt.Figure, png_path: Path, svg_path: Path) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, facecolor=BACKGROUND)
    fig.savefig(svg_path, facecolor=BACKGROUND)
    plt.close(fig)


def plot_single_series(
    df: pd.DataFrame,
    *,
    title: str,
    subtitle: str,
    footnote: str,
    png_path: Path,
    svg_path: Path,
    plot_start: str,
    plot_end: str | None,
) -> None:
    plot_df, _trimmed = filtered_plot_df(df, plot_start, plot_end)

    fig = plt.figure(figsize=(8.2, 10.6), dpi=220)
    fig.patch.set_facecolor(BACKGROUND)
    ax = fig.add_axes([0.12, 0.235, 0.72, 0.525])

    ax.plot(plot_df["month"], plot_df["share_pct"], color=MONTHLY, linewidth=3.3, zorder=2)
    ax.plot(plot_df["month"], plot_df["rolling_12m_pct"], color=ROLLING, linewidth=3.6, zorder=3)

    ymax = max(plot_df["share_pct"].max(), plot_df["rolling_12m_pct"].max()) * 1.18
    style_axis(ax, ymax=ymax)
    ax.set_xlim(plot_df["month"].min(), plot_df["month"].max() + pd.DateOffset(months=10))

    ax.axvline(CHATGPT_RELEASE, color=TEXT, linestyle=":", linewidth=2.0, zorder=1)
    ax.text(
        CHATGPT_RELEASE - pd.Timedelta(days=32),
        ymax * 0.89,
        "ChatGPT\nreleased",
        ha="right",
        va="top",
        color=TEXT,
        fontsize=12.5,
    )

    add_branding(fig)
    fig.text(0.065, 0.885, title, fontsize=23, color=TEXT, linespacing=1.08)
    fig.text(0.065, 0.825, subtitle, fontsize=15.5, color=SUBTEXT, linespacing=1.28)

    last_row = plot_df.iloc[-1]
    monthly_y = min(float(last_row["share_pct"]) + 0.18, ymax * 0.92)
    rolling_y = max(float(last_row["rolling_12m_pct"]) - 0.1, 0.15)
    if monthly_y - rolling_y < 0.5:
        monthly_y = min(monthly_y + 0.25, ymax * 0.94)
        rolling_y = max(rolling_y - 0.2, 0.1)
    if monthly_y < 0.45 and rolling_y < 0.45:
        rolling_y = 0.22
        monthly_y = 0.58
    label_x = plot_df["month"].max() + pd.DateOffset(days=34)

    ax.text(label_x, monthly_y, "monthly\nshare", color=TEXT, fontsize=14.5, weight="bold", va="center")
    ax.text(
        label_x,
        rolling_y,
        "12-month\nrolling\naverage",
        color=TEXT,
        fontsize=14.5,
        weight="bold",
        va="center",
    )

    fig.text(0.065, 0.082, footnote, fontsize=11.3, color=SUBTEXT, linespacing=1.42)
    save_figure(fig, png_path, svg_path)


def plot_comparison_series(
    core_df: pd.DataFrame,
    adjacent_df: pd.DataFrame,
    *,
    title: str,
    subtitle: str,
    footnote: str,
    png_path: Path,
    svg_path: Path,
    plot_start: str,
    plot_end: str | None,
) -> None:
    core_plot, _ = filtered_plot_df(core_df, plot_start, plot_end)
    adjacent_plot, _ = filtered_plot_df(adjacent_df, plot_start, plot_end)

    fig = plt.figure(figsize=(8.2, 10.6), dpi=220)
    fig.patch.set_facecolor(BACKGROUND)
    ax = fig.add_axes([0.12, 0.235, 0.72, 0.525])

    ax.plot(adjacent_plot["month"], adjacent_plot["rolling_12m_pct"], color=ADJACENT, linewidth=3.6, zorder=2)
    ax.plot(core_plot["month"], core_plot["rolling_12m_pct"], color=CORE, linewidth=3.6, zorder=3)

    ymax = max(adjacent_plot["rolling_12m_pct"].max(), core_plot["rolling_12m_pct"].max()) * 1.22
    style_axis(ax, ymax=ymax)
    ax.set_xlim(core_plot["month"].min(), core_plot["month"].max() + pd.DateOffset(months=11))

    ax.axvline(CHATGPT_RELEASE, color=TEXT, linestyle=":", linewidth=2.0, zorder=1)
    ax.text(
        CHATGPT_RELEASE - pd.Timedelta(days=32),
        ymax * 0.89,
        "ChatGPT\nreleased",
        ha="right",
        va="top",
        color=TEXT,
        fontsize=12.5,
    )

    add_branding(fig)
    fig.text(0.065, 0.885, title, fontsize=23, color=TEXT, linespacing=1.08)
    fig.text(0.065, 0.825, subtitle, fontsize=15.5, color=SUBTEXT, linespacing=1.28)

    core_last = core_plot.iloc[-1]
    adjacent_last = adjacent_plot.iloc[-1]
    label_x = core_plot["month"].max() + pd.DateOffset(days=38)
    core_y = float(core_last["rolling_12m_pct"]) + 0.08
    adjacent_y = float(adjacent_last["rolling_12m_pct"]) - 0.08
    if abs(core_y - adjacent_y) < 0.38:
        core_y += 0.22
        adjacent_y -= 0.22

    ax.text(label_x, core_y, "core", color=CORE, fontsize=14.5, weight="bold", va="center")
    ax.text(label_x, adjacent_y, "adjacent", color=ADJACENT, fontsize=14.5, weight="bold", va="center")

    fig.text(0.065, 0.082, footnote, fontsize=11.3, color=SUBTEXT, linespacing=1.42)
    save_figure(fig, png_path, svg_path)


def write_metadata(
    path: Path,
    frames: dict[str, pd.DataFrame],
    metadata: dict[str, dict[str, int | bool]],
    extraction_db_path: Path,
    openalex_db_path: Path,
) -> None:
    payload = {
        "source_extraction_db": str(extraction_db_path),
        "source_openalex_db": str(openalex_db_path),
        "corpus_filter": {
            "corpus": "Frontier Graph screened published-paper corpus",
            "screened_work_count_target": 242595,
            "exclude_retracted": True,
            "exclude_paratext": True,
            "require_publication_date": True,
        },
        "term_labels": [spec.label for spec in TERM_SPECS],
        "term_patterns": [spec.pattern for spec in TERM_SPECS],
        "variants": {},
    }
    for variant, df in frames.items():
        payload["variants"][variant] = {
            "description": VARIANT_DESCRIPTIONS[variant],
            "rows_seen": int(metadata[variant]["rows_seen"]),
            "rows_matched": int(metadata[variant]["rows_matched"]),
            "date_min": df["month"].min().strftime("%Y-%m-%d"),
            "date_max": df["month"].max().strftime("%Y-%m-%d"),
            "last_month_share_pct": float(df.iloc[-1]["share_pct"]),
            "last_rolling_12m_pct": float(df.iloc[-1]["rolling_12m_pct"]),
            "plot_trimmed_partial_last_month": bool(metadata[variant]["plot_trimmed_partial_last_month"]),
            "plot_end_month": str(metadata[variant]["plot_end_month"]),
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    pattern = build_regex()
    frames, metadata = load_variant_series(args.extraction_db, args.openalex_db, pattern)

    csv_paths = {
        "all": args.analysis_dir / "frontiergraph_ai_mentions_monthly.csv",
        "core": args.analysis_dir / "frontiergraph_ai_mentions_monthly_core.csv",
        "adjacent": args.analysis_dir / "frontiergraph_ai_mentions_monthly_adjacent.csv",
    }
    for variant, path in csv_paths.items():
        write_series_csv(path, frames[variant])

    plot_single_series(
        frames["all"],
        title="AI-related terms in published economics papers",
        subtitle="Monthly share of papers mentioning selected AI-related\nterms in their title or abstract",
        footnote=(
            "Source: Frontier Graph published-journal corpus\n"
            "* Terms include artificial intelligence, large language model, generative AI,\n"
            "ChatGPT, deep learning, neural network, BERT, transformer, and GPT model-family mentions."
        ),
        png_path=args.figures_dir / "frontiergraph_ai_mentions_share.png",
        svg_path=args.figures_dir / "frontiergraph_ai_mentions_share.svg",
        plot_start=args.plot_start,
        plot_end=args.plot_end,
    )

    plot_comparison_series(
        frames["core"],
        frames["adjacent"],
        title="AI-related terms in core and adjacent journals",
        subtitle="12-month rolling share of published papers mentioning selected\nAI-related terms",
        footnote=(
            "Source: Frontier Graph screened corpus\n"
            "* Core and adjacent follow the project's published-journal bucket definitions."
        ),
        png_path=args.figures_dir / "frontiergraph_ai_mentions_core_vs_adjacent.png",
        svg_path=args.figures_dir / "frontiergraph_ai_mentions_core_vs_adjacent.svg",
        plot_start=args.plot_start,
        plot_end=args.plot_end,
    )

    write_metadata(
        args.analysis_dir / "frontiergraph_ai_mentions_metadata.json",
        frames,
        metadata,
        args.extraction_db,
        args.openalex_db,
    )

    print(
        json.dumps(
            {
                "variants": {
                    variant: {
                        "rows_seen": metadata[variant]["rows_seen"],
                        "rows_matched": metadata[variant]["rows_matched"],
                        "last_rolling_12m_pct": round(float(frames[variant].iloc[-1]["rolling_12m_pct"]), 3),
                    }
                    for variant in ["all", "core", "adjacent"]
                },
                "csv_outputs": {key: str(path) for key, path in csv_paths.items()},
                "figure_outputs": {
                    "main": str(args.figures_dir / "frontiergraph_ai_mentions_share.png"),
                    "core_vs_adjacent": str(args.figures_dir / "frontiergraph_ai_mentions_core_vs_adjacent.png"),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
