# Remaining-Heuristic Hard-Case Final Adjudication

- Input set: `738` former no-majority remaining-heuristic rows
- Resolved by strict modal vote: `700`
- Resolved by manual override: `38`

## Final decision counts
- `promote_new_concept_family`: `515`
- `accept_existing_broad`: `148`
- `accept_existing_alias`: `33`
- `keep_unresolved`: `32`
- `reject_match_keep_raw`: `10`

## Manual adjudications

### `realized volatility (rv)` (`rhr_00262_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Realized volatility`
- Reason: Realized volatility is a standard finance construct. It is closely related to realized variance, but not cleanly reducible to it, so promoting a distinct family preserves the concept.

### `firm-sponsored training` (`rhr_01014_row`)
- Final decision: `accept_existing_broad`
- Canonical target: `Formal Training Programs`
- New concept family: `None`
- Reason: This reads as a subtype of formal training rather than a missing standalone family. Broad grounding preserves the label without over-expanding the ontology.

### `distribution of returns` (`rhr_01309_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Return distribution`
- Reason: This is a recognizable finance/statistics concept. Generic distribution nodes are too broad, so a dedicated family is the cleaner grounding.

### `simulation methods` (`rhr_01773_row`)
- Final decision: `accept_existing_broad`
- Canonical target: `Simulation`
- New concept family: `None`
- Reason: This is a generic methodological phrase. Broad attachment to Simulation captures the method family without creating an unnecessary new ontology node.

### `political tensions` (`rhr_02288_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Political tensions`
- Reason: The phrase denotes a recurring political-economy context that is broader and softer than crisis or conflict. Promoting a family preserves that distinction.

### `poor health` (`rhr_02323_row`)
- Final decision: `accept_existing_broad`
- Canonical target: `State of health`
- New concept family: `None`
- Reason: This is a directional state descriptor rather than a distinct concept family. Broad grounding to State of health is the safest fit.

### `coal resource tax reform` (`rhr_03027_row`)
- Final decision: `accept_existing_broad`
- Canonical target: `Tax reform`
- New concept family: `None`
- Reason: This is a specific reform episode inside a broader tax-reform domain. A safe parent concept exists, so broad grounding is preferable to creating a one-off family.

### `business cycle frequencies` (`rhr_03732_row`)
- Final decision: `accept_existing_broad`
- Canonical target: `Business Cycles`
- New concept family: `None`
- Reason: This is a frequency-domain specialization of business-cycle analysis rather than a separate ontology family. Broad attachment is sufficient.

### `uniform rule` (`rhr_04116_row`)
- Final decision: `keep_unresolved`
- Canonical target: `None`
- New concept family: `None`
- Reason: The phrase is too generic to anchor cleanly. It may be real in context, but there is no safe existing target or stable new-family interpretation.

### `social transfers` (`rhr_04543_row`)
- Final decision: `accept_existing_broad`
- Canonical target: `Income Transfer`
- New concept family: `None`
- Reason: This is close to the transfer domain, but not exact enough for aliasing. Broad grounding to Income Transfer preserves the main economics meaning.

### `temperature overshoot` (`rhr_04802_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Temperature overshoot`
- Reason: Overshoot is a distinct climate concept, not just generic overheating. A separate family better captures its policy and climate-economics use.

### `this paper (current study)` (`rhr_04803_row`)
- Final decision: `reject_match_keep_raw`
- Canonical target: `None`
- New concept family: `None`
- Reason: This is paper-internal meta language rather than a research concept. The raw label should be preserved for traceability, but ontology attachment should be rejected.

### `portfolio separation` (`rhr_04922_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Portfolio separation`
- Reason: This is a real finance concept and is more specific than generic portfolio allocation. Promoting a family preserves that established distinction.

### `house price expectations` (`rhr_04988_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `House price expectations`
- Reason: Expectations about house prices are substantively distinct from house prices themselves. A dedicated family is cleaner than collapsing to the level variable.

### `paper conclusions` (`rhr_04995_row`)
- Final decision: `reject_match_keep_raw`
- Canonical target: `None`
- New concept family: `None`
- Reason: This is paper-meta language rather than a stable concept node. Rejecting ontology attachment is safer than inventing a family.

### `random regret minimisation (rrm)` (`rhr_05059_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Random regret minimisation`
- Reason: This is a named discrete-choice framework, not just generic regret. It merits a distinct family node.

### `decisional conflict` (`rhr_05219_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Decisional conflict`
- Reason: This is a recognizable decision-science construct. Generic decision problem nodes are too broad for it.

### `monday` (`rhr_05373_row`)
- Final decision: `reject_match_keep_raw`
- Canonical target: `None`
- New concept family: `None`
- Reason: On its own this is too fragmentary and context-dependent to serve as an ontology concept. It likely reflects a truncated weekday effect or scheduling mention.

