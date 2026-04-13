# Ontology vNext Next Steps

## Where we are

We now have enough evidence to stop guessing about the next ontology move.

Current active baseline:

- patch `v1`
- mediator-label propagation
- generic container endpoint rule
- explanation-layer alias cleanup
- current path/mechanism shortlist builder

Patch `v2` was useful diagnostically, but rejected as the new active baseline.

The first layered internal ontology prototype is now also built and passes its coverage checks:

- canonical join coverage: `100%`
- family join coverage: `100%`
- endpoint context coverage on the active shortlist: `97%`
- edge evidence coverage on the active shortlist: `94%`

Prototype outputs:

- [ontology_vnext_proto_v1_findings.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/ontology_vnext_proto_v1_findings.md)
- [enriched_shortlist.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/27_ontology_vnext_proto_review/enriched_shortlist.md)
- [ontology_vnext_proto_v1_interpretation.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/ontology_vnext_proto_v1_interpretation.md)
- [vnext_frontier_question_prototype_findings.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/vnext_frontier_question_prototype_findings.md)
- [frontier_question_prototypes.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/28_vnext_frontier_question_prototypes/frontier_question_prototypes.md)

## What that means

The next gains are unlikely to come from another small label-only patch in the same style.

The next gains are more likely to come from redesigning **what information the ontology preserves** and then using that richer structure to create new frontier objects.

## Priority order

### 1. Use the layered prototype to define vNext frontier objects

Why first:

- we now have a working family/context/evidence overlay
- the next question is whether it enables better frontier objects, not whether the data can be built at all

Initial object families to prototype:

- family-aware frontier questions
- context-transfer questions
- missing empirical confirmation questions
- evidence-type expansion questions

Working findings:

- [ontology_vnext_proto_v1_findings.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/ontology_vnext_proto_v1_findings.md)
- [vnext_frontier_question_prototype_findings.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/vnext_frontier_question_prototype_findings.md)

Current read:

- strongest: context-transfer questions
- next strongest: evidence-type expansion questions
- also promising: missing empirical confirmation questions
- narrower for now: family-aware questions, because only one explicit broader family is seeded in this first slice

We now also have a conservative routing-layer experiment on top of the active shortlist:

- [vnext_frontier_objects_working_note.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/vnext_frontier_objects_working_note.md)
- [vnext_routed_shortlist_manual_review.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/vnext_routed_shortlist_manual_review.md)

Current read on the routing layer:

- good architecture: baseline path/mechanism object by default, routed vNext object only when the richer signal is strong
- next bottleneck: generic endpoints can still make some routed context-transfer questions feel weak
- next refinement should therefore be a **general endpoint-genericity guardrail**, not a topic-specific rule

### 2. Layered ontology first, as the structural default

Why second:

- this is the cleanest way to represent synonym vs broader/narrower vs do-not-merge
- the prototype confirms that the current single-layer graph is leaving useful structure on the floor

Working spec:

- [layered_ontology_v1_spec.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/layered_ontology_v1_spec.md)

### 3. Node-context signatures

Why third:

- many concepts are only interpretable with setting
- we want context without exploding node identity

Working spec:

- [node_context_signature_schema_v1.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/node_context_signature_schema_v1.md)

### 4. Edge-evidence attributes

Why fourth:

- many useful frontier questions are really about missing evidence type, not missing concept relation
- this is where theory vs empirics and design family become first-class

Working spec:

- [edge_evidence_schema_v1.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/edge_evidence_schema_v1.md)

## Practical implementation order

1. ontology creation postmortem
2. layered ontology schema tables
3. mention -> concept -> family mapping prototype
4. node-context signature prototype
5. edge-evidence schema prototype
6. build read-only enriched frontier question prototypes on top of the overlay
7. choose the 1 to 2 strongest prototype families for a second-generation scoring experiment
8. add a generic-endpoint guardrail to the routed object layer
9. only then test any ranking or surfacing changes

## What we should not do next

- not another topic-specific or family-specific ranking nudge
- not more narrow label cleanup unless it is needed to support the layered redesign
- not public release integration yet

## Main design principle

We should keep using **general, rule-based, reproducible** interventions.

The point is not to make the current shortlist look nice by hand.
The point is to make the representation itself richer, so the cleaner shortlist falls out of the system more naturally.
