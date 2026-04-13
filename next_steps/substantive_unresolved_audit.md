# Substantive Unresolved Audit

## Scope

This note reviews the top of the new `substantive_unresolved` audit bucket after the typed evidence pass.

The point is not to treat this whole bucket as one problem.
The point is to identify what kinds of unresolved edges remain once method-heavy and metadata-heavy tails are separated out.

## Current scale

Current bucket counts:

- `substantive_unresolved`: `276038`
- `method_artifact`: `24103`
- `metadata_container`: `24201`

So the largest unresolved pool is still substantive.

That is useful to know.
It means the unknown-evidence tail is not mostly a method-label problem once the typed audit buckets are in place.

## New substantive subtype split

Inside `substantive_unresolved`, the new deterministic subtype layer now separates:

- `policy_outcome_or_boundary`: `78793`
- `event_institution_context`: `15739`
- `finance_attribute_bundle`: `16657`
- `quantity_count_object`: `5248`
- `general_substantive_other`: `159601`

Priority split:

- `high`: `78793`
- `medium`: `191997`
- `low`: `5248`

This is the main improvement from this pass.

We no longer just know that a row is “substantive.”
We now know what kind of substantive unresolved row it is and how urgently it should be reviewed.

## New review pack

The unresolved queue now has a dedicated reproducible review pack at:

- `outputs/paper/31_substantive_unresolved_review/`

That pack currently includes:

- top `50` `policy_outcome_or_boundary` rows
- a balanced `75`-row cross-subtype review set

It also adds review-only flags such as:

- `same_reviewed_family`
- `has_context_entity`
- `likely_boundary_case`
- `likely_regime_or_implementation_bundle`

## High-support patterns

Representative high-support pairs in the substantive bucket include:

- `COVID-19 outbreak -> World Health Organization (WHO)`
- `default -> bank-specific characteristics`
- `CO2 emissions -> environmental quality`
- `country income level -> countries`
- `COVID-19 outbreak -> country income level`
- `COVID-19 pandemic -> COVID-19 outbreak`
- `drug prices -> Generic drugs`
- `CO2 emissions -> energy efficiency`
- `airports -> number of flights`
- `inflation -> unemployment`

Representative subtype leaders are now:

### `policy_outcome_or_boundary`

- `CO2 emissions -> environmental quality`
- `drug prices -> Generic drugs`
- `CO2 emissions -> energy efficiency`
- `taxes -> income tax rate`
- `house prices -> housing stock`

### `event_institution_context`

- `COVID-19 outbreak -> World Health Organization (WHO)`
- `country income level -> countries`
- `COVID-19 outbreak -> country income level`
- `COVID-19 pandemic -> COVID-19 outbreak`
- `HIV prevalence -> World Health Organization (WHO)`

### `finance_attribute_bundle`

- `default -> bank-specific characteristics`
- `bank-specific characteristics -> banking`
- `default -> defaults`
- `deposits -> bank-specific characteristics`
- `default -> lenders`

### `quantity_count_object`

- `number of agents -> place of residence`
- `number of flights -> number of passengers`
- `airports -> number of flights`
- `price changes -> number of trades`
- `bid-ask spread -> number of trades`

## What these rows are telling us

There are at least four different substantive-unresolved subtypes hiding in the same bucket.

### 1. Real substantive frontier candidates

Examples:

- `CO2 emissions -> environmental quality`
- `CO2 emissions -> energy efficiency`
- `inflation -> unemployment`
- `taxes -> income tax rate`

These look like real unresolved or weakly typed substantive relations.
They are the highest-value rows for manual review because they may reflect:

- genuine missing evidence-type labeling
- genuine ontology boundary ambiguity
- or genuinely interesting edge objects

After the deeper top-25 policy review, the manual labels now split as:

- `strong_substantive`: `14`
- `boundary_or_near_duplicate`: `5`
- `regime_or_implementation_bundle`: `3`
- `weak_or_mixed`: `3`

That makes the next review queue much more usable than before.

### 2. Event / institution / geography entanglements

Examples:

- `COVID-19 outbreak -> World Health Organization (WHO)`
- `COVID-19 outbreak -> country income level`
- `sub-Saharan Africa -> World Health Organization (WHO)`

These look less like ordinary substantive frontier pairs and more like:

- event-context entanglements
- institution / actor references
- or context-bearing concepts that want richer type structure

This is a sign that node typing still benefits from a richer entity layer, even though the latest dictionary-backed pass already cleaned the top policy queue materially.

### 3. Finance / banking attribute bundles

Examples:

- `default -> bank-specific characteristics`
- `deposits -> bank-specific characteristics`
- `bank-specific characteristics -> banking`
- `default -> lenders`

These look like structured domain bundles rather than clean paper-facing frontier objects.
They are likely useful for ontology cleanup, but not strong surfaced objects in their current form.

### 4. Quantity / counting objects

Examples:

- `number of flights -> number of passengers`
- `number of agents -> place of residence`
- `number of trades -> bid-ask spread`

These are substantive in the narrow type sense, but many are still weak surface objects.
They may benefit from a later concept-type refinement that distinguishes:

- quantity/count variables
- domain entities
- institutions/actors
- and substantive outcomes

## What to prioritize next

Priority order inside `substantive_unresolved` should be:

1. clear substantive policy/outcome pairs
2. ontology-boundary cases inside already-important domains
3. event/institution/context entanglements
4. structured finance/count-object tails

That means rows like:

- `CO2 emissions -> environmental quality`
- `CO2 emissions -> energy efficiency`
- `inflation -> unemployment`

deserve earlier attention than:

- `number of agents -> place of residence`
- `default -> lenders`

## Recommendation

Use `substantive_unresolved` as the next real audit queue.

Do not flatten it into one generic unknown bucket again.

The next useful move should now come from the review pack, especially:

- high-value substantive policy/outcome pairs
- event / institution objects
- banking attribute bundles
- count / quantity objects

The practical review order should now be:

1. `policy_outcome_or_boundary`
2. `event_institution_context`
3. `finance_attribute_bundle`
4. `quantity_count_object`
5. `general_substantive_other`

The deeper policy review is now recorded in:

- `next_steps/policy_outcome_or_boundary_deep_review.md`
