from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "paper" / "mermaid"
PNG_PATH = OUT_DIR / "method_figure_3_custom.png"
PDF_PATH = OUT_DIR / "method_figure_3_custom.pdf"


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
    "connector": "#8A92A0",
}


def rounded_box(ax, xy, w, h, text, fontsize=10.5, lw=1.3, z=3):
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
        boxstyle="round,pad=0.04,rounding_size=0.08",
        facecolor=COLORS["panel_fill"],
        edgecolor=COLORS["panel_edge"],
        linewidth=1.35,
        zorder=1,
    )
    ax.add_patch(patch)
    ax.text(
        x + 0.18,
        y + h - 0.18,
        title,
        ha="left",
        va="center",
        fontsize=9.4,
        color=COLORS["muted"],
        fontweight="semibold",
        zorder=2,
    )
    return patch


def arrow(
    ax,
    start,
    end,
    color,
    lw=1.8,
    style="-|>",
    mutation=12,
    connectionstyle=None,
    ls="-",
    z=2,
    shrinkA=4,
    shrinkB=4,
):
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
        shrinkA=shrinkA,
        shrinkB=shrinkB,
    )
    ax.add_patch(patch)
    return patch


def label(ax, x, y, text, fontsize=8.6, color=None, ha="center", va="center"):
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
    fig = plt.figure(figsize=(8.2, 5.7))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 10.2)
    ax.set_ylim(0, 7.0)
    ax.axis("off")

    panel(ax, (0.18, 4.15), 3.05, 2.35, "Paper A (direct claim)")
    panel(ax, (0.18, 0.25), 3.05, 3.35, "Paper B (mechanism)")
    panel(ax, (5.42, 0.95), 4.4, 5.55, "Shared graph candidate")

    # Paper A
    rounded_box(ax, (0.55, 5.75), 2.3, 0.42, "Transit investment")
    rounded_box(ax, (0.82, 4.6), 1.76, 0.42, "Employment")
    arrow(ax, (1.7, 5.73), (1.7, 5.04), COLORS["neutral"], lw=1.6, mutation=11)
    label(ax, 1.7, 5.35, "raises", fontsize=8.6)

    # Paper B
    rounded_box(ax, (0.55, 2.75), 2.3, 0.42, "Transit investment")
    rounded_box(ax, (0.95, 1.83), 1.5, 0.42, "Commute time")
    rounded_box(ax, (0.8, 0.58), 1.8, 0.42, "Reachable jobs")
    arrow(ax, (1.7, 2.73), (1.7, 2.26), COLORS["neutral"], lw=1.6, mutation=11)
    label(ax, 1.7, 2.42, "reduces", fontsize=8.4)
    arrow(ax, (1.7, 1.81), (1.7, 1.0), COLORS["neutral"], lw=1.6, mutation=11)
    label(ax, 1.7, 1.35, "expands", fontsize=8.4)

    # Shared graph
    rounded_box(ax, (6.28, 5.52), 2.4, 0.42, "Transit investment")
    rounded_box(ax, (7.18, 4.0), 1.9, 0.42, "Commute time")
    rounded_box(ax, (7.0, 2.43), 2.1, 0.42, "Reachable jobs")
    rounded_box(ax, (7.02, 0.92), 2.0, 0.42, "Employment")

    arrow(
        ax,
        (7.48, 5.5),
        (8.04, 4.42),
        COLORS["neutral"],
        lw=1.6,
        mutation=11,
        connectionstyle="arc3,rad=-0.22",
    )
    arrow(ax, (8.13, 3.98), (8.13, 2.86), COLORS["neutral"], lw=1.6, mutation=11)
    arrow(
        ax,
        (7.15, 5.5),
        (7.45, 1.36),
        COLORS["obs"],
        lw=2.3,
        mutation=11,
        connectionstyle="arc3,rad=0.36",
    )
    arrow(
        ax,
        (8.0, 2.42),
        (8.0, 1.37),
        COLORS["anchor"],
        lw=2.9,
        mutation=11,
        ls=(0, (2.2, 2.0)),
    )

    label(ax, 7.18, 3.08, "observed direct claim", fontsize=8.8, color=COLORS["obs"], ha="center")
    label(ax, 8.82, 1.92, "missing mechanism edge", fontsize=8.8, color=COLORS["anchor"], ha="center")

    # Match connectors
    arrow(
        ax,
        (3.18, 5.18),
        (5.45, 5.02),
        COLORS["connector"],
        lw=1.2,
        mutation=10,
        connectionstyle="arc3,rad=-0.18",
    )
    arrow(
        ax,
        (3.18, 1.95),
        (5.45, 2.28),
        COLORS["connector"],
        lw=1.2,
        mutation=10,
        connectionstyle="arc3,rad=0.12",
    )
    label(ax, 4.17, 5.32, "match concepts", fontsize=8.2, color=COLORS["connector"])
    label(ax, 4.18, 1.48, "match concepts", fontsize=8.2, color=COLORS["connector"])

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
