# V2 Ontology Second-Pass Review Note

This note summarizes the second-pass row review over the remaining heuristic overlay rows and the first within-paper distortion diagnostic.

## Definitions

- `candidate`: labels with FAISS rank-1 cosine in `[0.65, 0.75)`
- `rescue`: labels with FAISS rank-1 cosine in `[0.50, 0.65)`
- `unresolved`: labels with FAISS rank-1 cosine `< 0.50`

`High-impact low-confidence` refers to labels below the main `0.75` soft threshold that entered the rescue audit because they were frequent, appeared in many papers, were edge-rich, or were especially ambiguous. The audit builder uses:

- `impact_score = 0.40 * pct_rank(freq) + 0.35 * pct_rank(unique_papers) + 0.20 * pct_rank(unique_edge_instances) + 0.05 * pct_rank(directed_edge_instances)`
- inclusion if `rank1_score < 0.75` and any of:
  - `impact_score >= 0.90`
  - `freq >= 50`
  - `unique_papers >= 20`
  - candidate-band ambiguity (`rank_gap <= 0.02` and `impact_score >= 0.80`)

That audit universe contains `40,089` rows.

## Second-pass row review

We ran a full row-level GPT-5.4-mini (`reasoning=low`) review over the remaining heuristic share of the `40,089` audit universe:

- remaining heuristic review rows: `27,983`
- three full runs completed
- total actual model cost across the three runs was about `$46.86`

Per-run decision mix was stable:

- `accept_existing_broad`: about `15.7k` to `15.8k`
- `promote_new_concept_family`: about `9.4k` to `9.6k`
- `accept_existing_alias`: about `1.4k`
- `keep_unresolved`: about `0.9k`
- `reject_match_keep_raw`: about `0.3k`

Majority-vote result over the `27,983` rows:

- unanimous: `19,798`
- two-to-one majority: `7,447`
- no majority: `738`

Majority decision counts:

- `accept_existing_broad`: `16,181`
- `promote_new_concept_family`: `9,057`
- `accept_existing_alias`: `1,173`
- `keep_unresolved`: `622`
- `reject_match_keep_raw`: `192`
- `unclear`: `20`
- no majority: `738`

Agreement with the pre-existing heuristic row decision:

- agreement: `23,026`
- disagreement: `4,957`

The biggest transition was:

- `accept_existing_broad -> promote_new_concept_family`: `2,185`

This confirms that the heuristic layer was too eager to broad-attach a meaningful minority of rows.

## Round-2 reviewed overlay

We then folded the three-run majority decisions back into the reviewed overlay.

Final decision source counts in `ontology_enrichment_overlay_v2_reviewed_round2.parquet`:

- `remaining_row_majority_review`: `27,245`
- `row_review`: `9,566`
- `cluster_review`: `2,537`
- `heuristic`: `738`
- `unresolved_row_review`: `3`

So the heuristic residue shrank from `27,983` rows to `738`.

Final round-2 overlay action counts:

- `attach_existing_broad`: `22,087`
- `propose_new_concept_family`: `13,751`
- `add_alias_to_existing`: `2,474`
- `keep_unresolved`: `942`
- `reject_cluster`: `835`

Compared with the earlier reviewed overlay, round 2:

- reduced broad attachments
- reduced alias additions
- increased new-family promotions
- increased explicit rejects slightly

This is the direction we wanted.

## Round-2 sensitivity snapshot

Using the round-2 reviewed overlay:

- threshold `0.75`: overlay labels `340,853`, overlay occurrences `657,538`, unique grounded concepts `24,862`
- threshold `0.65`: overlay labels `842,368`, overlay occurrences `1,192,675`, unique grounded concepts `40,099`
- threshold `0.50`: overlay labels `1,379,967`, overlay occurrences `1,752,809`, unique grounded concepts `57,640`

The raw extraction graph is still fixed across thresholds. Only the interpretation layer changes.

## Within-paper distortion diagnostic

We also ran a within-paper distortion check over `242,595` papers to test whether global grounding collapses distinct local nodes/edges too aggressively.

Headline results:

- direct `>=0.75` only:
  - node collision rate: `0.016`
  - edge collision rate: `0.009`
  - self-loop rate: `0.014`
  - path-collapse rate: `0.036`

- round-2 reviewed overlay, existing-concept attachments only:
  - node collision rate: `0.019`
  - edge collision rate: `0.012`
  - self-loop rate: `0.012`
  - path-collapse rate: `0.035`

- round-2 reviewed overlay plus synthetic family nodes:
  - node collision rate: `0.017`
  - edge collision rate: `0.011`
  - self-loop rate: `0.011`
  - path-collapse rate: `0.031`

Interpretation:

- global grounding does distort within-paper structure, but not catastrophically
- adding synthetic family nodes for promoted new concept families reduces distortion relative to an existing-concept-only overlay
- the main residual distortion risk is not just thresholding; it is over-broad attachment

## Main takeaways

1. The second-pass GPT review was worth doing. It substantially reduced heuristic dependence.
2. A meaningful block of labels that had been broad-attached should instead be treated as new concept families.
3. The remaining heuristic residue is now small (`738` rows) and can be handled as a targeted hard-case set later.
4. Synthetic family nodes appear to protect within-paper structure better than forcing everything into existing ontology concepts.
