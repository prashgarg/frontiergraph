# v2 Ontology Stocktake

## Status note

This note is now a historical pre-freeze stocktake.

The current paper-facing ontology baseline is the frozen `v2.3` package:

- `data/ontology_v2/ontology_v2_3_candidate.json`
- `data/ontology_v2/extraction_label_mapping_v2_3_candidate.parquet`
- `data/ontology_v2/ontology_v2_3_freeze_note.md`
- `data/ontology_v2/ontology_v2_3_baseline_manifest.json`

That frozen baseline contains `154,359` ontology rows, `602` display-label changes,
`22` allowed roots, `4` ambiguous containers, and `0` accepted new intermediate-parent
promotions in the conservative Pause 1 closeout.

The sections below preserve the earlier stocktake for historical context about the
open-world review and overlay work that led into the freeze.

## Purpose

This note records where ontology v2 and its grounding layer stood after the open-world rescue pass, the repeated GPT-5.4-mini review runs, and the application of the reviewed overlay back into the ontology-grounded layer used by the paper.

The main distinction at that point was:

- the **base ontology** is fixed and provenance-clean
- the **grounding and rescue layer** is open-world, tiered, and reviewed

This means the project no longer relies on a binary matched/unmatched ontology story.

## Pre-freeze base ontology snapshot

Source of truth:

- `data/ontology_v2/ontology_v2_final.json`

Current size:

- `153,800` concepts

Source mix:

- `wikipedia`: `129,156`
- `openalex_keyword`: `9,338`
- `wikidata`: `8,394`
- `jel`: `5,031`
- `openalex_topic`: `1,881`

Interpretation:

- the ontology is broad and recall-oriented
- it is also strongly Wikipedia-heavy
- that broadness helps coverage, but it is also the main source of semantic drift risk in low-confidence matching

## Pre-freeze raw grounding layer

Source of truth:

- `data/ontology_v2/extraction_label_grounding_v2_reviewed.parquet`

Current size:

- `1,389,907` normalized extracted labels

Score-band counts:

- `linked`: `92,249`
- `soft`: `224,043`
- `candidate`: `524,551`
- `rescue`: `539,120`
- `unresolved`: `9,944`

Score-band occurrence counts:

- `linked`: `241,435`
- `soft`: `311,580`
- `candidate`: `628,668`
- `rescue`: `571,094`
- `unresolved`: `10,122`

Interpretation:

- the main mapping challenge is not the tiny `<0.50` tail
- the main challenge is the large `0.50–0.75` middle
- this confirms that a binary thresholded ontology story would be misleading

At the direct `0.75` threshold:

- `316,292` labels attach directly
- `553,015` label occurrences attach directly

These direct counts remain useful, but they are not the final reviewed open-world counts used in the paper.

## Reviewed overlay layer

Sources of truth:

- `data/ontology_v2/ontology_enrichment_overlay_v2_reviewed.parquet`
- `data/ontology_v2/ontology_missing_concept_proposals_v2_reviewed.parquet`
- `data/ontology_v2/reviewed_overlay_application_note.md`

Overlay size:

- `40,089` reviewed overlay rows

Final overlay actions:

- `attach_existing_broad`: `24,888`
- `propose_new_concept_family`: `10,891`
- `add_alias_to_existing`: `2,771`
- `keep_unresolved`: `797`
- `reject_cluster`: `742`

Overlay occurrence counts:

- `attach_existing_broad`: `94,925`
- `propose_new_concept_family`: `35,879`
- `add_alias_to_existing`: `20,530`
- `keep_unresolved`: `6,408`
- `reject_cluster`: `9,059`

Interpretation:

- the reviewed system is less willing to force aliases than the heuristic pass
- it is more willing to surface real missing concept families
- it is also more willing to explicitly reject misleading ontology attachments

Compared with the earlier heuristic overlay:

- `add_alias_to_existing` fell from `4,461` to `2,771`
- `propose_new_concept_family` rose from `9,680` to `10,891`
- `reject_cluster` rose from `127` to `742`

This is the right direction.

## Review layer and adjudication status

Source of truth:

- `data/ontology_v2/main_grounding_review_v2_adjudicated.parquet`
- `data/ontology_v2/main_grounding_review_v2_adjudicated.md`

Reviewed queue size:

- `11,569` items

Composition:

- `9,566` row items
- `2,000` cluster medoids
- `3` unresolved-row items

Final adjudicated decisions:

