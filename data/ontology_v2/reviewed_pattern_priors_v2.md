# Reviewed Pattern Priors V2

This file learns phrase-pattern priors from row-reviewed ontology decisions rather than imposing deterministic phrase rules by hand.

- reviewed row corpus: `36,814` labels
- included decision sources: `row_review`, `remaining_row_majority_review`, `unresolved_row_review`
- minimum support for a prior row: `20`

## Curated patterns
- `contains_parenthetical`: support `2582`, top decision `accept_existing_broad` (`0.49` share), broad `0.49`, new-family `0.41`, alias `0.09`, reject `0.00`, unresolved `0.01`
- `endswith_returns`: support `456`, top decision `accept_existing_broad` (`0.59` share), broad `0.59`, new-family `0.38`, alias `0.01`, reject `0.01`, unresolved `0.01`
- `endswith_uncertainty`: support `186`, top decision `accept_existing_broad` (`0.82` share), broad `0.82`, new-family `0.18`, alias `0.01`, reject `0.00`, unresolved `0.00`
- `endswith_volatility`: support `167`, top decision `accept_existing_broad` (`0.66` share), broad `0.66`, new-family `0.30`, alias `0.03`, reject `0.01`, unresolved `0.00`
- `endswith_consumption`: support `162`, top decision `accept_existing_broad` (`0.67` share), broad `0.67`, new-family `0.27`, alias `0.06`, reject `0.01`, unresolved `0.01`
- `contains_heterogeneity`: support `121`, top decision `accept_existing_broad` (`0.56` share), broad `0.56`, new-family `0.40`, alias `0.00`, reject `0.00`, unresolved `0.02`
- `endswith_constraints`: support `96`, top decision `promote_new_concept_family` (`0.49` share), broad `0.46`, new-family `0.49`, alias `0.03`, reject `0.00`, unresolved `0.02`
- `endswith_frictions`: support `41`, top decision `promote_new_concept_family` (`0.59` share), broad `0.32`, new-family `0.59`, alias `0.07`, reject `0.00`, unresolved `0.02`
- `endswith_per_capita`: support `32`, top decision `accept_existing_broad` (`0.75` share), broad `0.75`, new-family `0.25`, alias `0.00`, reject `0.00`, unresolved `0.00`

## Strong learned suffix priors
- `suffix_1=spillovers`: support `40`, top decision `accept_existing_broad` (`0.90` share)
- `suffix_2=economic growth`: support `40`, top decision `accept_existing_broad` (`0.90` share)
- `suffix_2=monetary policy`: support `48`, top decision `accept_existing_broad` (`0.88` share)
- `suffix_1=subsidies`: support `55`, top decision `accept_existing_broad` (`0.85` share)
- `suffix_2=human capital`: support `34`, top decision `accept_existing_broad` (`0.85` share)
- `suffix_1=announcements`: support `37`, top decision `accept_existing_broad` (`0.84` share)
- `suffix_1=intervention`: support `30`, top decision `accept_existing_broad` (`0.83` share)
- `suffix_1=futures`: support `30`, top decision `accept_existing_broad` (`0.83` share)
- `suffix_1=companies`: support `30`, top decision `accept_existing_broad` (`0.83` share)
- `suffix_2=growth rate`: support `30`, top decision `accept_existing_broad` (`0.83` share)
- `suffix_1=expenditure`: support `41`, top decision `accept_existing_broad` (`0.83` share)
- `suffix_1=development`: support `125`, top decision `accept_existing_broad` (`0.82` share)
- `suffix_1=energy`: support `34`, top decision `accept_existing_broad` (`0.82` share)
- `suffix_1=utilization`: support `44`, top decision `accept_existing_broad` (`0.82` share)
- `suffix_1=uncertainty`: support `186`, top decision `accept_existing_broad` (`0.82` share)
- `suffix_1=liquidity`: support `31`, top decision `accept_existing_broad` (`0.81` share)
- `suffix_1=taxation`: support `30`, top decision `accept_existing_broad` (`0.80` share)
- `suffix_1=reform`: support `38`, top decision `accept_existing_broad` (`0.79` share)
- `suffix_1=unemployment`: support `60`, top decision `accept_existing_broad` (`0.78` share)
- `suffix_2=financial markets`: support `41`, top decision `accept_existing_broad` (`0.78` share)
- `suffix_2=market returns`: support `49`, top decision `accept_existing_broad` (`0.78` share)
- `suffix_2=of firms`: support `31`, top decision `accept_existing_broad` (`0.77` share)
- `suffix_1=mobility`: support `39`, top decision `accept_existing_broad` (`0.77` share)
- `suffix_1=fluctuations`: support `55`, top decision `accept_existing_broad` (`0.76` share)
- `suffix_1=interventions`: support `38`, top decision `accept_existing_broad` (`0.76` share)

## Interpretation
- These priors should be used as weak, data-driven hints or ranking features, not as hard deterministic mapping rules.
- Patterns with high support and high concentration can guide queue ordering or default proposals.
- Patterns with mixed distributions should remain review-only and should not be promoted into hard-coded rules.
