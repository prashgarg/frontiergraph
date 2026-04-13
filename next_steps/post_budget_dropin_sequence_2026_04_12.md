# Post-budget drop-in sequence

This note records the exact next steps once the direct-to-path budget run
finishes.

## Expected upstream output

- [outputs/paper/151_retrieval_budget_direct_to_path](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/151_retrieval_budget_direct_to_path)

Expected files:

- `retrieval_budget_summary.csv`
- `retrieval_budget_cutoff_eval.csv`
- `retrieval_budget_summary.md`
- `retrieval_score_plateau_cutoff.csv`
- `retrieval_candidate_universe_summary.csv`

## Immediate next command

Run the paired builder:

- [scripts/build_dual_family_budget_pairing.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/build_dual_family_budget_pairing.py)

Recommended output directory:

- `outputs/paper/156_dual_family_budget_pairing`

## What to inspect first

1. does direct-to-path remain positive at broader \(K\) where path-to-direct
   fades?
2. do the two families differ mainly in levels, or in shape over \(K\)?
3. is the paired figure clear enough for appendix as-is?

## Manuscript insertion order

1. inspect the paired budget figure
2. if acceptable, insert it into:
   - [paper/appendix_paired_budget_extensions.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/appendix_paired_budget_extensions.tex)
3. add `\input{appendix_paired_budget_extensions.tex}` immediately after
   [paper/appendix_paired_family_extensions.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/appendix_paired_family_extensions.tex)
   and before
   [paper/appendix_direct_closure_extensions.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/appendix_direct_closure_extensions.tex)
4. recompile and render-check the appendix pages

## Decision rule

If the paired budget figure is informative for both families:

- keep it in the appendix first
- do not promote it to the main text until the whole paired-family story is
  stable

If the paired budget result is weak or one family is too noisy:

- keep the subsection, but compress the interpretation and avoid overclaiming
