# Paired-family status

This note records the paper state after the first dual-family parity pass.

## Main paper

The manuscript now treats `path-to-direct` and `direct-to-path` as coequal main
objects in the front end. The main results section starts with the paired-family
benchmark figure and paired benchmark table rather than privileging the
direct-closure stack.

## Completed paired-family outputs

- strict-shortlist benchmark pairing:
  - [outputs/paper/149_dual_family_main_pairing](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/149_dual_family_main_pairing)
- current reranked frontier pairing:
  - [outputs/paper/154_dual_family_extension_pairing](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/154_dual_family_extension_pairing)
- heterogeneity pairing:
  - [outputs/paper/154_dual_family_extension_pairing](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/154_dual_family_extension_pairing)

These paired extension figures already appear in the appendix.

## Completed appendix additions

- paired-family extension appendix:
  - [paper/appendix_paired_family_extensions.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/appendix_paired_family_extensions.tex)
- graph-evolution appendix figure:
  - [outputs/paper/155_graph_evolution_appendix](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/155_graph_evolution_appendix)
  - [paper/appendix_graph_evolution.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/appendix_graph_evolution.tex)

## Remaining family-parity blocker

The missing paired extension object is the direct-to-path retrieval-budget
comparison. The live job is:

- PID `57387`
- output target:
  - [outputs/paper/151_retrieval_budget_direct_to_path](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/outputs/paper/151_retrieval_budget_direct_to_path)

The paired builder is already ready:

- [scripts/build_dual_family_budget_pairing.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/build_dual_family_budget_pairing.py)

## Second design axis

The `max_path_len = 2, 3, 4, 5` axis is prepared but not yet run.

- execution note:
  - [next_steps/path_length_axis_execution_2026_04_12.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/path_length_axis_execution_2026_04_12.md)
- runner:
  - [scripts/run_path_length_axis.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/run_path_length_axis.py)
- summary builder:
  - [scripts/build_path_length_axis_summary.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/build_path_length_axis_summary.py)

The first honest version of that axis should run on `path-to-direct`. The
ranking layer now supports bounded lengths 4 and 5, but the direct-to-path
historical event is still length-2 path emergence.

## Drafted but not yet inserted

The following manuscript-ready appendix shells are written and waiting for the
empirical artifacts:

- [paper/appendix_paired_budget_extensions.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/appendix_paired_budget_extensions.tex)
- [paper/appendix_path_length_axis.tex](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/paper/appendix_path_length_axis.tex)

There is also a curation note for surfaced examples and public-facing labels:

- [next_steps/paired_examples_curation_2026_04_12.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/paired_examples_curation_2026_04_12.md)
- [next_steps/public_label_cleanup_2026_04_12.md](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/next_steps/public_label_cleanup_2026_04_12.md)
