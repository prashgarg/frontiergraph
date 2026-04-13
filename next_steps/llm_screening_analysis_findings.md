# LLM Screening Analysis Findings

Source run:
- `outputs/paper/100_llm_screening_async_runs_99_endpoint_first`

Parsed analysis:
- `outputs/paper/101_llm_screening_analysis_99_endpoint_first`

## Main findings

1. Prompt B (`record_aware`) is materially more generous than Prompt A (`semantic_blind`).
- Mean score: `3.432` vs `2.916`
- High-score share (`>=4`): `0.504` vs `0.292`
- Low-score share (`<=2`): `0.232` vs `0.401`

2. Prompt A/B agreement is only modest.
- Exact score agreement: `0.273`
- Within-one agreement: `0.694`
- Exact triage agreement: `0.360`
- Spearman correlation: `0.174`

3. The main Prompt A/B difference is depth-sensitive.
- On `top` rank-band rows, mean score shift `B - A` is only `0.017`
- On `deep` rank-band rows, mean score shift `B - A` is `0.969`

Interpretation:
- once the candidate is already near the surfaced top, semantic-only and record-aware prompts look much more similar
- deeper in the shelf, graph-local diagnostics push Prompt B toward more charitable readings

4. Pairwise within-field ordering is informative, but not fully aligned with current shelf order.
- Prefer higher-ranked item `A`: `0.552`
- Prefer lower-ranked item `B`: `0.448`
- No ties were emitted

Interpretation:
- the current within-field shelves are directionally sensible
- but they are not close to an LLM-stable final order yet

5. The strongest pairwise reorder pressure appears in:
- `trade-globalization` at `h=10` (`prefer_B = 0.495`)
- `development-urban` at `h=15` (`prefer_B = 0.505`)
- `climate-energy` is consistently noisy (`prefer_B ~ 0.43 - 0.46`)

## Examples

Consistently weak under A and B:
- `Energy sector -> List of countries by number of deaths -> Systemic risk`
- `Stock market bubble -> Fast-moving consumer goods -> Transaction Costs`
- `Econometric analysis -> Discount function -> Decision Making`

Consistently strong under A and B:
- `Water scarcity -> One Water (water management) -> Water use`
- `Corruption -> British Columbia Legislature raids -> Anti-corruption`
- `Medication adherence -> Coverage error -> Unnecessary health care`

Largest A/B disagreements:
- `New energy -> List of largest energy companies -> COVID-19` (`A=1`, `B=5`)
- `Healthcare Cost and Utilization Project -> Apixaban -> Medical services` (`A=1`, `B=5`)
- `Single peaked preferences -> Berne three-step test -> Star-shaped preferences` (`A=1`, `B=5`)

Pairwise reversals that look substantively sensible:
- `Economic expansion -> Biotechnology -> Environmental quality`
  vs
  `Energy Consumption -> Hydrogen production -> Coal pollution mitigation`
- `Clean energy -> Better Environmentally Sound Transportation -> Negative carbon dioxide emission`
  vs
  `Capital Investment -> Information industry -> Energy Efficiency`

## Prompting/runner fix for future runs

`288` single-candidate rows required parser repair because Prompt B responses were truncated in the `reason` field. The structured scores were recoverable, but future runs should still reduce this failure mode directly:

- increase `max_output_tokens`
- or shorten the required `reason`
- or reduce `text.verbosity`

Recommended first fix:
- raise `max_output_tokens` for Prompt B before any next async run
