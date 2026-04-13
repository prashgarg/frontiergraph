# Ontology Targets From Shortlist Review

## Purpose

This note records the **narrow ontology targets** suggested by the cleaned current-shortlist review.

The goal is not a full redesign yet. The goal is to identify the smallest set of ontology fixes that are now clearly justified by repeated failure patterns.

## What the shortlist review suggests

The cleaned shortlist no longer looks dominated by method artifacts or unreadable endpoint junk.

That means the ontology signals we still see are more trustworthy.

At this stage, the review suggests:
- some problems are still only shortlist/routing problems
- some are clearly label-resolution problems
- a smaller number are now clear ontology targets

## What is not yet a first ontology target

These are important, but should not be treated as the first ontology redesign task:

### 1. Repeated `state of the business cycle` variants
Examples:
- `state of the business cycle -> willingness to pay`
- `state of the business cycle -> carbon emissions`
- `state of the business cycle -> green innovation`

This looks more like:
- a repeated-family concentration issue
- possibly a ranking/presentation issue

than a clean ontology failure.

### 2. Repeated `green innovation` families
Examples:
- `financial development -> green innovation`
- `technological innovation -> green innovation`
- `natural resources -> green innovation`
- `renewable energy consumption -> green innovation`

This is partly semantic crowding and partly a real target family.

It does not yet prove that the ontology itself is wrong.

### 3. Weak explanation text with unresolved mediators
This is real, but often still looks like:
- mediator label resolution
- missing display aliases

rather than ontology structure itself.

## First ontology targets

### Target 1. Emissions family cleanup

Examples:
- `CO2 emissions`
- `carbon emissions`
- `carbon emissions (CO2 emissions)`
- `environmental quality (CO2 emissions)`
- `ecological footprint`

Why this looks like a real ontology problem:
- the shortlist produces awkward pairs such as:
  - `CO2 emissions -> carbon emissions`
  - `carbon emissions -> environmental quality`
- the family currently mixes:
  - very close synonyms
  - parenthetical aliases
  - possibly broader environmental-outcome objects

Likely fix:
- create a cleaner canonical family around emissions-related concepts
- distinguish:
  - canonical emissions outcome
  - broader environmental-quality outcome
  - related but distinct footprint-style outcomes
- add alias rules so obvious near-synonyms do not survive as separate surfaced objects

Priority:
- **high**

### Target 2. Willingness-to-pay family cleanup

Examples:
- `willingness to pay`
- `willingness to pay (WTP)`

Why this looks like a real ontology problem:
- these are clearly the same concept family in surfaced output
- they still appear as separate semantic objects in the shortlist

Likely fix:
- canonicalize to one display label
- keep the other as an alias only

Priority:
- **high**

### Target 3. Environmental-quality label family

Examples:
- `environmental quality (CO2 emissions)`
- possibly related overlaps with:
  - `carbon emissions`
  - `CO2 emissions`
  - `environmental pollution`

Why this looks ontology-adjacent:
- the label suggests a parenthetical alias, but the semantic object may actually be different
- this creates ambiguity in surfaced questions

Likely fix:
- inspect whether this node is:
  - a mislabeled alias
  - a broader environmental-quality construct
  - a merged concept that should be split

Priority:
- **medium to high**

### Target 4. Recurrent unresolved mediator labels

This is not a single concept family, but it is now a clear narrow target.

Why it matters:
- several otherwise plausible questions still have explanation layers that fall back to generic wording because the top mediators are unresolved

Likely fix:
- not a full ontology redesign
- targeted label-resolution patch for recurrent mediator codes that appear in important current families

Priority:
- **medium**

## Likely first redesign shape

The evidence now points toward a **minimal patch first**, not a full ontology overhaul.

Best current sequence:

1. canonicalize the obvious synonym/alias families
2. inspect and split the emissions/environmental-quality family where needed
3. patch recurrent mediator display labels
4. rerun the shortlist cleanup method

Only after that should we ask whether a fuller layered ontology is necessary.

## Decision rule

If these narrow fixes materially reduce:
- ontology-problem tags
- awkward near-duplicate surfaced objects
- unresolved important mediator explanations

then we should keep the ontology redesign narrow.

If they do **not** materially reduce those failures, that is the point where a layered redesign becomes more justified.

## Bottom line

The shortlist review now gives us a clean ontology starting point.

The first ontology work should target:
1. emissions-family normalization/splitting
2. willingness-to-pay label consolidation
3. environmental-quality family inspection
4. recurrent mediator-label resolution

That is a much more defensible place to start than redesigning the whole ontology at once.

## Update after patch v1 and mediator-label propagation

Two things changed after the first narrow patch pass:

1. the emissions and willingness-to-pay cleanup was worth doing
2. many apparent mediator-label ontology failures were actually a representation problem in the frontier output, not a true ontology problem

The most current next-target note is now:
- [targeted_ontology_patch_v2_scope.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/targeted_ontology_patch_v2_scope.md)

And the broader ontology-design note is now:
- [ontology_redesign_broader_architecture.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/ontology_redesign_broader_architecture.md)
