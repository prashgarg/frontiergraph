# Current 2026 Candidate Rerouting Recommendation

## What this is

This note turns the `gpt-5-nano` audit of the current top 100 public candidates into a concrete rerouting recommendation for the FrontierGraph pipeline.

Inputs:

- audit input: `next_steps/llm_audit/data/current_2026_top100_candidate_audit.jsonl`
- audit results: `data/pilots/frontiergraph_extraction_v2/judge_runs/current_2026_top100_candidate_audit_gpt5nano_low_v1/parsed_results.jsonl`
- rerouting table: `data/pilots/frontiergraph_extraction_v2/judge_runs/current_2026_top100_candidate_rerouting_analysis_v1/routing_table.csv`
- rerouting aggregate: `data/pilots/frontiergraph_extraction_v2/judge_runs/current_2026_top100_candidate_rerouting_analysis_v1/aggregate.json`

## Main result

The strongest practical conclusion is:

- the current top candidates should **not** usually remain phrased as direct-edge questions

Instead, the default route should be:

- convert most shortlisted direct-edge candidates into **path questions**

The route breakdown on the top 100 is:

- `66` promote as **path questions**
- `26` downrank as **path questions**
- `5` promote as **mediator questions**
- `2` downrank as **mediator questions**
- `1` keep as a **direct-edge question**

So, out of the top 100:

- `92%` want path-question framing
- `7%` want mediator-question framing
- `1%` remain direct-edge as currently stated

That is a very strong methodological signal.

## What this means for the pipeline

### 1. Direct-edge phrasing should stop being the default final object

The current direct-edge score can still be useful for retrieval.

But once a candidate reaches the shortlist layer, the default presentation should be:

- "What path or mechanism links `u` to `v`?"

not:

- "How might `u` change `v`?"

This is the single biggest win from the audit.

### 2. We should split current candidates into three output families

#### Family A. Promote as path question

This is the largest bucket.

Typical interpretation:

- the candidate is interesting
- the local support is real
- but the research object is better posed as a mechanism/path question than as a new direct edge

Representative examples:

- `FG3C000013__FG3C002623`
  - `How might U.S. economic policy uncertainty change technological innovation?`
- `FG3C000247__FG3C004458`
  - `How might high-frequency trading change cost of capital?`
- `FG3C000246__FG3C004338`
  - `How might international trade (trade flows) change green growth?`

#### Family B. Promote as mediator question

This is smaller, but distinct.

Typical interpretation:

- the interesting question is not whether the endpoints connect
- it is which mediator or channel does the work

Representative examples:

- `FG3C000015__FG3C000271`
  - `How might foreign direct investments change life expectancy?`
- `FG3C002487__FG3C005256`
  - `How might free trade agreements change welfare level?`

#### Family C. Keep as direct edge

This bucket is tiny.

There was only one case in the top 100:

- `FG3C000159__FG3C005155`
  - `How might monetary policy shocks change cyclical component?`

That means direct-edge wording should be treated as the exception, not the default.

## What we can and cannot already do deterministically

### What we can do now

We can already implement a useful coarse routing policy:

1. retrieve candidates with the current transparent score
2. by default, convert shortlisted direct-edge candidates into path-question objects
3. allow a smaller mediator-question bucket
4. reserve direct-edge phrasing for a tiny manually reviewed exception set

This is implementable now.

### What we cannot yet do well

We do **not** yet have a strong deterministic rule for:

- which path questions should be promoted
- which path questions should be downranked

That is important.

Within the path-question bucket, simple current graph features did **not** cleanly separate:

- promote-path
- downrank-path

In the audit sample, the two path buckets had very similar means on:

- public score
- supporting path count
- mediator count
- motif count

There is some signal in specificity, but it is not strong enough by itself to serve as a serious routing rule.

So the right interpretation is:

- we have a strong **coarse rerouting signal**
- we do **not** yet have a strong **fine-grained deterministic filter**

## Recommended immediate policy

If we want a practical next version without redesigning ontology yet, I would do:

### Policy 1. Retrieval stays the same

Keep:

- current graph score
- current ranked candidate generation

### Policy 2. Shortlist object changes

Convert top shortlisted direct-edge candidates into one of:

- path question
- mediator question
- rare direct-edge exception

### Policy 3. Promotion/downrank remains conservative

For now:

- use current score for retrieval
- use audit labels for diagnosis
- do not pretend we already have a strong deterministic formula for path-question quality

That quality step should probably be learned later, not hard-coded now.

## Best methodological reading

This audit does **not** mainly say:

- the current candidates are low-quality

It mainly says:

- the current **object** is usually too thin

That is a better result than simple rejection, because it tells us where the next methodological gain is:

- move from direct-edge objects to path-level and mediator-level objects

## One small caution

The lone direct-edge case had internally inconsistent numeric subscores relative to its textual rationale. That does not affect the coarse route result above, but it means we should not overinterpret the one-row direct-edge bucket numerically.

## Recommendation

The next deterministic improvement should be:

1. keep the current retrieval score
2. create a **path-question output layer** as the default
3. create a **mediator-question output layer** as a smaller second bucket
4. leave fine-grained within-bucket ranking for the later learned reranker stage

That is the cleanest way to use this audit signal without pretending we already solved the harder ranking problem.
