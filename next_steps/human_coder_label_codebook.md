# Human Coder Label Codebook

## Purpose

This file defines a simple qualitative coding scheme for the blinded human-validation prompts in:

- `outputs/paper/44_human_validation_materials/human_validation_blinded_sheet.csv`

The goal is to simulate one economics-trained human coder reading the prompts cold and assigning a small, interpretable set of labels.

This is **not** a substitute for real human ratings.
It is a first-pass qualitative coding layer that can help us:

- inspect what kinds of prompts look strong or weak on sight
- identify recurring theme crowding
- compare later real rater notes against a structured internal prior

## Coding assumptions

- The coder sees only the blinded prompt text.
- The coder does not use the answer key.
- The coder is asked to behave like one economics-trained reader under limited time.
- The coder is evaluating the surfaced question as a screening prompt, not checking whether the relation is true.

## Fields

### `human_coder_attention_label`

Main decision under limited attention.

Allowed values:

- `would_open`: I would click/read this under a tight shortlist budget.
- `maybe_open`: I would keep it in reserve, but it is not an obvious headline item.
- `would_skip`: I would probably skip this if I had many other prompts to inspect.

### `human_coder_topic_cluster`

Dominant substantive area as perceived from prompt text.

Allowed values:

- `climate_energy`
- `climate_macro`
- `macro_core`
- `public_finance`
- `innovation_green`
- `distribution`
- `measurement_meta`

### `human_coder_primary_reason`

Primary reason for the attention decision.

Allowed values:

- `good_screening_candidate`
- `interesting_cross_domain`
- `clear_policy_hook`
- `clear_macro_link`
- `too_generic`
- `close_substitute`
- `mechanism_unclear`
- `measurement_heavy`
- `direction_awkward`

### `human_coder_issue_flags`

Optional semicolon-separated flags for recurring concerns or strengths.

Allowed values:

- `crowded_CO2_theme`
- `repeated_business_cycle_theme`
- `generic_endpoint`
- `measurement_endpoint`
- `close_substitute_pair`
- `direction_reversal_variant`
- `policy_relevant`
- `cross_domain`
- `mechanism_thin`

## How to read the labels

The labels are meant to be compact rather than exhaustive.

Examples:

- `would_open` + `good_screening_candidate`
  means the prompt feels both readable and worth scarce attention.
- `would_skip` + `measurement_heavy`
  means the prompt feels too meta or too measurement-oriented to function well as a headline research question.
- `would_skip` + `close_substitute`
  means the endpoints feel too similar or too near-duplicate to generate a compelling standalone prompt.

## Recommended use

Use these labels as:

1. a blinded internal benchmark for how one economics-trained reader might react
2. a way to summarize qualitative crowding in the pack
3. a companion to the numeric rating exercise, not a replacement for it

Do not use this single-pass coding file as evidence in the paper on its own.
