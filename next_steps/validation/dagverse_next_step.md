# DAGverse: Next Validation Step

Date: 2026-04-01

## What is now ready

The ArXiv-backed abstract-level DAGverse slice has now been materialized successfully.

Files:
- `next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark.jsonl`
- `next_steps/validation/data/dagverse/frontiergraph_arxiv_abstract_true_benchmark_manifest.json`

Summary:
- requested rows: `25`
- materialized rows: `25`
- errors: `0`
- rough total input tokens: `8,548`
- rough mean input tokens per paper: `341.92`

## Why DAGverse matters after ReCITE

The ReCITE pilot showed that exact-match metrics can be misleading when:
- the benchmark gold graph is more operational or figure-specific than the abstract
- our extraction is more semantic and paper-summary oriented

DAGverse may be a fairer second benchmark because:
- the graphs are smaller
- they are explicitly semantic DAGs
- they are grounded in paper content rather than only generic reasoning tasks
- the selected `abstract=true` rows are explicitly compatible with abstract-level extraction

## Expected comparison advantages over ReCITE

Compared with ReCITE, we expect:
- fewer nodes per graph
- less ontology spread within a single paper
- better alignment between abstract-level content and graph-level target
- fewer cases like ReCITE paper `90`, where the gold loop is not really recoverable from the abstract

## Remaining challenge

Even here, exact string matching will still be too strict.
We should reuse the same layered evaluation logic:

1. exact node matching
2. normalized matching
3. embedding-assisted matching
4. agentic/manual semantic judgment

## Recommended immediate run

Run a small pilot first:
- `5` DAGverse papers
- `gpt-5-mini`
- `low` reasoning

Reason:
- cheap
- enough to check whether DAGverse is genuinely a fairer benchmark than ReCITE
- enough to see whether the semantic-vs-operational mismatch is smaller

## Practical hypothesis

If DAGverse behaves as expected, then:
- node-level semantic overlap should improve meaningfully relative to ReCITE
- edge-level overlap may still lag, but less severely
- manual mapping should look more like ordinary synonym/abstraction reconciliation and less like "different graph object entirely"

## Best use of DAGverse

DAGverse should probably become:
- the cleaner benchmark for semantic graph recovery from title + abstract

ReCITE should remain:
- the harder stress test for ontology mismatch and graph-object mismatch