- `accept_existing_broad`: `5,235`
- `promote_new_concept_family`: `4,345`
- `accept_existing_alias`: `1,101`
- `reject_match_keep_raw`: `686`
- `keep_unresolved`: `188`
- `unclear`: `14`

Resolution sources:

- `three_run_unanimous`: `8,244`
- `three_run_majority`: `2,973`
- `hard_case_modal`: `349`
- `hard_case_modal_weak`: `1`
- `manual_override`: `2`

Interpretation:

- the reviewed subset is now well adjudicated
- the final overlay is no longer just a heuristic rescue layer
- however, only the most important ambiguous subset was directly reviewed; the entire `40,089` overlay universe was not individually adjudicated row by row

## How the reviewed overlay was applied

Application rules:

- row-level reviews override cluster-level reviews
- reviewed cluster-medoid decisions propagate to labels in reviewed clusters when there is no row review
- unresolved raw labels are always preserved
- broad or alias decisions require a resolvable existing ontology target; otherwise they fall back to new-family or unresolved

Decision-source mix in the final reviewed overlay:

- `heuristic`: `27,983`
- `row_review`: `9,566`
- `cluster_review`: `2,537`
- `unresolved_row_review`: `3`

Interpretation:

- the overlay is reviewed where it matters most
- but a large share of the overlay still rests on heuristic logic and reviewed-cluster propagation rather than direct row-level adjudication

## Reviewed sensitivity outputs

Source of truth:

- `outputs/paper/46_ontology_grounding_sensitivity_reviewed/summary.csv`
- `outputs/paper/46_ontology_grounding_sensitivity_reviewed/summary.md`

At threshold `0.75`:

- direct threshold labels: `316,292`
- direct threshold occurrences: `553,015`
- reviewed overlay labels with attachment: `343,951`
- reviewed overlay occurrences with attachment: `668,470`
- unique grounded concepts: `25,495`

At threshold `0.50`:

- reviewed overlay labels with attachment: `1,379,972`
- reviewed overlay occurrences with attachment: `1,752,830`
- unique grounded concepts: `57,640`

Hard rule preserved across sensitivity variants:

- raw-label preservation rate: `1.0`
- raw-edge preservation rate: `1.0`

Interpretation:

- the raw graph is fixed across threshold variants
- only the ontology-grounded interpretation layer changes
- the reviewed overlay materially improves `0.75`-threshold coverage without pretending the low-confidence tail is fully exact

## What is solid now

- the project has moved decisively beyond a binary matched/unmatched ontology view
- broader grounding is now a first-class, explicit outcome
- unresolved and rejected states are explicit
- important low-confidence labels are no longer silently deleted
- the paper appendix now reflects the reviewed open-world grounding system rather than the earlier heuristic queue language

## What remains unfinished

We have **not** yet:

- added the reviewed new concept families into the base ontology itself
- rebuilt the base ontology from reviewed proposals
- re-materialized the downstream graph / ranker stack on top of the reviewed overlay as the default layer
- replaced the fallback clusterer with a stronger semantic clustering backend

This means the current system is:

- strong enough for the paper’s ontology writeup
- strong enough to avoid false novelty from ontology deletion
- not yet a fully consolidated ontology-v2.1 system

## Main remaining risks

### 1. Base ontology weakness in economics-facing areas

The base ontology is still weak in some regions, especially:

- operational phrases common in economics papers
- contexts where the nearest ontology neighborhood is Wikipedia-heavy and semantically strange

Examples discussed in the audit include:

- `financial frictions`
- `search frictions`
- `female sex`
- `unobserved heterogeneity`

### 2. Cluster layer quality

The current cluster layer is good enough for triage but not final truth. It still relies on:

- TF-IDF character fallback clustering
- truncated audit-universe clustering
- simple lexical gates and dominance thresholds

### 3. Overlay versus ontology gap

The project now has many reviewed `propose_new_concept_family` outcomes, but these still live in an overlay/proposal regime rather than in the ontology itself.

## Bottom line

Ontology v2 is now in a much stronger state than before:

- the base ontology exists and is broad
- the mapping is tiered and open-world
- the reviewed overlay protects the graph from false deletion
- the paper can now describe the ontology system honestly

But ontology work is not finished. The next major step is not another binary-threshold tweak. It is a v2.1 pass that:

- promotes the best reviewed missing concept families into the ontology
- improves alias and broader-grounding deterministically where possible
- strengthens the cluster layer
- then re-materializes the downstream graph and benchmark stack on top of that stronger reviewed ontology layer
