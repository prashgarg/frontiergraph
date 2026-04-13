# Exploratory testbeds: maturity plan

Date: 12 April 2026

This note turns the two exploratory appendix testbeds into concrete work programs:

1. bundle uptake
2. adopter profiles

The goal is not to decide now whether these belong in the main paper, the appendix, or a separate follow-on paper. The goal is to make the next steps operational, auditable, and staged so that each new table or figure answers a clear question.

## 1. Core principle

The main paper's historical object is an edge. These testbeds move one level up:

- `bundle uptake` changes the downstream unit from edge to later paper
- `adopter profiles` changes the downstream unit from edge to later paper and later author/team/venue

That means both testbeds require the same upstream object first:

- a paper-level uptake table that links each historically predictable edge to the later paper that realizes it

Without that table, neither extension is mature.

## 2. What is already available

The repo already supports a useful first version of both testbeds.

Available now:

- historical prediction panels with edge-level realization timing
- paper-level corpus rows with `paper_id`, `year`, `title`, `authors`, `venue`
- paper metadata with `primary_subfield_display_name`
- funder metadata:
  - `unique_funder_count`
  - `first_funder`
  - `funder_display_names`
  - `funder_ids`
- full corpus edge rows with `paper_id`, which should allow construction of realizing-paper mappings

Not yet available in ready-to-use form:

- author affiliations / institutions
- author seniority or career age
- country of author affiliation
- team structure beyond parsing the `authors` string
- journal prestige buckets in a clean curated mapping
- paper type labels such as theory / structural / reduced-form / measurement

So the plan should start with what can be done now, then decide whether the later metadata linkage is worth the cost.

## 3. Shared prerequisite: the uptake spine

Both testbeds need the same upstream table.

### Object

One row per:

- historically predicted edge
- horizon
- cutoff year
- realizing paper

with enough information to identify:

- the predicted edge
- the prediction family (`path_to_direct` or `direct_to_path`)
- the first realization year
- whether the row corresponds to the first realizing paper or one of several realizers

### Minimum columns

- `candidate_id`
- `u`, `v`, `source_id`, `target_id`
- `candidate_family_mode`
- `cutoff_year_t`
- `horizon`
- `first_realized_year`
- `realizing_paper_id`
- `realizing_paper_year`
- `realizing_paper_title`
- `realizing_paper_authors`
- `realizing_paper_venue`
- `realizing_primary_subfield_display_name`
- `realizing_unique_funder_count`

### Key design choices

- Use the first realizing paper as the default adoption event.
- Preserve all realizing papers in a wider table so later robustness checks are possible.
- Keep family labels attached at the prediction level.
- Add a clean flag for whether the realization is the first observed realization for that edge.

### Immediate deliverable

A new reusable parquet/csv pair, for example:

- `outputs/paper/<run>/historical_edge_uptake_spine.parquet`
- `outputs/paper/<run>/historical_edge_uptake_spine.csv`

This is the main blocker. Once this exists, the rest becomes straightforward.

## 4. Testbed A: bundle uptake

### Question

When a later paper realizes one historically predictable edge, how often does that same paper also realize other historically predictable edges?

### Why it matters

The current paper treats one predicted edge as the downstream unit. But later papers may be realizing paper-sized bundles:

- one direct closure plus one mechanism
- several connected mechanisms
- several adjacent direct closures
- mixed bundles across both families

If bundle uptake is common, then:

- wider reading budgets become easier to justify
- the relevant downstream object is not just one edge
- the graph may be better understood as surfacing agenda slices rather than isolated claims

### Stage A1. Build the paper-level bundle table

From the uptake spine, collapse to one row per later paper with:

- count of predicted edges realized
- count realized by family
- number of unique source nodes
- number of unique target nodes
- number of unique focal mediators, where defined

Immediate outputs:

- distribution of realized predicted-edge counts per paper
- share of realizing papers with more than one predicted edge
- family mix within realizing papers

### Stage A2. Add graph-locality measures

For each later paper that realizes more than one predicted edge, compute:

- overlap in endpoints
- overlap in source node
- overlap in target node
- overlap in mediator, where defined
- graph distance between realized predicted edges in the historical graph at the cutoff

The first useful summary is not a complicated model. It is:

- are multi-edge papers mostly local bundles or scattered grabs?

### Stage A3. Classify bundle types

Build simple bundle classes:

- `single-edge`
- `direct-only`
- `path-only`
- `mixed-family`
- `shared-endpoint`
- `shared-mediator`
- `dispersed`

This will make the descriptive results readable.

### Stage A4. First figures/tables

High-value first exhibits:

1. Histogram:
   - number of predicted edges realized per later paper
2. Stacked bar:
   - family composition of realizing papers (`path_to_direct`, `direct_to_path`, mixed)
