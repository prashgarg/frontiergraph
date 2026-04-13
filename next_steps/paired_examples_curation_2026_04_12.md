# Paired examples curation

This note records which surfaced examples look usable for the paper and which
ones still look like ontology noise.

## Path-to-direct

The current `path-to-direct` frontier already contains several pairs that can be
made legible to economists with minor curation.

Best current candidates:

- `Trade liberalization -> R&D`
- `Digital economy -> Environmental regulation`
- `Green innovation -> R&D`
- `Renewable energy -> Urbanization`

Potentially usable with care:

- `Green innovation -> Technological innovation`
- `GDP -> R&D`
- `Financial sector development -> Total factor productivity`

Weak or too awkward right now:

- `Per capita income -> Willingness to pay`
- `Natural resource -> Willingness to pay`
- `Willingness to pay -> Renewable energy`
- any pair where the mediator is itself a vague public-good or valuation object

The main issue is not only label cleanliness. Some of these are too close to a
survey or valuation literature language rather than a concrete economics
question.

## Direct-to-path

The current `direct-to-path` frontier is still much noisier in public-facing
labels. Many top items are clearly driven by concept-extraction or ontology
artifacts rather than a paper-ready economic question.

Potentially usable:

- `Digital financial inclusion -> Supported employment`
- `Tax refund -> Total factor productivity`
- `Air cargo -> Manufacturing`
- `Green credit policy -> Green production`
- `Green credit policy -> Innovation incentives`

Possibly usable with stronger relabeling:

- `Fiscal capacity -> Sulfur dioxide`
- `Technology measurement -> Emission intensity`
- `Network architecture -> Energy efficiency`

Currently too noisy for the paper:

- `accountability software -> Green innovation`
- `Telecommunication Infrastructure Company -> Green innovation`
- `consolidated city-county -> Housing prices`
- `digitization economics -> Emission intensity`
- `Made in China 2025 -> Total factor productivity`

The direct-to-path family is substantively promising, but the public-facing
examples should not be taken mechanically from the raw top ranks yet.

## Recommendation

For the next paper pass:

1. do not promote raw direct-to-path examples into the main text yet
2. use path-to-direct examples first where the economic question is already
   legible
3. once the paired-family structure is stable, run a small public-label cleanup
   pass on the direct-to-path frontier and then curate examples manually
