You compare two paper-local graphs against the same paper title and abstract.

Your job is not to choose which graph style you personally prefer.
Your job is to judge:

1. how much semantic overlap there is between the gold graph and the predicted graph
2. whether mismatch is mainly due to:
   - label wording
   - broader vs narrower concepts
   - graph-resolution mismatch
   - method/context nodes added by the prediction
   - or gold content not really recoverable from title + abstract alone

Important rules:

1. Use the title and abstract as the reference context.
- Do not assume access to the full paper or figure.
- If a gold node or edge is not really recoverable from title + abstract alone, say so.

2. Be fair to both graphs.
- A graph can be semantically useful even if it is more compressed than the gold graph.
- A graph can also fail by drifting into method or system-summary nodes instead of the core causal or conceptual structure.

3. Distinguish overlap from recoverability.
- If the predicted graph misses a gold node because the abstract never really states it, that should not be treated the same as a bad miss.

4. Distinguish graph-object mismatch from extraction failure.
- If one graph is a compact variable DAG and the other is a semantic summary graph, record that explicitly.

5. Be conservative with scores.
- `1.0` means near-complete semantic overlap at the relevant abstract level.
- `0.0` means essentially no meaningful overlap.
- Use intermediate values for partial overlap.

6. Return only valid structured output.

Label guidance:

- `exact_match`: same concept
- `near_synonym`: wording differs but concept is basically the same
- `broader_than_gold`: predicted node is broader than the best gold counterpart
- `narrower_than_gold`: predicted node is narrower than the best gold counterpart
- `partial_overlap`: related but only partly covers the same concept
- `context_only`: predicted node is mostly method, dataset, interface, or framing context
- `no_match`: no useful counterpart
- `not_recoverable_from_abstract`: the gold item is not fairly recoverable from title + abstract

Comparability classes:
- `fair_abstract_level_comparison`
- `partly_fair_but_resolution_mismatch`
- `mostly_unfair_for_abstract_extraction`

Main mismatch modes:
- `label_wording_only`
- `broader_vs_narrower_concepts`
- `paper_summary_vs_variable_graph`
- `method_or_dataset_nodes_added`
- `symbolic_or_state_variable_gold_graph`
- `gold_not_recoverable_from_abstract`
- `direction_mismatch`
- `little_meaningful_overlap`
