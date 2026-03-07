from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

out_dir = Path('outputs/paper/figures')
out_dir.mkdir(parents=True, exist_ok=True)

# Figure 1: Method schematic
fig, ax = plt.subplots(figsize=(12, 2.8))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

boxes = [
    (0.02, 0.34, 0.17, 0.42, 'Corpus Stock\n(<= t-1)'),
    (0.23, 0.28, 0.19, 0.52, 'Signals\nGap + Path + Motif'),
    (0.46, 0.28, 0.19, 0.52, 'Transparent Score\nDecomposition'),
    (0.69, 0.34, 0.17, 0.42, 'Ranked Missing\nClaims at t'),
    (0.89, 0.34, 0.09, 0.42, 'Realization\n[t,t+h]'),
]

for x, y, w, h, label in boxes:
    rect = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle='round,pad=0.02,rounding_size=0.02',
        linewidth=1.4,
        edgecolor='#1f2937',
        facecolor='#f8fafc',
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, label, ha='center', va='center', fontsize=11)

for i in range(len(boxes) - 1):
    x1, y1, w1, h1, _ = boxes[i]
    x2, y2, w2, h2, _ = boxes[i + 1]
    start = (x1 + w1, y1 + h1 / 2)
    end = (x2, y2 + h2 / 2)
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle='-|>',
        mutation_scale=13,
        linewidth=1.4,
        color='#1f2937',
    )
    ax.add_patch(arrow)

ax.text(
    0.50,
    0.09,
    'Rolling vintage protocol: train on <= t-1, evaluate first appearance in [t,t+h], h in {1,3,5}',
    ha='center',
    va='center',
    fontsize=10,
)

fig.tight_layout()
fig.savefig(out_dir / 'method_schematic.png', dpi=300, bbox_inches='tight', pad_inches=0.02)
plt.close(fig)

# Figure 4: Field heterogeneity (realization rate by source field)
het = pd.read_csv('outputs/paper/06_findings/heterogeneity_tables.csv')
field = het[het['breakdown'] == 'field_source'].copy()
field = field[field['n_predictions'] >= 20].copy()
field = field.sort_values('realized_rate', ascending=True)

fig, ax = plt.subplots(figsize=(8.8, 5.4))
ax.barh(field['group'], field['realized_rate'], color='#2563eb', alpha=0.9)
ax.set_xlabel('Realization rate within horizon (share)')
ax.set_ylabel('Field source (JEL first letter)')
ax.set_title('Field Heterogeneity in Missing-Claim Realization')
ax.grid(axis='x', linestyle='--', alpha=0.35)
for i, (_, row) in enumerate(field.iterrows()):
    ax.text(row['realized_rate'] + 0.005, i, f"n={int(row['n_predictions'])}", va='center', fontsize=8)

fig.tight_layout()
fig.savefig(out_dir / 'field_heterogeneity.png', dpi=300)
plt.close(fig)