3. Table:
   - share of papers that are single-edge vs multi-edge, by family and horizon
4. Locality figure:
   - graph-distance distribution among realized predicted edges within the same paper

### Stage A5. Maturity threshold

This testbed is mature enough for paper inclusion once it can answer:

- are later papers mostly single-edge or multi-edge adopters?
- when multi-edge, are the adopted ideas locally connected?
- do mixed-family bundles matter in practice?

If the answer is clearly yes, this becomes a real section candidate.
If the answer is weak or noisy, it should likely stay a future-paper note.

## 5. Testbed B: adopter profiles

### Question

What kinds of papers, teams, venues, and subfields independently move toward graph-supported questions?

### Why it matters

This changes the interpretation of the tool.

The question is not:

- who used Frontier Graph?

The question is:

- which kinds of scientific actors already behave as if they are reading local graph structure well?

That speaks to:

- burden-of-knowledge arguments
- science-of-science work on novelty and incentives
- how different institutional settings absorb underworked ideas

### Stage B1. Start with metadata already available

The first adopter-profile table should use only variables already in the repo:

- `venue`
- `primary_subfield_display_name`
- parsed author count from `authors`
- funder presence / count
- year

Derived variables that can be built immediately:

- `team_size`
- `solo_vs_team`
- `has_any_funder`
- `funder_count_bucket`
- `core_subfield`
- simple venue buckets from a curated mapping:
  - general-interest
  - field
  - adjacent / interdisciplinary
  - working-paper / other

### Stage B2. Build paper-type proxies carefully

Do not start with a full classifier. Start with modest proxies:

- title/abstract keyword flags for theory / model / experiment / survey / measurement
- venue-based hints
- data-use or method tags if available in the extraction layer

These should be described as proxies, not definitive labels.

### Stage B3. First descriptive tables

High-value first outputs:

1. Uptake shares by family and venue bucket
2. Uptake shares by family and subfield
3. Uptake shares by family and team size bucket
4. Uptake shares by family and funder presence
5. Comparison of single-edge vs multi-edge adopting papers on the same dimensions

These are modest but already informative.

### Stage B4. Later metadata expansion

Only after the basic version works should we decide whether to link richer metadata:

- author-level OpenAlex authorships
- affiliation institutions
- institution country
- author career age / seniority
- repeated-author local-incumbent vs entrant measures

This is where the testbed becomes much heavier. It should only be done if the first descriptive version already looks informative.

### Stage B5. Maturity threshold

This testbed is mature enough for broader use once it can answer:

- are `path_to_direct` and `direct_to_path` adopted by different kinds of papers?
- are mixed-family or bundle adopters different from single-edge adopters?
- do uptake patterns vary meaningfully by venue, team size, or subfield?

If the answer is yes with current metadata, this is already a publishable appendix or side-paper base.

## 6. Recommended execution order

The fastest path to maturity is:

1. build the shared uptake spine
2. run bundle-uptake descriptives
3. run adopter-profile descriptives with currently available metadata
4. decide whether richer metadata linkage is worth doing

This order matters because:

- bundle uptake only needs the uptake spine
- adopter profiles need the uptake spine plus paper metadata
- richer author/institution linkage should not happen until the low-cost version already looks promising

## 7. Concrete deliverables

### Week 1 deliverables

- `historical_edge_uptake_spine`
- `bundle_uptake_paper_level`
- first descriptive note with:
  - counts
  - histograms
  - family mix
  - multi-edge shares

### Week 2 deliverables

- `adopter_profile_paper_level`
- venue/subfield/team/funder descriptives
- one compact exploratory memo:
  - what is already clearly interesting
  - what is probably noise
  - what additional metadata would change the picture materially

## 8. What can be done now vs later

### Can be done now

- edge-to-paper uptake spine
- bundle size distributions
- family composition of bundles
- venue/subfield/team/funder descriptives
- single-edge vs multi-edge adopter comparisons

### Requires new linkage or heavier engineering

- author seniority
- institution prestige
- affiliation country
- incumbent vs entrant author classification
- richer causal claims about adoption behavior

## 9. Decision rule for promotion

Promote one of these testbeds into the paper only if it yields one clear substantive claim in plain language.

Examples:

- “Later papers often realize bundles rather than isolated edges.”
- “Mechanism-thickening uptake is more common in broader teams and adjacent-field outlets.”
- “Mixed-family bundles are common enough that wider shortlists have paper-level value.”

If we do not get a claim of that form, these should stay appendix-only or move to a separate paper.

## 10. Immediate next actions

1. Build the historical edge-to-paper uptake spine.
2. Start with bundle uptake, not adopter profiles.
3. Use current metadata for the first adopter-profile cut.
4. Only then decide whether to invest in richer author/institution linkage.

This is the right way to keep the testbeds empirical and disciplined rather than letting them expand into an unbounded wishlist.
