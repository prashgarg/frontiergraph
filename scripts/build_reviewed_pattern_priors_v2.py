from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ontology_v2"
OUT_PATH = DATA_DIR / "reviewed_pattern_priors_v2.parquet"
NOTE_PATH = DATA_DIR / "reviewed_pattern_priors_v2.md"

SOURCE_PATH = DATA_DIR / "ontology_enrichment_overlay_v2_reviewed_round2.parquet"
ROW_SOURCES = {"row_review", "remaining_row_majority_review", "unresolved_row_review"}
DECISIONS = [
    "accept_existing_broad",
    "promote_new_concept_family",
    "accept_existing_alias",
    "reject_match_keep_raw",
    "keep_unresolved",
    "unclear",
]
MIN_SUPPORT = 20


def tokenize(label: str) -> list[str]:
    text = str(label).strip().lower()
    text = re.sub(r"[^a-z0-9()]+", " ", text)
    return [tok for tok in text.split() if tok]


def shannon_entropy(counts: list[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count <= 0:
            continue
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def pattern_records(df: pd.DataFrame) -> pd.DataFrame:
    counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    examples: dict[tuple[str, str], list[str]] = defaultdict(list)

    def add(pattern_type: str, pattern_value: str, decision: str, label: str) -> None:
        key = (pattern_type, pattern_value)
        counts[key][decision] += 1
        if len(examples[key]) < 8 and label not in examples[key]:
            examples[key].append(label)

    curated_checks = {
        "endswith_per_capita": lambda toks, raw: len(toks) >= 2 and toks[-2:] == ["per", "capita"],
        "endswith_volatility": lambda toks, raw: len(toks) >= 1 and toks[-1] == "volatility",
        "endswith_uncertainty": lambda toks, raw: len(toks) >= 1 and toks[-1] == "uncertainty",
        "endswith_constraints": lambda toks, raw: len(toks) >= 1 and toks[-1] == "constraints",
        "endswith_frictions": lambda toks, raw: len(toks) >= 1 and toks[-1] == "frictions",
        "endswith_returns": lambda toks, raw: len(toks) >= 1 and toks[-1] == "returns",
        "endswith_consumption": lambda toks, raw: len(toks) >= 1 and toks[-1] == "consumption",
        "contains_heterogeneity": lambda toks, raw: "heterogeneity" in toks,
        "contains_parenthetical": lambda toks, raw: "(" in raw and ")" in raw,
    }

    for _, row in df.iterrows():
        label = str(row["label"])
        decision = str(row["final_decision"])
        toks = tokenize(label)
        if not toks:
            continue

        for n in (1, 2, 3):
            if len(toks) >= n:
                add(f"suffix_{n}", " ".join(toks[-n:]), decision, label)
                add(f"prefix_{n}", " ".join(toks[:n]), decision, label)

        for pattern_name, fn in curated_checks.items():
            if fn(toks, label.lower()):
                add("curated", pattern_name, decision, label)

    rows = []
    for (pattern_type, pattern_value), decision_counts in counts.items():
        support = sum(decision_counts.values())
        if support < MIN_SUPPORT:
            continue
        top_decision, top_count = decision_counts.most_common(1)[0]
        rows.append(
            {
                "pattern_type": pattern_type,
                "pattern_value": pattern_value,
                "support": support,
                "top_decision": top_decision,
                "top_share": top_count / support,
                "entropy": shannon_entropy([decision_counts.get(dec, 0) for dec in DECISIONS]),
                "example_labels_json": pd.Series(examples[(pattern_type, pattern_value)]).to_json(orient="values"),
                **{f"count__{dec}": int(decision_counts.get(dec, 0)) for dec in DECISIONS},
                **{f"share__{dec}": float(decision_counts.get(dec, 0) / support) for dec in DECISIONS},
            }
        )
    result = pd.DataFrame(rows).sort_values(
        ["pattern_type", "support", "top_share"], ascending=[True, False, False]
    ).reset_index(drop=True)
    return result


def render_note(df: pd.DataFrame, priors: pd.DataFrame) -> str:
    lines = [
        "# Reviewed Pattern Priors V2",
        "",
        "This file learns phrase-pattern priors from row-reviewed ontology decisions rather than imposing deterministic phrase rules by hand.",
        "",
        f"- reviewed row corpus: `{len(df):,}` labels",
        "- included decision sources: `row_review`, `remaining_row_majority_review`, `unresolved_row_review`",
        f"- minimum support for a prior row: `{MIN_SUPPORT}`",
        "",
        "## Curated patterns",
    ]
    curated = priors[priors["pattern_type"] == "curated"].copy()
    curated = curated.sort_values(["support", "top_share"], ascending=[False, False])
    for _, row in curated.iterrows():
        lines.append(
            f"- `{row['pattern_value']}`: support `{int(row['support'])}`, "
            f"top decision `{row['top_decision']}` (`{row['top_share']:.2f}` share), "
            f"broad `{row['share__accept_existing_broad']:.2f}`, "
            f"new-family `{row['share__promote_new_concept_family']:.2f}`, "
            f"alias `{row['share__accept_existing_alias']:.2f}`, "
            f"reject `{row['share__reject_match_keep_raw']:.2f}`, "
            f"unresolved `{row['share__keep_unresolved']:.2f}`"
        )

    lines.extend(["", "## Strong learned suffix priors"])
    suffix = priors[
        priors["pattern_type"].isin(["suffix_1", "suffix_2", "suffix_3"])
        & (priors["support"] >= 30)
        & (priors["top_share"] >= 0.65)
    ].copy()
    suffix = suffix.sort_values(["top_share", "support"], ascending=[False, False]).head(25)
    for _, row in suffix.iterrows():
        lines.append(
            f"- `{row['pattern_type']}={row['pattern_value']}`: support `{int(row['support'])}`, "
            f"top decision `{row['top_decision']}` (`{row['top_share']:.2f}` share)"
        )

    lines.extend(["", "## Interpretation"])
    lines.extend(
        [
            "- These priors should be used as weak, data-driven hints or ranking features, not as hard deterministic mapping rules.",
            "- Patterns with high support and high concentration can guide queue ordering or default proposals.",
            "- Patterns with mixed distributions should remain review-only and should not be promoted into hard-coded rules.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    df = pd.read_parquet(SOURCE_PATH)
    df = df[df["decision_source"].isin(ROW_SOURCES)].copy()
    df = df[df["final_decision"].notna()].copy()
    priors = pattern_records(df)
    priors.to_parquet(OUT_PATH, index=False)
    NOTE_PATH.write_text(render_note(df, priors), encoding="utf-8")
    print(f"Reviewed row corpus: {len(df):,}")
    print(f"Pattern prior rows: {len(priors):,}")


if __name__ == "__main__":
    main()
