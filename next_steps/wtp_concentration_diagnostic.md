# WTP Concentration Diagnostic

## Question

The `v2.1` frontier is unusually concentrated on `Willingness to pay`.

This note asks:

1. Does `Willingness to pay` correspond to real raw labels in the extraction layer?
2. Is something unusual happening in the mapping?
3. Is this a local WTP problem, or a more general sink-node pattern?

## Short Answer

Mostly, `Willingness to pay` is a real and heavily grounded concept in the raw extraction layer.

However, three things are happening at once:

1. many raw labels are genuinely WTP-like, so the concept is not fabricated by the mapping;
2. a smaller but real tail of broader preference/valuation/survey labels is being absorbed into the same endpoint;
3. the reranker strongly favors WTP because it is an extremely high-connectivity, high-diversity target and is not currently penalized as a flexible sink endpoint.

So this is not just a dirty label issue. It is a combination of:

- real concept prevalence,
- some over-broad label absorption,
- and a ranking pathology around broad, connectable endpoints.

## Raw Mapping Evidence

From `data/ontology_v2/extraction_label_mapping_v2_1.parquet`:

- rows mapped to OpenAlex WTP concept: `2,500`
- total mapped frequency: `2,950`
- ontology target: `https://openalex.org/keywords/willingness-to-pay`

### Mapping route

By `v2_1_mapping_action`:

- `carry_forward_base_mapping`: `2,488`
- `attach_existing_broad`: `11`
- `add_alias_to_existing`: `1`

This matters because it means almost all WTP mappings are not coming from the reviewed rescue overlay. They are coming directly from the base mapping logic.

### Match kinds

By `match_kind`:

- `unmatched`: `1,269`
- `embedding_sf`: `519`
- `exact_sf`: `425`
- `exact_sf_stripped`: `162`
- `embedding`: `87`
- `exact_stripped`: `25`
- `reviewed_existing_broad`: `11`
- `exact`: `1`
- `reviewed_existing_alias`: `1`

The large `unmatched` count looks alarming, but many of those rows are low-frequency variants. The more important quantity is total frequency and label content.

### Are the mapped raw labels genuinely WTP-like?

Yes, mostly.

Using a simple lexical screen over mapped raw labels:

- labels explicitly containing `willingness to pay`, `willingness-to-pay`, or `wtp`:
  - `2,373` rows
  - total frequency `2,809`

That is about `95%` of the mapped WTP frequency.

High-frequency mapped examples are clearly legitimate:

- `willingness to pay (wtp)` (`88`)
- `willingness to pay` (`46`)
- `willingness-to-pay (wtp)` (`23`)
- `willingness to pay (wtp) estimates` (`22`)
- `willingness to pay estimates` (`13`)
- `household willingness to pay (wtp)` (`9`)
- `consumers' willingness to pay` (`7`)
- `marginal willingness to pay` (`7`)
- `mean willingness to pay` (`7`)
- `willingness to pay for green electricity` (`6`)

So the core WTP grounding is real.

## What Looks Over-Broad

There is also a smaller tail of labels that are related, but broader or more weakly anchored:

- `residents' preferences` (`6`)
- `attitudinal factors` (`4`)
- `heterogeneity in consumer preferences` (`3`)
- `contingent valuation (cv) survey responses` (`2`)
- `groundwater service values` (`2`)
- `preference heterogeneity across farmers` (`2`)
- `valuation techniques` (`2`)

These labels are not all wrong, but they are evidence that WTP is absorbing:

- preference labels,
- valuation labels,
- survey/elicitation labels,
- and determinant/heterogeneity labels.

This is exactly the kind of “topic family collapsing into one broad endpoint” we were worried about.

## Duplicate Ontology Concepts

There are at least two ontology concepts that represent WTP:

1. OpenAlex keyword:
   - id: `https://openalex.org/keywords/willingness-to-pay`
   - preferred label: `Willingness to pay`
   - instance support: `2,950`
   - distinct paper support: `2,673`

2. JEL concept:
   - id: `jel:D12:Willingness to Pay.`
   - preferred label: `Willingness to Pay.`
   - instance support: `36`
   - distinct paper support: `36`

