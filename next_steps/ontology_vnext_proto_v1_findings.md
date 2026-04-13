# Ontology vNext Prototype v1 Findings

## What was built

We built the first internal layered ontology prototype on top of the current active baseline:

- active corpus: `data/processed/research_allocation_v2_patch_v1/hybrid_corpus.parquet`
- active shortlist: `outputs/paper/23_current_path_mediator_shortlist_patch_v1_labels_generic/current_path_mediator_shortlist.csv`
- concept/context source: `data/production/frontiergraph_concept_public/concept_hard_app.sqlite`

Artifacts written:

- `data/processed/ontology_vnext_proto_v1/canonical_concepts.parquet`
- `data/processed/ontology_vnext_proto_v1/mention_proxy.parquet`
- `data/processed/ontology_vnext_proto_v1/concept_families.parquet`
- `data/processed/ontology_vnext_proto_v1/mapping_table.parquet`
- `data/processed/ontology_vnext_proto_v1/concept_context_signatures.parquet`
- `data/processed/ontology_vnext_proto_v1/edge_evidence_profiles.parquet`
- `outputs/paper/27_ontology_vnext_proto_review/enriched_shortlist.csv`
- `outputs/paper/27_ontology_vnext_proto_review/enriched_shortlist.md`
- `next_steps/ontology_vnext_proto_v1_interpretation.md`

## What passed

The prototype passed every gate in the implementation plan.

- canonical join coverage on the active shortlist: `100%`
- family join coverage on the active shortlist: `100%`
- endpoint context coverage: `97%`
- edge evidence coverage: `94%`
- concepts assigned to more than one family: `0`
- environmental boundary concepts remain separate canonical concepts while sharing one family: `yes`
- mapping kind in this first slice: exact only

This means the prototype is not just conceptually appealing. It is also operationally usable on the current shortlist.

## What the prototype recovers that the active baseline loses

### 1. Family structure without forced merges

The environmental outcome concepts can now be read as:

- separate canonical concepts for ranking and interpretation
- one broader family for cross-concept reasoning

That is the right compromise for a family like:

- `CO2 emissions`
- `ecological footprint`
- `environmental quality`
- `environmental degradation`
- `environmental pollution`

The active flat ontology could only choose between:

- merge them too aggressively, or
- keep them separate with no broader relation

The prototype shows we can keep both levels.

### 2. Context without exploding node identity

The shortlist now carries interpretable node context such as:

- top geographies
- top units of analysis
- representative context fields

This is enough to support statements like:

- a concept is mostly studied at the country level
- a concept is mostly household- or firm-level
- a link is mostly observed in China/OECD/US contexts

without creating a separate node for every context combination.

### 3. Evidence type at the edge level

The shortlist now also tells us whether local pair support is mainly:

- `theory`
- `empirics`
- `mixed`
- `unknown`

and what the dominant design family is.

That is a real expansion of the frontier object. We no longer have to ask only:

- what relation is missing?

We can start asking:

- what empirical confirmation is missing?
- what kind of evidence is missing?
- what context transfer is missing?

## What we learned from the enriched shortlist

The layered overlay is already informative on the current shortlist even without reranking.

Examples:

- some top environmental questions are really **within-family** outcome transitions, not just arbitrary node pairs
- willingness-to-pay questions become more interpretable once the target concept carries household/individual context
- macro/growth examples look different from environmental examples in both context and evidence profile

So the richer ontology is not abstract infrastructure only. It changes how we read the frontier.

## What this does not do yet

This prototype does **not**:

- replace the active ranking baseline
- rerank the frontier
- change public outputs
- add broader/narrower/related/do-not-merge mappings beyond the first minimal family layer

So this is a successful interpretive prototype, not yet a new scoring system.

## Main conclusion

The next ontology gains should come from preserving more structure, not from continuing to hand-clean one label family at a time.

The flat canonical layer was useful for getting the first paper and ranking system working.
But the prototype shows that three additional structures are now mature enough to matter:

1. family layer
2. node context
3. edge evidence

## Concrete next move

The next build should not be another narrow ontology patch.

It should be a small set of **vNext frontier question prototypes** built on top of this layered overlay, for example:

- family-aware frontier questions
- context-transfer questions
- missing empirical confirmation questions
- evidence-type expansion questions

That keeps the active baseline intact while testing whether the richer ontology produces genuinely more useful frontier objects.
