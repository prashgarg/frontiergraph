from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "paper" / "mermaid"
PNG_PATH = OUT_DIR / "method_figure_5_custom.png"
PDF_PATH = OUT_DIR / "method_figure_5_custom.pdf"


COLORS = {
    "panel_fill": "#FBF7EA",
    "panel_edge": "#D8C9A7",
    "node_fill": "#EEF1F7",
    "node_edge": "#A9B6CB",
    "text": "#253041",
    "muted": "#5E677D",
    "obs": "#4F719B",
    "neutral": "#7B8597",
    "anchor": "#C26143",
}


def rounded_box(ax, xy, w, h, text, fontsize=16, lw=1.4, z=3):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=COLORS["node_fill"],
        edgecolor=COLORS["node_edge"],
        linewidth=lw,
        zorder=z,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=COLORS["text"],
        zorder=z + 1,
    )
    return patch


def panel(ax, xy, w, h, title):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.04,rounding_size=0.09",
        facecolor=COLORS["panel_fill"],
        edgecolor=COLORS["panel_edge"],
        linewidth=1.4,
        zorder=1,
    )
    ax.add_patch(patch)
    ax.text(
        x + 0.22,
        y + h - 0.18,
        title,
        ha="left",
        va="center",
        fontsize=9.5,
        color=COLORS["muted"],
        fontweight="semibold",
        zorder=2,
    )
    return patch


def arrow(ax, start, end, color, lw=2.0, style="-|>", mutation=14, connectionstyle=None, ls="-", z=2):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=mutation,
        linewidth=lw,
        linestyle=ls,
        color=color,
        connectionstyle=connectionstyle,
        zorder=z,
        shrinkA=4,
        shrinkB=4,
    )
    ax.add_patch(patch)
    return patch


def label(ax, x, y, text, fontsize=14, color=None, ha="center", va="center"):
    ax.text(
        x,
        y,
        text,
        fontsize=fontsize,
        color=color or COLORS["muted"],
        ha=ha,
        va=va,
        zorder=5,
    )


def main():
    fig = plt.figure(figsize=(8.6, 4.6))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 8.6)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    panel(ax, (0.32, 0.34), 3.45, 3.55, "Local support")
    panel(ax, (4.86, 1.18), 3.1, 1.82, "Surfaced question")

    rounded_box(ax, (0.92, 3.28), 1.85, 0.36, "Transit investment", fontsize=9.8)
    rounded_box(ax, (1.58, 2.42), 1.65, 0.36, "Commute time", fontsize=9.6)
    rounded_box(ax, (1.58, 1.52), 1.65, 0.36, "Reachable jobs", fontsize=9.6)
    rounded_box(ax, (1.35, 0.7), 1.4, 0.36, "Employment", fontsize=9.6)

    # Support graph edges
    arrow(
        ax,
        (1.88, 3.28),
        (2.35, 2.76),
        COLORS["neutral"],
        lw=1.8,
        connectionstyle="arc3,rad=-0.35",
        mutation=13,
    )
    arrow(ax, (2.4, 2.42), (2.4, 1.87), COLORS["neutral"], lw=1.8, mutation=13)
    arrow(
        ax,
        (1.55, 3.28),
        (1.8, 1.0),
        COLORS["obs"],
        lw=2.4,
        connectionstyle="arc3,rad=0.28",
        mutation=13,
    )
    arrow(
        ax,
        (2.5, 1.52),
        (2.18, 1.03),
        COLORS["anchor"],
        lw=2.2,
        ls=(0, (2, 2)),
        mutation=13,
    )

    label(ax, 0.55, 2.35, "observed direct claim", fontsize=8.1, color=COLORS["obs"], ha="left")
    label(ax, 1.95, 1.23, "benchmark anchor", fontsize=7.8, color=COLORS["anchor"], ha="center")

    # Transition to question
    arrow(ax, (3.85, 1.95), (4.82, 1.95), COLORS["neutral"], lw=1.7, mutation=13)
    label(ax, 4.34, 2.08, "compress to question", fontsize=7.9, color=COLORS["muted"])

    q = FancyBboxPatch(
        (5.28, 1.42),
        2.3,
        1.02,
        boxstyle="round,pad=0.03,rounding_size=0.08",
        facecolor=COLORS["node_fill"],
        edgecolor=COLORS["node_edge"],
        linewidth=1.2,
        zorder=3,
    )
    ax.add_patch(q)
    ax.text(
        6.43,
        1.94,
        "Could transit investment\nraise employment\nby reducing commute\ntime\nand expanding reachable\njobs?",
        ha="center",
        va="center",
        fontsize=8.2,
        color=COLORS["text"],
        zorder=4,
        linespacing=1.08,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in [PNG_PATH, PDF_PATH]:
        fig.savefig(
            path,
            dpi=300,
            transparent=True,
            bbox_inches="tight",
            pad_inches=0.01,
        )


if __name__ == "__main__":
    main()
