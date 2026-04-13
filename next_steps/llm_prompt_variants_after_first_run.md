# LLM Prompt Variants After First Run

Updated pack:
- `outputs/paper/102_llm_screening_prompt_pack_v2_endpoint_first`

## Why the pack changed

The first async run showed three concrete issues:

1. `record_aware` was too generous on semantically odd deep-tail candidates.
2. `record_aware` responses were verbose enough to trigger truncated JSON in some rows.
3. Pairwise within-field judgments may still contain order bias, and coarse veto-style screening may be more stable than a 1-5 score.

## Active variants

### Prompt A: semantic_blind
Role:
- harsh semantic counterweight

What it tests:
- whether the candidate reads like a sharp question object using only labels and family tags

### Prompt B: record_aware (v2)
Change:
- now explicitly skeptical
- says numeric support cannot rescue semantically weak objects
- short reason requirement
- higher output-token headroom, but lower verbosity

What it tests:
- whether graph-local diagnostics add value without making the model too charitable

### Prompt C: pairwise_within_field (v2)
Change:
- stronger tie instruction
- explicit warning not to force a choice

What it tests:
- shelf ordering quality within field, with fewer artificial forced comparisons

### Prompt E: veto_screen
New.

What it tests:
- whether a coarse pass/review/fail screen is more stable and defensible than a 1-5 scalar score

Likely use:
- first-pass paper-worthiness filter before any finer reranking

### Prompt F: pairwise_within_field_swapped
New.

What it tests:
- position bias in pairwise judgments by swapping A/B order on the same pair set

Likely use:
- compare Prompt C vs Prompt F on the same pairs
- if choices change often under swapping, pairwise results need debiasing or aggregation

## Concrete motivating examples

Examples where Prompt B v1 looked too generous:
- `New energy -> List of largest energy companies -> COVID-19`
- `Healthcare Cost and Utilization Project -> Apixaban -> Medical services`
- `Single peaked preferences -> Berne three-step test -> Star-shaped preferences`

Examples that should fail under a stronger veto screen:
- `Energy sector -> List of countries by number of deaths -> Systemic risk`
- `Stock market bubble -> Fast-moving consumer goods -> Transaction Costs`

Examples useful for pairwise swap checks:
- `Economic expansion -> Biotechnology -> Environmental quality`
  vs
  `Energy Consumption -> Hydrogen production -> Coal pollution mitigation`
- `Clean energy -> Better Environmentally Sound Transportation -> Negative carbon dioxide emission`
  vs
  `Capital Investment -> Information industry -> Energy Efficiency`

## Recommended next run order

1. rerun `Prompt B v2` on the same 2000 rows
2. run `Prompt E` on the same 2000 rows
3. run `Prompt F` on the same 2000 pairs
4. compare:
   - A vs Bv2 generosity gap
   - score vs veto stability
   - C vs F order sensitivity
