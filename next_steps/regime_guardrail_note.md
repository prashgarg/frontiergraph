# Regime Guardrail Note

## Scope

This note reviews:

- `outputs/paper/34_design_family_inference_review/broader_regime_bundle_guardrailed.csv`
- `outputs/paper/34_design_family_inference_review/broader_regime_bundle_kept.csv`
- `next_steps/reviewed_policy_edge_semantics.csv`

The goal is to record the post-freeze state of the broader regime queue after adding the last reviewed residual policy row.

## Main result

The regime layer is now cleaner than before.

Current counts are:

- `broader_regime_rows`: `13`
- `keep`: `9`
- `drop`: `4`

Drop reasons:

- `generic_policy_object`: `2`
- `boundary_case`: `2`

Kept semantic split:

- `policy_instrument`: `6`
- `policy_target`: `2`
- `governance_regime`: `1`

## What changed

The earlier weak residual row:

- `CO2 emissions -> mitigation`

is no longer in the kept regime queue.
It is now handled as a reviewed generic policy object in:

- `next_steps/reviewed_policy_edge_semantics.csv`

So the kept queue no longer carries an `unclassified` residual.

## What dropped

The dropped rows are now exactly the ones we do not want in the clean regime slice:

- `CO2 emissions -> policy`
- `CO2 emissions -> mitigation`
- `taxes -> income tax rate`
- `income tax rate -> corporate tax rate`

## What stayed

The kept rows remain coherent policy-semantic objects, including:

- `CO2 emissions -> international emissions trading`
- `CO2 emissions -> Emission Trading Scheme (ETS)`
- `CO2 emissions -> carbon neutrality target`
- `CO2 emissions -> Intended Nationally Determined Contributions (INDCs)`
- `monetary policy -> state of the business cycle`
- `tax compliance -> income tax rate`

## Current judgment

The coarse regime semantics plus light guardrail are stable enough to keep as part of the internal edge layer.

The right next move is **not** to widen the regime queue again.
It is to treat the current reviewed policy semantics table as the stable internal source of truth.

## Recommendation

Do:

1. keep the reviewed policy semantics and guardrail fields in the ontology-vNext edge artifacts
2. treat the regime layer as frozen except for future reviewed override rows
3. use the kept regime rows as paper-extension or internal-interpretation examples, not as a new surfaced object family