### `earlier work` (`rhr_05648_row`)
- Final decision: `reject_match_keep_raw`
- Canonical target: `None`
- New concept family: `None`
- Reason: This is a backward-looking paper-reference phrase, not a stable research concept. Ontology attachment should be rejected.

### `dominant firm` (`rhr_06510_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Dominant firm`
- Reason: This is a standard industrial-organization concept and is not equivalent to a generic price maker label. It should remain distinct.

### `energy stock market` (`rhr_10265_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Energy stock market`
- Reason: This denotes a meaningful market segment and current ontology neighbors are clearly off-target. A family promotion is safer than forced broad attachment.

### `policy anticipations hypothesis` (`rhr_11195_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Policy anticipations hypothesis`
- Reason: This reads like a named expectations-related proposition rather than a generic expectations-hypothesis alias. A distinct family keeps that specificity.

### `western guangdong` (`rhr_11376_row`)
- Final decision: `keep_unresolved`
- Canonical target: `None`
- New concept family: `None`
- Reason: This is a geographic regional label. It is valid context, but not something we should eagerly promote into the ontology without a cleaner geographic hierarchy.

### `erm membership` (`rhr_12995_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `ERM membership`
- Reason: Exchange-rate mechanism membership is a real institutional status in international macro and finance. It deserves a distinct family rather than a generic membership node.

### `market services` (`rhr_14528_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Market services`
- Reason: This is a standard sectoral classification phrase and is not well captured by generic market nodes. A distinct family is cleaner.

### `household vulnerability to poverty` (`rhr_16865_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Household vulnerability to poverty`
- Reason: This is a recurring development and welfare concept. Current candidates are too weak or acronym-bound to support safe aliasing.

### `simple model presented in paper` (`rhr_19557_row`)
- Final decision: `reject_match_keep_raw`
- Canonical target: `None`
- New concept family: `None`
- Reason: This is paper-internal exposition language, not a reusable concept family. Rejecting ontology attachment is the right treatment.

### `benchmarking allocation method` (`rhr_21145_row`)
- Final decision: `keep_unresolved`
- Canonical target: `None`
- New concept family: `None`
- Reason: This sounds method-like, but the phrase is still too generic and context-bound to justify either a new family or a safe existing target.

### `first-order approach validity` (`rhr_22828_row`)
- Final decision: `keep_unresolved`
- Canonical target: `None`
- New concept family: `None`
- Reason: This is a methodological validity phrase rather than a stable canonical concept. Keeping it unresolved is safer than inventing a family.

### `liberal-market economies` (`rhr_24075_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Liberal market economies`
- Reason: This is a named comparative-political-economy construct from the varieties-of-capitalism literature. It should remain distinct from generic market economy nodes.

### `perspective of the analysis` (`rhr_25209_row`)
- Final decision: `reject_match_keep_raw`
- Canonical target: `None`
- New concept family: `None`
- Reason: This is framing language about how a paper is written, not a stable research concept. Ontology attachment should be rejected.

### `policymakers and researchers` (`rhr_25290_row`)
- Final decision: `reject_match_keep_raw`
- Canonical target: `None`
- New concept family: `None`
- Reason: This is a conjunction of actor groups, usually part of framing or audience language rather than a concept node. Rejecting the attachment is cleaner.

### `professional self-regulation` (`rhr_25580_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Professional self-regulation`
- Reason: This is a recognizable institutional-governance concept and is more specific than generic self-regulatory organization. A dedicated family is justified.

### `rating duration` (`rhr_25742_row`)
- Final decision: `keep_unresolved`
- Canonical target: `None`
- New concept family: `None`
- Reason: The phrase is too ambiguous across finance and ratings contexts to resolve confidently. Leaving it unresolved is the safer option.

### `tgc prices` (`rhr_26793_row`)
- Final decision: `keep_unresolved`
- Canonical target: `None`
- New concept family: `None`
- Reason: This acronym-heavy phrase looks like a real market label, but it is too opaque to ground safely without domain-specific expansion. Keep it unresolved.

### `trade tensions` (`rhr_26909_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Trade tensions`
- Reason: Trade tensions is a standard softer concept than trade war, often used in policy and international-economics work. It should remain distinct.

### `world interest rate (fall)` (`rhr_27317_row`)
- Final decision: `keep_unresolved`
- Canonical target: `None`
- New concept family: `None`
- Reason: This mixes a macro concept with a directional episode marker. Without a cleaner canonical form, unresolved treatment is safer than forced grounding.

### `use of antibiotics` (`rhr_27638_row`)
- Final decision: `promote_new_concept_family`
- Canonical target: `None`
- New concept family: `Antibiotic use`
- Reason: This is an exposure or behavior construct that is meaningfully distinct from antibiotics as an object. A dedicated family preserves that distinction.
