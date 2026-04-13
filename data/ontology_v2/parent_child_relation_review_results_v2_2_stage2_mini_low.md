# Parent-Child Relation Review Results v2.2

- model: `gpt-5.4-mini (reasoning=low)`
- reviewed items: `19,330`
- batches: `774`
- prompt tokens: `3,320,041`
- completion tokens: `904,362`

## Decisions
- `valid_parent`: `10,434`
- `invalid`: `3,155`
- `context_not_parent`: `2,625`
- `sibling_or_related`: `2,281`
- `plausible_but_too_broad`: `511`
- `alias_or_duplicate`: `324`

## Confidence
- `high`: `16,260`
- `medium`: `2,932`
- `low`: `138`

## Sample rows

| review_tier      | candidate_channel    | child_label                                      | candidate_parent_label                 | decision           | confidence   | reason                                                                                  |
|:-----------------|:---------------------|:-------------------------------------------------|:---------------------------------------|:-------------------|:-------------|:----------------------------------------------------------------------------------------|
| inferred_lexical | lexical_ngram_parent | Keynesian Dynamic Stochastic General Equilibrium | Dynamic Stochastic General Equilibrium | valid_parent       | high         | Keynesian DSGE is a specific variant of dynamic stochastic general equilibrium models.  |
| inferred_lexical | lexical_ngram_parent | Real gross domestic product                      | Gross domestic product                 | valid_parent       | high         | Real GDP is a standard subtype of GDP measured in inflation-adjusted terms.             |
| inferred_lexical | lexical_ngram_parent | Dynamic Computable General Equilibrium.          | Computable General Equilibrium         | valid_parent       | high         | Dynamic CGE is a specific form of computable general equilibrium model.                 |
| inferred_lexical | lexical_ngram_parent | Quasi-Monte Carlo method                         | Monte Carlo method                     | valid_parent       | high         | Quasi-Monte Carlo is a variant of Monte Carlo methods.                                  |
| inferred_lexical | lexical_ngram_parent | Functional principal component analysis          | Principal component analysis           | valid_parent       | high         | Functional PCA is a specific version of principal component analysis.                   |
| inferred_lexical | lexical_ngram_parent | Aggregate Human Capital                          | Human Capital                          | valid_parent       | high         | Aggregate human capital is a broader human-capital concept at the economy-wide level.   |
| inferred_lexical | lexical_ngram_parent | Human Capital Investment                         | Human Capital                          | valid_parent       | high         | Human capital investment is a direct subtype of human capital.                          |
| inferred_lexical | lexical_ngram_parent | Specific Human Capital.                          | Human Capital                          | valid_parent       | medium       | Specific human capital is a narrower category within human capital.                     |
| inferred_lexical | lexical_ngram_parent | Aggregate Energy Consumption                     | Energy Consumption                     | valid_parent       | high         | Aggregate energy consumption is a broader economy-wide form of energy consumption.      |
| inferred_lexical | lexical_ngram_parent | Carbon dioxide equivalent                        | Carbon dioxide                         | sibling_or_related | medium       | Carbon dioxide equivalent is a measurement conversion, not a subtype of carbon dioxide. |
| inferred_lexical | lexical_ngram_parent | Carbon dioxide removal                           | Carbon dioxide                         | sibling_or_related | high         | Carbon dioxide removal is an intervention involving CO2, not a type of carbon dioxide.  |
| inferred_lexical | lexical_ngram_parent | Credit default swap index                        | Credit default swap                    | valid_parent       | high         | A credit default swap index is a specific index built from credit default swaps.        |
