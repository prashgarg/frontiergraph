# Option C Parallel Prep

Date: 2026-04-12

These are the highest-value family-agnostic tasks to do while the `direct-to-path`
benchmark and reranker runs are computing.

They are chosen to avoid two failure modes:

- rewriting the paper before the family comparison exists
- wasting time on tasks that will be invalidated by the family comparison

## 1. Paper restructure under Option C

The likely main-text structure, if the family comparison is worth keeping, is:

1. question choice under scarce attention
2. corpus, paper-local extraction, and graph construction
3. two historical objects
   - `path-to-direct`
   - `direct-to-path`
4. main comparison
   - strict shortlist
   - richer ranking rule
   - reading-budget frontier
5. where each family helps more
6. surfaced examples and path development
7. discussion and limits

The key writing rule is:

- define both objects early in plain language
- do not yet tell the reader that one is the “cleaner” validation object
- let the side-by-side results and examples establish the case

## 2. Intro example replacements

The current intro example should stop leading with a case where the direct edge sounds
like the wrong economic object.

Good `path-to-direct` examples:

- broadband access -> search frictions -> business formation
- transit investment -> commute time -> employment
- trade liberalization -> imported inputs -> firm productivity
- childcare subsidies -> maternal labor supply -> household income

Good `direct-to-path` examples:

- broadband access -> business formation, later thickened by search frictions
- trade liberalization -> firm productivity, later thickened by imported inputs
- transit investment -> employment, later thickened by commute time

Recommended introduction move:

- lead with a `direct-to-path` example because it is closer to what economists care
  about
- then say that the paper studies two empirically distinct forms of research progress:
  direct closure and mechanism thickening

## 3. Intro paragraph draft direction

The introduction should eventually say something close to this:

- economists often care about whether a known relation works through a specific channel
- other times they care about whether local structure already implies a direct relation
  that later becomes explicit
- the paper studies both objects prospectively in the same literature graph

That is better than opening as if the project were only about missing direct edges.

## 4. Appendix graph-evolution figure

This figure is family-agnostic and should be built regardless of which family ends up
foregrounded.

Recommended multi-panel figure:

- Panel A: number of active concepts over time
- Panel B: number of active support edges over time
- Panel C: average degree and 90th percentile degree over time
- Panel D: giant connected-component share over time
- Panel E: sampled shortest-path distribution over time
- Panel F: clustering / transitivity over time

Optional later panel, after path-length runs:

- Panel G: share of candidate support coming from lengths 2, 3, 4, and 5

What this figure should teach:

- the graph becomes denser over time
- the graph is already short-path by the later sample
- longer-path search should therefore be treated as a disciplined extension, not as a
  free novelty dial

## 5. Why this matters for the path-length extension

If the graph is already dominated by shortest paths of length 3 and 4, then setting
`max_len = 10` does not buy a clean “creative” object. It mostly risks turning the
screen into generic graph proximity.

So when the family comparison is done, the path-length appendix should likely test:

- `2`
- `3`
- `4`
- maybe `5`

Not:

- `10`

## 6. Family-paired examples section

Once the runs finish, the examples section should not just list top examples by family.
It should try to pair them conceptually.

Ideal pattern:

- one domain
- one `path-to-direct` question
- one `direct-to-path` question
- one sentence on why the two are different

That will make the contrast legible to economists without extra graph jargon.

## 7. What not to do while runs are active

Do not:

- rewrite the whole introduction yet
- rebuild the main figure sequence yet
- run the path-length exercise yet
- expand human-usefulness packs yet

Those all depend on what the family comparison actually shows.

## 8. Best next paper-facing move after results land

Once the current runs finish, the next writing task should be:

- rewrite the introduction and object-definition section around the two families
- using a `direct-to-path` example first
- while keeping one or two strong `path-to-direct` examples in reserve

That is the cleanest way to make the paper more economist-facing without deciding too
early which family deserves rhetorical priority.
