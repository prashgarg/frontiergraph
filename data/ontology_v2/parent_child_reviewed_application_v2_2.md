# Parent-Child Reviewed Application v2.2

- ontology rows: `154,522`
- selected reviewed parent edges: `13,037` rows over `13,037` child concepts
- confirmed current reviewed parents: `1,586`
- replaced current parents with a reviewed better parent: `1,817`
- new parent assignments for previously flat concepts: `9,634`
- ambiguous high-confidence valid candidates held out: `4`
- duplicate cleanup candidates: `572`
- too-broad parent candidates: `727`
- high-confidence invalid current-parent cleanup rows: `2,432`

## Effective Parent Source
- `no_parent`: `135,706`
- `accepted_unique`: `12,074`
- `legacy_parent`: `3,495`
- `cleared_reviewed_invalid_parent`: `2,274`
- `accepted_best`: `963`
- `cleared_cycle`: `10`

## Selected Edge Channels
- `lexical_ngram_parent`: `8,732`
- `existing_parent_label`: `2,594`
- `jel_code_hierarchy`: `566`
- `openalex_topic_field`: `475`
- `openalex_topic_subfield`: `382`
- `semantic_broader_neighbor`: `288`

## Sample Selected Edges

| child_label                                    | candidate_parent_label     | candidate_channel     | review_tier             | selection_status   | reason                                                                                       |
|:-----------------------------------------------|:---------------------------|:----------------------|:------------------------|:-------------------|:---------------------------------------------------------------------------------------------|
| absolute performance                           | Performance                | lexical_ngram_parent  | inferred_lexical        | accepted_unique    | Performance is the broader concept for absolute performance.                                 |
| anticipated and unanticipated inflation/shocks | Inflation                  | existing_parent_label | existing_parent_cleanup | accepted_unique    | Anticipated and unanticipated inflation shocks are a specific form of inflation.             |
| Asset Demand                                   | Resource Demand            | existing_parent_label | existing_parent_cleanup | accepted_unique    | Asset demand is a specific kind of resource demand.                                          |
| Asset price bubbles                            | Asset price inflation      | existing_parent_label | existing_parent_cleanup | accepted_unique    | Asset price bubbles are a subtype of asset price inflation.                                  |
| available data                                 | Data                       | lexical_ngram_parent  | inferred_lexical        | accepted_unique    | Available data is a specific kind of data.                                                   |
| Bank competition                               | Competition                | lexical_ngram_parent  | inferred_lexical        | accepted_unique    | Bank competition is a specific application of competition in banking.                        |
| bank efficiency                                | Efficiency                 | lexical_ngram_parent  | inferred_lexical        | accepted_best      | Bank efficiency is a specific form of efficiency.                                            |
| Bank profitability                             | Profitability              | lexical_ngram_parent  | inferred_lexical        | accepted_best      | Bank profitability is a specific case of profitability.                                      |
| Banking Uncertainty                            | Banking                    | lexical_ngram_parent  | inferred_lexical        | accepted_unique    | Banking is the broader field that directly encompasses banking uncertainty.                  |
| bankruptcy exemptions                          | Bankruptcy                 | lexical_ngram_parent  | inferred_lexical        | accepted_best      | Bankruptcy exemptions are a specific concept within bankruptcy law.                          |
| Biomass energy                                 | Energy                     | lexical_ngram_parent  | inferred_lexical        | accepted_best      | Biomass energy is a subtype of energy.                                                       |
| Borrower performance                           | Performance                | lexical_ngram_parent  | inferred_lexical        | accepted_unique    | Borrower performance is a specific kind of performance measure.                              |
| borrower risk                                  | Risk                       | lexical_ngram_parent  | inferred_lexical        | accepted_unique    | Borrower risk is a specific kind of risk.                                                    |
| British stock market                           | Stock Market               | lexical_ngram_parent  | inferred_lexical        | accepted_unique    | British stock market is a specific stock market.                                             |
| capacity investment                            | Investment                 | lexical_ngram_parent  | inferred_lexical        | accepted_unique    | Capacity investment is a specific form of investment.                                        |
| carry trade profitability                      | Cost of carry              | existing_parent_label | existing_parent_cleanup | accepted_unique    | Carry trade profitability is directly tied to cost of carry.                                 |
| catastrophic health expenditure                | Health Expenditure         | lexical_ngram_parent  | inferred_lexical        | accepted_best      | Catastrophic health expenditure is a specific form of health expenditure.                    |
| caution in use of accra indexes                | ACCRA Cost of Living Index | existing_parent_label | existing_parent_cleanup | accepted_unique    | ACCRA Cost of Living Index is the broader index concept for caution in use of accra indexes. |
| Certainty theory                               | Certainty                  | existing_parent_label | existing_parent_cleanup | accepted_unique    | Certainty is the correct broader concept for certainty theory in economics.                  |
| changes in input prices                        | Import Price               | existing_parent_label | existing_parent_cleanup | accepted_unique    | Import Price is a good broader label for changes in input prices.                            |
