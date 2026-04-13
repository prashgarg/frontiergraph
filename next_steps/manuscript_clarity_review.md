# Manuscript Clarity Review

Reviewed against the economics-paper-clarity skill and compared with top papers in this space (Impact4Cast, Sourati & Evans, Park et al., Ludwig & Mullainathan).

---

## MAJOR IMPROVEMENTS (would meaningfully change how a referee reads the paper)

### 1. The abstract is too long and too detailed

Three dense paragraphs. The second paragraph reports metric names (precision@100, recall@100, MRR) and specific results (h=5, h=10) that an abstract reader cannot contextualize yet. Compare with Park et al. (Nature 2023) — their abstract is 150 words and leads with one clean sentence of the finding. Sourati & Evans — ~200 words, two paragraphs.

**Fix:** Cut to two paragraphs, ~200 words. Lead with question and setting. Give the main comparison result in one plain sentence ("the learned reranker beats popularity-based baselines on the main screening metrics at every horizon tested"). Drop metric names, h-values, and the diversification/overlay sentences from the abstract entirely.

### 2. The introduction repeats itself

Lines 93–95 (the "These findings connect..." paragraph) and the closing paragraph (lines 95, "One way to read the paper...") both restate what the paper does. The introduction also front-loads too many footnotes — three substantial footnotes in the first two paragraphs (Fort, Agrawal, Ludwig/Mullainathan) that break the reading flow. These are excellent citations but should be inline or in the lit review, not footnoted in the opening.

**Fix:** Merge the last two paragraphs of the intro into one. Move the Fort and Agrawal footnotes into the Related Literature section where they fit more naturally. Keep the Kleinberg/Ludwig footnote but trim it.

### 3. Section 5.1 is doing too much work

The "Popularity at the strict shortlist" subsection (5.1) currently contains:
- The transparent score vs PA result
- The co-occurrence baseline result
- The reranker result with full numbers
- The feature-set decomposition with three variants and percentages
- The single-feature ablation reference
- The "two layers" interpretation

This is the densest paragraph in the paper (~20 lines, line 582). A referee reading this will lose the thread. The reranker result and the feature decomposition should be in their own subsection.

**Fix:** Split Section 5.1 into two subsections:
- 5.1 "Popularity and co-occurrence at the strict shortlist" — transparent score, PA, co-occurrence
- 5.2 "The learned reranker rescues the benchmark" — reranker numbers, feature decomposition, directed-vs-cooc result

This also creates a cleaner narrative arc: the graph loses → but wait, the reranker wins → and directed features alone are what matters.

### 4. The Discussion is too long

The Discussion (Section 6) is currently ~3 pages with two long paragraphs of limitations, two paragraphs of broader concerns, a "next steps" paragraph, and a closing paragraph. The limitations paragraph (line 594) is a single paragraph of ~15 lines with 3 footnotes — extremely dense. Compare with top economics papers — discussion sections are typically 1–1.5 pages maximum.

**Fix:** Trim. Move the extraction-noise, concept-sensitivity, and temporal-generalization details to a dedicated "Robustness and limitations" appendix subsection. Keep only the 3–4 highest-level points in the Discussion proper. The policy sentence at the end is good — promote it slightly.

### 5. Tables in the appendix lack "reader entry points"

The appendix has 19 tables. Many have good notes but the surrounding text doesn't always tell the reader what to look at first. Compare with Impact4Cast — their tables always have a bold "key result" sentence in the caption. Sourati & Evans highlight the main number in bold.

**Fix:** For each appendix table, ensure the caption or the first sentence of surrounding text states the takeaway: "The main result is..." or "The key row is..."

---

## MINOR IMPROVEMENTS (polish that helps but doesn't change the argument)

### 6. Some figure captions are too long

The fignotes on several figures are 4–6 lines of dense text (e.g., the extraction-flow figure note at line 172, the main-benchmark note at line 571). Compare with top economics papers where figure notes are 1–3 lines. The note should tell the reader what to notice, not re-explain the methodology.

**Fix:** Trim figure notes to 2–3 sentences. The first sentence says what the figure shows. The second says what to notice. The third gives one technical caveat if needed.

### 7. "ontology-vNext" and "routed overlays" still appear in the abstract

Line 72: "Routed overlays such as context transfer and evidence-type expansion enter only later. Family-aware comparison and ontology-vNext remain support and interpretation layers." A general economist will not know what "ontology-vNext" means. These terms are internal project vocabulary that leaked into the abstract.

**Fix:** Remove "ontology-vNext" from the abstract entirely. Replace with plain English: "Internal support layers such as semantic typing and family-aware comparison remain behind the main benchmark."

### 8. The "How to read the benchmark" box is good but could be earlier

The tcolorbox at line 558 explains precision@100, recall@100, and MRR in plain language. This is excellent — but it appears after the reader has already seen metric names in the abstract, introduction, and evaluation design section. By the time they reach the box, they've either figured it out or given up.

**Fix:** Move this box to Section 3 (right before or after the prospective evaluation subsection) so the reader has the plain-language translation before seeing any results.

### 9. Some inline numbers have excessive precision

