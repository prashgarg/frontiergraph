#!/usr/bin/env python3
"""Build AI-mentions time-series and charts for the published Frontier Graph corpus."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
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
DEFAULT_SOURCE_LIST_DIR = Path("data/production/frontiergraph_extraction_v2/fwci_core150_adj150/source_lists")
DEFAULT_ANALYSIS_DIR = Path("outputs/analysis")
DEFAULT_FIGURES_DIR = Path("outputs/figures")

CHATGPT_RELEASE = pd.Timestamp("2022-11-30")

BACKGROUND = "#F4F8FB"
PANEL = "#FFFFFF"
TEXT = "#18324A"
SUBTEXT = "#627588"
GRID = "#D8E3EC"
AXIS = "#93A6B8"
MONTHLY = "#8FD7E8"
ROLLING = "#137C82"
CORE = "#24539A"
ADJACENT = "#1A9A8C"
ACCENT = "#2F7E86"
MUTED = "#8396A8"
CORE_CUTOFF_COLORS = {50: "#163B7A", 100: "#3F6CB7", 150: "#9FB9E3"}
ADJ_CUTOFF_COLORS = {50: "#116A6C", 100: "#24A09A", 150: "#A4E0DB"}
FIELD_LINE = "#24539A"


@dataclass(frozen=True)
class TermSpec:
    label: str
    pattern: str


@dataclass(frozen=True)
class FieldSpec:
    slug: str
    label: str
    patterns: tuple[str, ...]


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

FIELD_SPECS = [
    FieldSpec(
        "labour",
        "Labour",
        (
            r"\blabo[u]?r market\b",
            r"\bwage inequality\b",
            r"\bunemployment\b",
            r"\boccupational licensing\b",
            r"\bemployment\b",
        ),
    ),
    FieldSpec(
        "macro",
        "Macro",
        (
            r"\bmacroeconomic\b",
            r"\bmonetary\b",
            r"\binflation\b",
            r"\bbusiness cycle\b",
            r"\boil price shocks?\b",
            r"\bglobal economy\b",
            r"\bokun'?s law\b",
            r"\bmacroeconomics?\b",
        ),
    ),
    FieldSpec(
        "public_finance",
        "Public finance",
        (
            r"\btax(?:ation)?\b",
            r"\btax evasion\b",
            r"\bfiscal\b",
            r"\bpublic finance\b",
            r"\bgovernment spending\b",
            r"\bsubsid(?:y|ies)\b",
        ),
    ),
    FieldSpec(
        "trade",
        "Trade",
        (
            r"\btrade\b",
            r"\btariff",
            r"\bexport",
            r"\bimport",
            r"\beconomic sanctions?\b",
        ),
    ),
    FieldSpec(
        "development",
        "Development",
        (
            r"\bdevelopment\b",
            r"\bpoverty\b",
            r"\bmicrofinance\b",
            r"\bfinancial inclusion\b",
            r"\bspecial economic zones?\b",
            r"\bresource curse\b",
        ),
    ),
    FieldSpec(
        "finance",
        "Finance",
        (
            r"\basset pricing\b",
            r"\bbanking\b",
            r"\bmortgage\b",
            r"\bcapital flows?\b",
            r"\bvolatility\b",
            r"\boption pricing\b",
            r"\bcredit risk\b",
            r"\bfinancialization\b",
            r"\bfinancial markets?\b",
            r"\binvestment\b",
        ),
    ),
    FieldSpec(
        "health",
        "Health",
        (
            r"\bhealth care\b",
            r"\bhealthcare\b",
            r"\bhealth economics?\b",
            r"\bhealth systems?\b",
            r"\bpharmaceutical\b",
            r"\bcancer treatment\b",
            r"\bquality of life\b",
        ),
    ),
    FieldSpec(
        "environment_energy",
        "Environment and energy",
        (
            r"\benvironment",
            r"\bclimate\b",
            r"\benergy\b",
            r"\brenewable\b",
            r"\bgreen bonds?\b",
            r"\bresources?\b",
        ),
    ),
]

FIELD_REGEX = {
    spec.slug: [re.compile(pattern, re.I) for pattern in spec.patterns] for spec in FIELD_SPECS
}

VARIANT_DESCRIPTIONS = {
    "all": "Full screened published-paper corpus",
    "core": "Core economics journals in the screened corpus",
    "adjacent": "Adjacent journals in the screened corpus",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction-db", type=Path, default=DEFAULT_EXTRACTION_DB)
    parser.add_argument("--openalex-db", type=Path, default=DEFAULT_OPENALEX_DB)
    parser.add_argument("--source-list-dir", type=Path, default=DEFAULT_SOURCE_LIST_DIR)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    parser.add_argument("--plot-start", default="2015-01-01")
    parser.add_argument("--plot-end", default=None)
    return parser.parse_args()


def build_regex() -> str:
    return "|".join(spec.pattern for spec in TERM_SPECS)


def assign_major_field(topic: str | None) -> str | None:
    if not topic:
        return None
    haystack = str(topic).strip().lower()
    if not haystack:
        return None
    for spec in FIELD_SPECS:
        if any(pattern.search(haystack) for pattern in FIELD_REGEX[spec.slug]):
            return spec.slug
    return None


def load_paper_frame(extraction_db_path: Path, openalex_db_path: Path, pattern: str) -> pd.DataFrame:
    conn = sqlite3.connect(extraction_db_path)
    conn.execute("ATTACH DATABASE ? AS oa", (str(openalex_db_path),))
    query = """
        SELECT
            oa.publication_date,
            fg.publication_year,
            fg.bucket,
            fg.source_id,
            fg.source_display_name,
            oa.primary_topic_display_name,
            fg.title,
            fg.abstract
        FROM works AS fg
        LEFT JOIN oa.works_base AS oa
          ON fg.openalex_work_id = oa.work_id
        WHERE oa.publication_date IS NOT NULL
          AND oa.publication_date != ''
          AND COALESCE(oa.is_retracted, 0) = 0
          AND COALESCE(oa.is_paratext, 0) = 0
          AND fg.bucket IN ('core', 'adjacent')
        ORDER BY oa.publication_date
    """
    frame = pd.read_sql_query(query, conn)
    conn.close()

    frame["publication_date"] = pd.to_datetime(frame["publication_date"], errors="coerce")
    frame = frame[frame["publication_date"].notna()].copy()
    frame["month"] = frame["publication_date"].dt.to_period("M").dt.to_timestamp()
    frame["text"] = frame["title"].fillna("") + " " + frame["abstract"].fillna("")
    frame["is_match"] = frame["text"].str.contains(pattern, case=False, regex=True, na=False)
    frame["major_field"] = frame["primary_topic_display_name"].map(assign_major_field)
    frame.drop(columns=["text"], inplace=True)
    return frame


def build_series_frame_from_subset(subset: pd.DataFrame, month_index: pd.DatetimeIndex) -> pd.DataFrame:
    if subset.empty:
        df = pd.DataFrame({"month": month_index})
        df["paper_count"] = 0
        df["mention_count"] = 0
        df["share_pct"] = 0.0
        df["rolling_12m_pct"] = 0.0
        return df

    grouped = (
        subset.groupby("month", as_index=False)
        .agg(paper_count=("month", "size"), mention_count=("is_match", "sum"))
        .sort_values("month")
    )
    df = pd.DataFrame({"month": month_index})
    df = df.merge(grouped, on="month", how="left")
    df["paper_count"] = df["paper_count"].fillna(0).astype(int)
    df["mention_count"] = df["mention_count"].fillna(0).astype(int)
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


def filtered_plot_df(df: pd.DataFrame, plot_start: str, plot_end: str | None) -> tuple[pd.DataFrame, bool]:
    trimmed_df, trimmed = trim_partial_last_month(df)
    filtered = trimmed_df[trimmed_df["month"] >= pd.Timestamp(plot_start)].copy()
    if plot_end:
        filtered = filtered[filtered["month"] <= pd.Timestamp(plot_end)]
    return filtered, trimmed


def build_variant_series(frame: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, int | bool | str]]]:
    month_index = pd.date_range(frame["month"].min(), frame["month"].max(), freq="MS")
    subsets = {
        "all": frame,
        "core": frame[frame["bucket"] == "core"].copy(),
        "adjacent": frame[frame["bucket"] == "adjacent"].copy(),
    }
    frames: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict[str, int | bool | str]] = {}
    for name, subset in subsets.items():
        df = build_series_frame_from_subset(subset, month_index)
        trimmed_df, trimmed = trim_partial_last_month(df)
        frames[name] = df
        metadata[name] = {
            "rows_seen": int(len(subset)),
            "rows_matched": int(subset["is_match"].sum()),
            "plot_trimmed_partial_last_month": trimmed,
            "plot_end_month": trimmed_df.iloc[-1]["month"].strftime("%Y-%m-%d"),
        }
    return frames, metadata


def load_cutoff_source_sets(source_list_dir: Path) -> tuple[dict[str, set[str]], dict[str, str]]:
    sets: dict[str, set[str]] = {}
    labels: dict[str, str] = {}
    for bucket in ("core", "adjacent"):
        path = source_list_dir / f"{bucket}_mean_fwci_top150.csv"
        ranked = pd.read_csv(path)
        for cutoff in (50, 100, 150):
            key = f"{bucket}_top_{cutoff}"
            sets[key] = set(ranked.loc[ranked["rank"] <= cutoff, "source_id"].astype(str))
            labels[key] = f"{bucket} {cutoff}"
    return sets, labels


def build_cutoff_series(
    frame: pd.DataFrame, cutoff_sets: dict[str, set[str]]
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, int | bool | str]]]:
    month_index = pd.date_range(frame["month"].min(), frame["month"].max(), freq="MS")
    frames: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict[str, int | bool | str]] = {}
    for key, source_ids in cutoff_sets.items():
        bucket = "core" if key.startswith("core_") else "adjacent"
        subset = frame[(frame["bucket"] == bucket) & (frame["source_id"].isin(source_ids))].copy()
        df = build_series_frame_from_subset(subset, month_index)
        trimmed_df, trimmed = trim_partial_last_month(df)
        frames[key] = df
        metadata[key] = {
            "rows_seen": int(len(subset)),
            "rows_matched": int(subset["is_match"].sum()),
            "plot_trimmed_partial_last_month": trimmed,
            "plot_end_month": trimmed_df.iloc[-1]["month"].strftime("%Y-%m-%d"),
        }
    return frames, metadata


def build_field_series(
    frame: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, int | bool | str]]]:
    month_index = pd.date_range(frame["month"].min(), frame["month"].max(), freq="MS")
    frames: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict[str, int | bool | str]] = {}
    for spec in FIELD_SPECS:
        subset = frame[frame["major_field"] == spec.slug].copy()
        df = build_series_frame_from_subset(subset, month_index)
        trimmed_df, trimmed = trim_partial_last_month(df)
        frames[spec.slug] = df
        metadata[spec.slug] = {
            "rows_seen": int(len(subset)),
            "rows_matched": int(subset["is_match"].sum()),
            "plot_trimmed_partial_last_month": trimmed,
            "plot_end_month": trimmed_df.iloc[-1]["month"].strftime("%Y-%m-%d"),
        }
    return frames, metadata


def style_axis(ax: plt.Axes, *, ymax: float, year_step: int = 2) -> None:
    ax.set_facecolor(PANEL)
    ax.grid(axis="y", color=GRID, linewidth=1.0)
    ax.grid(axis="x", visible=False)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.spines["bottom"].set_linewidth(1.1)
    ax.tick_params(axis="both", colors=SUBTEXT, labelsize=11.5, length=0)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator(year_step))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(0, ymax)


def style_small_multiple_axis(ax: plt.Axes, *, ymax: float) -> None:
    ax.set_facecolor(PANEL)
    ax.grid(axis="y", color=GRID, linewidth=0.85)
    ax.grid(axis="x", visible=False)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.tick_params(axis="both", colors=SUBTEXT, labelsize=9.0, length=0)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator(4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(0, ymax)


def add_branding(fig: plt.Figure) -> None:
    return None


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

    fig = plt.figure(figsize=(11.2, 7.3), dpi=220)
    fig.patch.set_facecolor(BACKGROUND)
    ax = fig.add_axes([0.08, 0.23, 0.84, 0.52])

    ax.plot(plot_df["month"], plot_df["share_pct"], color=MONTHLY, linewidth=2.5, alpha=0.9, zorder=2)
    ax.plot(plot_df["month"], plot_df["rolling_12m_pct"], color=ROLLING, linewidth=3.2, zorder=3)

    ymax = max(plot_df["share_pct"].max(), plot_df["rolling_12m_pct"].max()) * 1.18
    style_axis(ax, ymax=ymax)
    ax.set_xlim(plot_df["month"].min(), plot_df["month"].max())

    ax.axvline(CHATGPT_RELEASE, color=MUTED, linestyle=(0, (2, 2)), linewidth=1.8, zorder=1)
    ax.text(
        CHATGPT_RELEASE + pd.Timedelta(days=20),
        ymax * 0.92,
        "Nov 2022",
        ha="left",
        va="center",
        color=SUBTEXT,
        fontsize=10.8,
    )

    add_branding(fig)
    fig.text(0.08, 0.92, title, fontsize=21.5, color=TEXT, linespacing=1.06)
    fig.text(0.08, 0.865, subtitle, fontsize=13.6, color=SUBTEXT, linespacing=1.3)
    fig.legend(
        handles=[
            Line2D([0], [0], color=MONTHLY, linewidth=3.0, label="Monthly share"),
            Line2D([0], [0], color=ROLLING, linewidth=3.4, label="12-month rolling average"),
            Line2D([0], [0], color=MUTED, linewidth=1.8, linestyle=(0, (2, 2)), label="ChatGPT release"),
        ],
        loc="upper left",
        bbox_to_anchor=(0.08, 0.82),
        frameon=False,
        ncol=3,
        fontsize=11.2,
        handlelength=2.6,
        labelcolor=TEXT,
    )

    fig.text(0.08, 0.095, footnote, fontsize=10.5, color=SUBTEXT, linespacing=1.38)
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

    fig = plt.figure(figsize=(11.2, 7.3), dpi=220)
    fig.patch.set_facecolor(BACKGROUND)
    ax = fig.add_axes([0.08, 0.23, 0.84, 0.52])

    ax.plot(adjacent_plot["month"], adjacent_plot["rolling_12m_pct"], color=ADJACENT, linewidth=3.2, zorder=2)
    ax.plot(core_plot["month"], core_plot["rolling_12m_pct"], color=CORE, linewidth=3.2, zorder=3)

    ymax = max(adjacent_plot["rolling_12m_pct"].max(), core_plot["rolling_12m_pct"].max()) * 1.22
    style_axis(ax, ymax=ymax)
    ax.set_xlim(core_plot["month"].min(), core_plot["month"].max())

    ax.axvline(CHATGPT_RELEASE, color=MUTED, linestyle=(0, (2, 2)), linewidth=1.8, zorder=1)
    ax.text(
        CHATGPT_RELEASE + pd.Timedelta(days=20),
        ymax * 0.92,
        "Nov 2022",
        ha="left",
        va="center",
        color=SUBTEXT,
        fontsize=10.8,
    )

    add_branding(fig)
    fig.text(0.08, 0.92, title, fontsize=21.5, color=TEXT, linespacing=1.06)
    fig.text(0.08, 0.865, subtitle, fontsize=13.6, color=SUBTEXT, linespacing=1.3)
    fig.legend(
        handles=[
            Line2D([0], [0], color=CORE, linewidth=3.4, label="Core journals"),
            Line2D([0], [0], color=ADJACENT, linewidth=3.4, label="Adjacent journals"),
            Line2D([0], [0], color=MUTED, linewidth=1.8, linestyle=(0, (2, 2)), label="ChatGPT release"),
        ],
        loc="upper left",
        bbox_to_anchor=(0.08, 0.82),
        frameon=False,
        ncol=3,
        fontsize=11.2,
        handlelength=2.6,
        labelcolor=TEXT,
    )

    fig.text(0.08, 0.095, footnote, fontsize=10.5, color=SUBTEXT, linespacing=1.38)
    save_figure(fig, png_path, svg_path)


def plot_cutoff_series(
    series_map: dict[str, pd.DataFrame],
    labels: dict[str, str],
    *,
    title: str,
    subtitle: str,
    footnote: str,
    png_path: Path,
    svg_path: Path,
    plot_start: str,
    plot_end: str | None,
) -> None:
    order = [
        "core_top_50",
        "core_top_100",
        "core_top_150",
        "adjacent_top_50",
        "adjacent_top_100",
        "adjacent_top_150",
    ]
    plot_frames = {key: filtered_plot_df(series_map[key], plot_start, plot_end)[0] for key in order}
    ymax = max(float(df["rolling_12m_pct"].max()) for df in plot_frames.values()) * 1.22

    fig = plt.figure(figsize=(11.2, 7.8), dpi=220)
    fig.patch.set_facecolor(BACKGROUND)
    ax = fig.add_axes([0.08, 0.22, 0.84, 0.48])

    handles: list[Line2D] = []
    for key in order:
        bucket = "core" if key.startswith("core_") else "adjacent"
        cutoff = int(key.rsplit("_", 1)[-1])
        color = CORE_CUTOFF_COLORS[cutoff] if bucket == "core" else ADJ_CUTOFF_COLORS[cutoff]
        df = plot_frames[key]
        ax.plot(df["month"], df["rolling_12m_pct"], color=color, linewidth=3.0, zorder=3)
        handles.append(Line2D([0], [0], color=color, linewidth=3.6, label=labels[key]))

    style_axis(ax, ymax=ymax)
    ax.set_xlim(next(iter(plot_frames.values()))["month"].min(), next(iter(plot_frames.values()))["month"].max())

    ax.axvline(CHATGPT_RELEASE, color=MUTED, linestyle=(0, (2, 2)), linewidth=1.8, zorder=1)
    ax.text(
        CHATGPT_RELEASE + pd.Timedelta(days=20),
        ymax * 0.92,
        "Nov 2022",
        ha="left",
        va="center",
        color=SUBTEXT,
        fontsize=10.8,
    )

    add_branding(fig)
    fig.text(0.08, 0.92, title, fontsize=21.5, color=TEXT, linespacing=1.06)
    fig.text(0.08, 0.865, subtitle, fontsize=13.6, color=SUBTEXT, linespacing=1.3)
    fig.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.08, 0.81),
        ncol=2,
        frameon=False,
        fontsize=11.0,
        handlelength=2.5,
        labelcolor=TEXT,
    )

    fig.text(0.08, 0.095, footnote, fontsize=10.5, color=SUBTEXT, linespacing=1.38)
    save_figure(fig, png_path, svg_path)


def plot_field_small_multiples(
    field_frames: dict[str, pd.DataFrame],
    field_metadata: dict[str, dict[str, int | bool | str]],
    *,
    title: str,
    subtitle: str,
    footnote: str,
    png_path: Path,
    svg_path: Path,
    plot_start: str,
    plot_end: str | None,
) -> None:
    order = [spec.slug for spec in FIELD_SPECS]
    plot_frames = {slug: filtered_plot_df(field_frames[slug], plot_start, plot_end)[0] for slug in order}
    ymax = max(float(df["rolling_12m_pct"].max()) for df in plot_frames.values()) * 1.2
    ymax = max(ymax, 0.8)

    fig, axes = plt.subplots(4, 2, figsize=(12.2, 10.0), dpi=220)
    fig.patch.set_facecolor(BACKGROUND)
    plt.subplots_adjust(left=0.08, right=0.96, top=0.74, bottom=0.14, wspace=0.18, hspace=0.34)

    for ax, spec in zip(axes.flat, FIELD_SPECS):
        df = plot_frames[spec.slug]
        ax.plot(df["month"], df["rolling_12m_pct"], color=FIELD_LINE, linewidth=2.6, zorder=3)
        ax.axvline(CHATGPT_RELEASE, color=MUTED, linestyle=(0, (2, 2)), linewidth=1.2, zorder=1)
        style_small_multiple_axis(ax, ymax=ymax)
        ax.set_xlim(df["month"].min(), df["month"].max())
        ax.set_title(spec.label, loc="left", fontsize=12.3, color=TEXT, pad=8)
        ax.text(
            0.0,
            1.02,
            f"{int(field_metadata[spec.slug]['rows_seen']):,} papers",
            transform=ax.transAxes,
            fontsize=9.2,
            color=SUBTEXT,
            va="bottom",
        )

    add_branding(fig)
    fig.text(0.08, 0.93, title, fontsize=21.5, color=TEXT, linespacing=1.06)
    fig.text(0.08, 0.875, subtitle, fontsize=13.6, color=SUBTEXT, linespacing=1.3)
    fig.text(0.08, 0.095, footnote, fontsize=10.5, color=SUBTEXT, linespacing=1.38)
    save_figure(fig, png_path, svg_path)


def write_series_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out["month"] = out["month"].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)


def write_long_series_csv(path: Path, frames: dict[str, pd.DataFrame], label_map: dict[str, str], kind: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for key, df in frames.items():
        tmp = df.copy()
        tmp["series_key"] = key
        tmp["series_label"] = label_map[key]
        tmp["series_kind"] = kind
        rows.append(tmp)
    out = pd.concat(rows, ignore_index=True)
    out["month"] = out["month"].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)


def write_metadata(
    path: Path,
    *,
    variant_metadata: dict[str, dict[str, int | bool | str]],
    cutoff_metadata: dict[str, dict[str, int | bool | str]],
    field_metadata: dict[str, dict[str, int | bool | str]],
    extraction_db_path: Path,
    openalex_db_path: Path,
    source_list_dir: Path,
) -> None:
    payload = {
        "source_extraction_db": str(extraction_db_path),
        "source_openalex_db": str(openalex_db_path),
        "source_rank_dir": str(source_list_dir),
        "corpus_filter": {
            "corpus": "Frontier Graph screened published-paper corpus",
            "screened_work_count_target": 242595,
            "exclude_retracted": True,
            "exclude_paratext": True,
            "require_publication_date": True,
        },
        "term_labels": [spec.label for spec in TERM_SPECS],
        "term_patterns": [spec.pattern for spec in TERM_SPECS],
        "field_keyword_map": {spec.label: list(spec.patterns) for spec in FIELD_SPECS},
        "variants": variant_metadata,
        "cutoff_variants": cutoff_metadata,
        "field_variants": field_metadata,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    pattern = build_regex()
    papers = load_paper_frame(args.extraction_db, args.openalex_db, pattern)

    variant_frames, variant_metadata = build_variant_series(papers)
    cutoff_sets, cutoff_labels = load_cutoff_source_sets(args.source_list_dir)
    cutoff_frames, cutoff_metadata = build_cutoff_series(papers, cutoff_sets)
    field_frames, field_metadata = build_field_series(papers)

    effective_plot_end = args.plot_end or str(variant_metadata["all"]["plot_end_month"])

    csv_paths = {
        "all": args.analysis_dir / "frontiergraph_ai_mentions_monthly.csv",
        "core": args.analysis_dir / "frontiergraph_ai_mentions_monthly_core.csv",
        "adjacent": args.analysis_dir / "frontiergraph_ai_mentions_monthly_adjacent.csv",
    }
    for variant, path in csv_paths.items():
        write_series_csv(path, variant_frames[variant])

    write_long_series_csv(
        args.analysis_dir / "frontiergraph_ai_mentions_monthly_cutoffs.csv",
        cutoff_frames,
        cutoff_labels,
        kind="journal_cutoff",
    )
    write_long_series_csv(
        args.analysis_dir / "frontiergraph_ai_mentions_monthly_fields.csv",
        field_frames,
        {spec.slug: spec.label for spec in FIELD_SPECS},
        kind="field",
    )

    plot_single_series(
        variant_frames["all"],
        title="Share of published papers mentioning AI terms",
        subtitle="Title or abstract matches in the screened economics-paper corpus",
        footnote=(
            "Source: published-journal corpus assembled for Frontier Graph\n"
            "AI terms include artificial intelligence, large language model, generative AI, ChatGPT,\n"
            "deep learning, neural network, BERT, transformer, and explicit GPT model-family mentions."
        ),
        png_path=args.figures_dir / "frontiergraph_ai_mentions_share.png",
        svg_path=args.figures_dir / "frontiergraph_ai_mentions_share.svg",
        plot_start=args.plot_start,
        plot_end=effective_plot_end,
    )

    plot_comparison_series(
        variant_frames["core"],
        variant_frames["adjacent"],
        title="AI-term mentions in core and adjacent journal sets",
        subtitle="12-month rolling averages for title or abstract matches",
        footnote=(
            "Source: published-journal corpus assembled for Frontier Graph\n"
            "Core and adjacent follow the project's published-journal bucket definitions."
        ),
        png_path=args.figures_dir / "frontiergraph_ai_mentions_core_vs_adjacent.png",
        svg_path=args.figures_dir / "frontiergraph_ai_mentions_core_vs_adjacent.svg",
        plot_start=args.plot_start,
        plot_end=effective_plot_end,
    )

    plot_cutoff_series(
        cutoff_frames,
        cutoff_labels,
        title="AI-term mentions by journal-set cutoff",
        subtitle="12-month rolling averages for the top 50, 100, and 150 core and adjacent sets",
        footnote=(
            "Source: published-journal corpus assembled for Frontier Graph\n"
            "Cutoffs are nested subsets of the mean-FWCI ranked source lists used to build the current corpus."
        ),
        png_path=args.figures_dir / "frontiergraph_ai_mentions_cutoff_splits.png",
        svg_path=args.figures_dir / "frontiergraph_ai_mentions_cutoff_splits.svg",
        plot_start=args.plot_start,
        plot_end=effective_plot_end,
    )

    plot_field_small_multiples(
        field_frames,
        field_metadata,
        title="AI-term mentions across major field slices",
        subtitle="12-month rolling averages from paper-level primary-topic assignments",
        footnote=(
            "Source: published-journal corpus assembled for Frontier Graph\n"
            "Fields are assigned with a transparent keyword map over each paper's OpenAlex primary topic label."
        ),
        png_path=args.figures_dir / "frontiergraph_ai_mentions_major_fields.png",
        svg_path=args.figures_dir / "frontiergraph_ai_mentions_major_fields.svg",
        plot_start=args.plot_start,
        plot_end=effective_plot_end,
    )

    write_metadata(
        args.analysis_dir / "frontiergraph_ai_mentions_metadata.json",
        variant_metadata=variant_metadata,
        cutoff_metadata=cutoff_metadata,
        field_metadata=field_metadata,
        extraction_db_path=args.extraction_db,
        openalex_db_path=args.openalex_db,
        source_list_dir=args.source_list_dir,
    )

    print(
        json.dumps(
            {
                "variants": {
                    variant: {
                        "rows_seen": int(variant_metadata[variant]["rows_seen"]),
                        "rows_matched": int(variant_metadata[variant]["rows_matched"]),
                        "last_rolling_12m_pct": round(float(variant_frames[variant].iloc[-1]["rolling_12m_pct"]), 3),
                    }
                    for variant in ["all", "core", "adjacent"]
                },
                "cutoffs": {
                    key: {
                        "rows_seen": int(cutoff_metadata[key]["rows_seen"]),
                        "rows_matched": int(cutoff_metadata[key]["rows_matched"]),
                    }
                    for key in [
                        "core_top_50",
                        "core_top_100",
                        "core_top_150",
                        "adjacent_top_50",
                        "adjacent_top_100",
                        "adjacent_top_150",
                    ]
                },
                "fields": {
                    spec.slug: {
                        "rows_seen": int(field_metadata[spec.slug]["rows_seen"]),
                        "rows_matched": int(field_metadata[spec.slug]["rows_matched"]),
                    }
                    for spec in FIELD_SPECS
                },
                "figure_outputs": {
                    "main": str(args.figures_dir / "frontiergraph_ai_mentions_share.png"),
                    "core_vs_adjacent": str(args.figures_dir / "frontiergraph_ai_mentions_core_vs_adjacent.png"),
                    "journal_cutoffs": str(args.figures_dir / "frontiergraph_ai_mentions_cutoff_splits.png"),
                    "major_fields": str(args.figures_dir / "frontiergraph_ai_mentions_major_fields.png"),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
