# Public label cleanup

This note records the minimum cleanup standard for surfaced labels that appear
in the paper or appendix.

## Already implemented

- sentence-end punctuation is stripped in
  [scripts/build_current_reranked_frontier.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/build_current_reranked_frontier.py)
- paired examples are now being curated with the same punctuation cleanup

## Remaining common problems

These still appear in the raw frontier outputs:

- organization-like nodes that should not be public-facing concepts
  - `Telecommunication Infrastructure Company`
  - `consolidated city-county`
- policy-program names that may need relabeling before paper use
  - `Made in China 2025`
  - `Exchange Information Disclosure Act`
- awkward ontology phrases that are mechanically valid but paper-ugly
  - `accountability software`
  - `digitization economics`
  - `supported employment`

## Rule for paper use

Do not take examples straight from the raw frontier output if:

- a node reads like an organization, law title, firm name, or extraction stub
- the pair is legible only because one endpoint is extremely broad
- the resulting question sounds like ontology debris rather than an economics
  question

## Safe next step

If the paired examples section becomes main-text material, the right procedure
is:

1. generate the raw current-frontier package
2. apply the punctuation cleanup
3. manually curate 5--10 examples per family
4. if a label is still useful but ugly, relabel it only at the presentation
   layer rather than changing the underlying ontology