Line 582: "recall@100 of 0.071850" — six decimal places for a recall metric in a screening exercise. Similarly "0.053224" for PA. The reader cannot distinguish 0.071850 from 0.072. Compare with top papers — two or three significant digits.

**Fix:** Round to three decimal places throughout: 0.072, 0.053, 0.048, etc. Keep full precision in appendix tables only.

### 10. The path-development section could be shorter in the main text

Section 5.5 takes ~2 pages on aggregate transition patterns, journal splits, and subfield splits. The path-development result is interesting but it's a secondary finding, not the main benchmark result. The journal and subfield splits (lines 685–697) could move to the appendix.

**Fix:** Keep the aggregate finding and one paragraph of interpretation in the main text. Move the journal-tier and subfield-split details to the appendix.

### 11. Two paragraphs in "Where structure helps more" are redundant

Lines 660–662 (the topic split paragraph) and lines 662 (a nearly identical sentence) say the same thing twice: "The graph score looks relatively better in several health-care, inequality, banking, housing, and macro-policy clusters." This is a clear editing artifact.

**Fix:** Delete one of the two paragraphs. They say the same thing.

---

## NEW ADDITIONS (would add value beyond improving what exists)

### 12. A "one-page summary" table

Top papers in this space often have a compact summary table that a reader can scan to understand the full result. Something like:

| Layer | What it does | Beats PA? | Key metric |
|-------|-------------|-----------|-----------|
| Transparent score | Inspectable ranking | No | P@100 = 0.090 (h=5) |
| Co-occurrence | Undirected co-mention | No | P@100 = 0.137 (h=5) |
| Learned reranker | 34 graph features, walk-forward | Yes, all horizons | P@100 = 0.222 (h=5) |
| Directed features only | 18 causal features | Yes | P@100 = 0.204 (h=5) |

This would go in the main text after the benchmark results and before the heterogeneity section. It lets a busy reader get the full picture from one table.

### 13. A "what the system actually shows a reader" screenshot or mockup

The paper describes the public system at frontiergraph.com but never shows what a reader would actually see. A screenshot or mockup of one surfaced question — with the graph neighborhood, the path/mechanism rendering, and the overlay — would make the surfaced object tangible. Impact4Cast doesn't do this either, but SciMuse does (personalized suggestions), and it's much more compelling.

**Fix:** Add one figure (main text or appendix) showing a screenshot or rendered example of a surfaced question from the public tool.

### 14. A compact "how we differ from closest comparables" table

The Related Literature now cites Impact4Cast, Sourati & Evans, Tong et al., etc. But the reader has to parse prose to understand the differences. A compact positioning table would help:

| | This paper | Impact4Cast | Sourati & Evans | Tong et al. |
|---|-----------|-------------|-----------------|-------------|
| Domain | Economics | All sciences | Biomedicine | Psychology |
| Edge type | Directed causal | Co-occurrence | Co-occurrence | Causal |
| Main null | Pref. attachment | Various ML | Content-only | TransE |
| Temporal eval | Walk-forward | Holdout | Holdout | None |
| Human validation | Prepared, not collected | No | No | Yes |

This could go in the Related Literature section or the appendix.

### 15. A forward-looking "research agenda" paragraph

The Discussion currently ends with a modest policy sentence. Top metascience papers (Park et al., Sourati & Evans) often end with a more ambitious forward-looking paragraph about what the approach could eventually enable. One paragraph connecting to the broader AI-assisted research ecosystem — how this approach could complement funder decision-making, journal scope-setting, or department hiring — would give the paper more ambition without overclaiming.

---

## COMPARISON WITH TOP PAPERS

### What Park et al. (Nature 2023) does better:
- Crisper abstract (150 words, one main finding)
- One signature figure (CD index decline) that everyone remembers
- Minimal jargon — the "disruption index" is defined once and used throughout
- Very short discussion

### What Impact4Cast (Gu & Krenn 2025) does better:
- Pipeline figure is cleaner and has real data flowing through
- Single-feature ablation presented as a clean bar chart
- The AUC metric is more familiar to ML audiences than precision@100

### What Sourati & Evans (Nature Human Behaviour 2023) does better:
- The "alien vs human-aware" distinction is a memorable conceptual contribution
- They name their key insight ("human-aware AI") in a way that sticks
- Shorter paper overall

### What Ludwig & Mullainathan (QJE 2024) does better:
- The "three-step procedure" (train → communicate → verify) is a clean framework
- They use one running example (mugshots) throughout
- Minimal technical detail in the main text — everything goes to the appendix

### What YOUR paper does better than all of them:
- **Richer graph object** — directed causal claims with typed edges, not just co-occurrence
- **More thorough benchmark** — multiple baselines, feature decomposition, regime splits, temporal generalization
- **The anchor/object separation** — conceptually original
- **Economics-specific heterogeneity** — method-family, journal-tier, and funding splits that are substantively interpretable
- **Public tool** — frontiergraph.com lets readers inspect the output
- **Honest about limitations** — the transparent score losing is reported prominently rather than hidden

### The gap:
Your paper is more thorough but less crisp than the best comparables. The main risk is that a referee drowns in the detail before reaching the punchline. The fixes above are mostly about surfacing the punchline earlier and cutting repetition.
