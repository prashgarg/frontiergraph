# Method-v2 Human Validation Internal Audit

## Purpose

This is an internal assistant QA pass on the refreshed blinded human-validation pack in
`outputs/paper/79_method_v2_human_validation_pack/human_validation_key.csv`.

It is not a substitute for external or human ratings. Its job is narrower:

- catch wording problems that would contaminate the comparison
- separate genuinely weak baseline items from obvious ontology or prompt artifacts
- decide whether the pack is clean enough to use as-is or should be lightly trimmed first

## What was cleaned before this audit

The pack was regenerated after three prompt-level fixes:

- trailing label punctuation is removed in prompt text
- mediator prompts now use a more paper-like template:
  - `Could X be one mechanism linking A to B?`
- design or method mediators now use a method-specific template:
  - `Would X be a useful way to study how A relates to B?`

I also excluded the clearly meta source label `Conceptual framework`, and forced the bureaucratic mediator label `Coordination of Information on the Environment` to fall back to a generic mechanism question.

## Headline judgment

After the cleanup, the pack is substantially better.

- The `graph_selected` arm now mostly reads like real, mechanism-oriented paper questions.
- The `pref_attach_selected` arm is still weaker, but mostly in a fair way: the questions are broader, less specific, or less naturally motivated.
- Only a small number of rows still look weak for reasons that are too artifact-like rather than substantively weak.

My recommendation is:

- use the pack as-is for internal review
- if we send it to external raters, lightly replace the worst `2` rows and optionally a third

## Item-level audit

Judgment labels:

- `keep_strong`: good paper-facing question; no change needed
- `keep_fair_weak`: weaker than the graph arm, but weak in a fair and informative way
- `keep_rewrite_only`: acceptable question, but the wording still carries some awkwardness
- `replace_if_external`: weak enough that it risks testing ontology noise more than ranking quality

| item_id | group | judgment | rationale |
|---|---|---|---|
| `HV001` | `graph_selected` | `keep_rewrite_only` | Plausible, but `Carbon dioxide` is a slightly awkward mediator label for paper-facing prose. The underlying question is still real. |
| `HV002` | `pref_attach_selected` | `keep_fair_weak` | This is a method question rather than a mechanism question, but the current wording makes that explicit and legitimate. |
| `HV003` | `graph_selected` | `keep_strong` | Clear, specific, and naturally reads like a mechanism hypothesis. |
| `HV004` | `pref_attach_selected` | `keep_strong` | Strong baseline item. Reads like a credible finance/corporate mechanism question. |
| `HV005` | `graph_selected` | `keep_rewrite_only` | Plausible but still somewhat broad. `Water use` is a workable mediator, though not as crisp as the strongest graph items. |
| `HV006` | `pref_attach_selected` | `keep_fair_weak` | Broad, but still a real substantive question. Weakness is informative rather than artifactual. |
| `HV007` | `graph_selected` | `keep_strong` | Clear mechanism and good economist-facing phrasing. |
| `HV008` | `pref_attach_selected` | `keep_fair_weak` | Broad, but interpretable. It looks like a real but loose paper idea. |
| `HV009` | `graph_selected` | `keep_strong` | One of the cleaner graph questions. Mechanism is concrete and the endpoints are interpretable. |
| `HV010` | `pref_attach_selected` | `replace_if_external` | `cost-effectiveness analysis -> Willingness to Pay` via `benefit` still reads too meta and too generic. This is closer to concept-bucket noise than a paper idea. |
| `HV011` | `graph_selected` | `keep_rewrite_only` | Reasonable, but `Bid price` is somewhat design-like and domain-specific. Still acceptable. |
| `HV012` | `pref_attach_selected` | `replace_if_external` | `Policy uncertainty` linking `Uncertainty` to `Spillovers` is close to tautological. This risks feeling circular to raters. |
| `HV013` | `graph_selected` | `keep_strong` | Strong and easy to understand. Reads like a real mechanism hypothesis. |
| `HV014` | `pref_attach_selected` | `keep_fair_weak` | Broad but still interpretable. Weakness comes from scope, not prompt noise. |
| `HV015` | `graph_selected` | `keep_strong` | Strong question with a plausible mediator and concrete target. |
| `HV016` | `pref_attach_selected` | `keep_strong` | Strong baseline item. Reads like a legitimate transmission-mechanism question. |
| `HV017` | `graph_selected` | `keep_rewrite_only` | Plausible, though `Policy uncertainty` as a mediator here is a little generic. Still good enough to keep. |
| `HV018` | `pref_attach_selected` | `keep_fair_weak` | Slightly awkward cross-policy mechanism, but still clearly interpretable. |
| `HV019` | `graph_selected` | `keep_rewrite_only` | The question is real, though `Income` is a generic mediator. Acceptable but not among the sharpest items. |
| `HV020` | `pref_attach_selected` | `keep_fair_weak` | Somewhat niche and abstract, but still reads like a real information/frictions question. |
| `HV021` | `graph_selected` | `keep_fair_weak` | The fallback wording is much better than the original label, but the underlying pair remains broad. This is acceptable, though not a showcase item. |
| `HV022` | `pref_attach_selected` | `replace_if_external` | `What mechanism might link Firms to Uncertainty?` is too generic and too endpoint-broad to be a useful external rating item. |
| `HV023` | `graph_selected` | `keep_rewrite_only` | Plausible, though again `Policy uncertainty` is a generic mediator. Fine to keep. |
| `HV024` | `pref_attach_selected` | `keep_fair_weak` | Broad but legitimate. This is a fair weak baseline item. |

## Distributional assessment

### Graph-selected arm

The graph-selected arm now looks materially better than the baseline arm for the right reason:

- more items have a concrete mechanism
- more items feel paper-shaped rather than concept-bucket-shaped
- fewer items are dominated by generic endpoints alone

Its weak points are mostly ordinary ones:

- some mediators are still broad (`Income`, `Policy uncertainty`)
- a few labels remain a bit literal (`Carbon dioxide`, `Bid price`)

These are acceptable weaknesses for a real shortlist.

### Preferential-attachment arm

The baseline arm is still weaker overall, but most of that weakness is informative:

- broader endpoints
- more generic mediators
- less naturally motivated questions

That is fine. A human-validation comparison should preserve that weakness.

The problem is only the small subset where weakness comes from meta labels or near-tautology rather than from ranking quality. Those are the rows I flagged for replacement if we go to external raters.

## Recommended use

### For internal review now

Use the pack as-is.

It is already good enough to tell us whether the refreshed graph-selected frontier is reading better than the baseline.

### For external or paper-facing human ratings

I would lightly trim the worst rows first.

Replace:

- `HV010`
- `HV012`
- `HV022`

If we want to stay maximally faithful to the current baseline draw, keep them and disclose that the baseline includes a few very generic items. But my preference is to replace them with the next-best baseline rows from the same horizon buckets, because that makes the comparison cleaner without changing the qualitative story.

## Bottom line

The wording cleanup solved the main prompt problem.

The remaining issue is not template quality. It is that a few baseline-selected items are still too generic or too meta to be ideal human-rating items. That is now a pack-selection question, not a wording question.