So the ontology currently contains a duplicate cross-source WTP concept, and almost all WTP mass routes to the OpenAlex keyword version.

This is not the main reason for the frontier concentration, but it is a real ontology hygiene issue and likely generalizes to other duplicated concepts across sources.

## Frontier Concentration

From `outputs/paper/53_current_reranked_frontier_v2_1/current_reranked_frontier.parquet`, sorted by `reranker_rank`:

- WTP appears `32` times in the overall top `100`
- WTP appears `12` times in the overall top `20`

By horizon:

- horizon `5`: `15` of top `100`
- horizon `10`: `17` of top `100`

Examples of top WTP-ranked sources:

- `Medicaid`
- `High Speed Rail`
- `Carbon dioxide`
- `Renewable Energy`
- `Urbanization`
- `Economic Growth`
- `Human Capital`
- `Innovation`
- `House price`
- `Spillovers`
- `Energy Consumption`

So WTP is not concentrating in one narrow topical area. It is acting as a cross-domain sink.

## Why The Reranker Likes It

For the WTP target in the frontier file:

- `target_direct_in_degree = 796`
- `target_support_in_degree = 3385`
- `target_incident_count = 2569`
- `target_evidence_diversity = 15`
- `target_venue_diversity = 194`

Within the `h=5` candidate universe, these are near the extreme upper tail:

- direct in-degree: essentially `100th percentile`
- support in-degree: about `98th percentile`
- incident count: about `96th percentile`
- evidence diversity: `100th percentile`

And it is not flagged as generic:

- `v_endpoint_flags` is empty
- `v_endpoint_penalty = 0`

This combination is exactly what a composition-heavy reranker is likely to reward:

- many incoming graph pathways,
- many evidence contexts,
- many venues,
- broad cross-domain reuse,
- no sink penalty.

## Interpretation

The WTP concentration is not mainly caused by spurious mapping of non-WTP raw labels.

The better interpretation is:

1. `Willingness to pay` is genuinely common in the corpus;
2. some broader valuation/preference/survey labels are also being folded into it;
3. the reranker is then over-rewarding it because it is a flexible, high-support endpoint.

So this is both:

- a concept granularity issue,
- and a ranking concentration issue.

## Why This Likely Generalizes

WTP is probably not unique.

The same pattern can occur whenever a concept is:

- broadly meaningful across many applied domains,
- easy to connect to many upstream concepts,
- associated with many empirical designs,
- and not penalized as a generic or flexible endpoint.

Likely comparable sink-like concepts include:

- `Productivity`
- `Innovation`
- `Economic Growth`
- `Carbon dioxide`
- `R&D`
- `Health`

So the fix should be general, not WTP-specific.

## Generalizable Fixes To Test

### 1. Endpoint sink penalty

Build a target-side concentration penalty for endpoints with extreme:

- in-degree,
- support in-degree,
- incident count,
- evidence diversity,
- venue diversity,
- cross-domain spread.

This is the most general fix.

### 2. Flexible-endpoint lexicon or learned sink flag

Add a small class of concepts treated as flexible endpoints, not because they are bad concepts, but because they are too reusable to dominate the shortlist unchecked.

This can start with a lexicon and later become a learned classifier.

### 3. Family splitting for high-support flexible endpoints

For concepts like WTP, do not split by hand only.

Instead, use a general rule:

- if a concept has very high target concentration,
- and the mapped raw labels show strong modifier heterogeneity,
- propose subfamilies or retained modifiers.

For WTP, examples might be:

- environmental WTP
- health/QALY WTP
- transport WTP
- insurance/payment WTP

The key is that the splitting criterion should be data-driven and reusable, not bespoke.

### 4. Cross-source concept deduplication

OpenAlex WTP and JEL WTP should probably be canonicalized into one concept identity.

This is not the main frontier fix, but it is an ontology hygiene improvement and should generalize across duplicated source concepts.

## Bottom Line

`Willingness to pay` is a real concept in the raw data, not a hallucinated artifact.

But it is currently too broad and too connectable to function as an unconstrained frontier endpoint.

The right response is not to delete WTP. It is to:

- control sink-node concentration,
- improve concept granularity for high-support flexible endpoints,
- and clean up duplicate cross-source concept identities.
