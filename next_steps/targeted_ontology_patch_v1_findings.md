# Targeted Ontology Patch v1 Findings

## Purpose

This note records the first **narrow, evidence-led ontology patch** on the frozen research-allocation graph.

The patch was executed as a **local experimental corpus-layer intervention** because the full ontology SQLite build chain was not available in this workspace. The key question is still the right one:

- if we merge a small number of clearly duplicated concept families,
- then rerun the same reranker -> current frontier -> path/mechanism shortlist -> concentration stack,
- do we get a materially better current frontier without introducing topic-specific hand bias?

## What was patched

Hard merges:
- emissions core:
  - `FG3C000010` (`carbon emissions`)
  - `FG3C004594` (`carbon emissions (CO2 emissions)`)
  - `FG3C005109` (`CO2 emissions (carbon emissions)`)
  -> `FG3C000003` (`CO2 emissions`)
- environmental quality:
  - `FG3C001420` (`environmental quality (CO2 emissions)`)
  -> `FG3C000081` (`environmental quality`)
- ecological footprint:
  - `FG3C001218` (`ecological footprints`)
  -> `FG3C000064` (`ecological footprint`)
- willingness to pay core:
  - `FG3C000787` (`willingness to pay`)
  -> `FG3C000323` (`willingness to pay`)
- willingness to pay estimates:
  - `FG3C004121` (`willingness to pay estimates`)
  -> `FG3C002310` (`willingness to pay estimates`)

Label overrides:
- `FG3C001033` -> `environmental degradation`
- canonical labels forced for the merged endpoint families above

Artifacts:
- patched corpus: [hybrid_corpus.parquet](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/research_allocation_v2_patch_v1/hybrid_corpus.parquet)
- patch manifest: [manifest.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/research_allocation_v2_patch_v1/manifest.json)
- patch note: [patch_note.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/data/processed/research_allocation_v2_patch_v1/patch_note.md)

## Mechanical effect

- rows: `1,271,014 -> 1,270,732`
- unique concepts: `6,752 -> 6,745`
- unique pairs: `783,681 -> 780,283`

So this was a **small but nontrivial** patch. It did not rewrite the graph wholesale.

## What improved

### 1. Label cleanliness improved sharply

Targeted noisy label hits in the cleaned shortlist fell:
- `43 -> 0`

In practice, this removed surfaced objects like:
- `carbon emissions (CO2 emissions)`
- `environmental quality (CO2 emissions)`
- `willingness to pay (WTP)`

The cleaned shortlist now reads much more like:
- `income tax rate -> CO2 emissions`
- `state of the business cycle -> willingness to pay`
- `CO2 emissions -> ecological footprint`

instead of mixed canonical / parenthetical duplicates.

### 2. The 10-year reranker improved

Best tuned configuration changed from:
- baseline h=10: `glm_logit + structural`, `alpha=0.01`

to:
- patched h=10: `pairwise_logit + composition`, `alpha=0.10`

And the key historical metric improved:
- Recall@100: `0.0609 -> 0.0634`
- delta Recall@100 vs transparent: `+0.0282 -> +0.0301`

The 5-year result was roughly flat:
- Recall@100: `0.0713 -> 0.0716`
- mean MRR moved slightly down

So the patch helped more on the longer horizon than the shorter one.

### 3. Cleaned-shortlist environmental share fell materially

Environment/climate share in the cleaned top-100 shortlist:
- h=5: `50.5% -> 35.0%`
- h=10: `48.5% -> 35.5%`

This matters because it shows that **ontology cleanup alone** can reduce shortlist-level thematic overconcentration without any hand-tuned topic penalty.

## What got worse or became more obvious

### 1. Canonical-node concentration increased

Top endpoint share in the surfaced frontier top 100:
- h=5: `0.105 -> 0.200`
- h=10: `0.110 -> 0.205`

This is not surprising. Once several noisy emissions variants are merged, more mass lands on the canonical `CO2 emissions` node.

In the patched shortlist, the most frequent endpoint became:
- `CO2 emissions` with `26` appearances in the top 100 at both horizons

So the patch reduced **family duplication**, but increased **canonical-node centralization**.

### 2. Some top questions are cleaner but still weak

Examples:
- `price changes -> CO2 emissions`
- `willingness to pay -> CO2 emissions`
- `policy variables -> CO2 emissions`

These are cleaner than before, but some still look broad or underexplained. That means ontology cleanup helped, but did not solve the whole ranking/object problem.

## Interpretation

This was **not** a pure free lunch.

What the patch did:
- remove noisy duplicate labels
- collapse a few repeated ontology failures
- improve long-horizon ranking slightly
- reduce shortlist-level environmental share materially

What it did **not** do:
- eliminate concentration entirely
- make every top current question sharp
- solve generic explanations or broad endpoint problems

The main trade-off is now clearer:

- better ontology cleanup reduces duplicate-family clutter
- but successful merges also make the surviving canonical nodes more central

That is a genuine ontology-side effect, not a bug in the comparison.

## Decision

This patch was worth keeping as an internal method result.

It supports a specific conclusion:
- narrow ontology cleanup can improve frontier quality in a **general, rule-based** way
- but ontology cleanup alone is not enough
- after a successful merge pass, we still need:
  - shortlist-level general repeated-family control
  - better mechanism/path explanations
  - possibly more ontology work on adjacent families

## Recommended next step

Do **patch set v2**, but keep the same discipline:

1. patch only clear family-level ontology problems
2. rerun the same frozen-ontology pipeline
3. compare:
   - label cleanliness
   - reranker metrics
   - shortlist thematic shares
   - canonical-node concentration

The next likely ontology targets are:
- `environmental degradation` / `environmental pollution` / `environmental quality` boundary
- recurrent generic mediator labels in the top current shortlist
- broader family cleanup around `policy variables` and similarly weak container endpoints
