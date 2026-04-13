# Context Normalization Working Note

## Design choice

Blocs and groups stay as blocs and groups in the canonical normalized field.

We do not collapse `OECD`, `EU-15`, `BRICS`, or `G7` into constituent countries by default because that would blur evidence provenance.
A relation observed at the bloc level is not the same thing as direct country-level evidence.

If we later want bloc membership reasoning, it should be added as separate metadata rather than replacing the observed context label.

## Table schema

- `raw_value`
- `normalized_display`
- `context_type`
- `granularity`
- `canonical_context_id`
- `status`
- `observed_count`

## Early normalization policy

- normalize obvious aliases: `CHN -> China`, `USA -> United States`, `GBR -> United Kingdom`, `KOR -> South Korea`, etc.
- keep blocs distinct: `OECD countries`, `BRICS countries`, `G7 countries`, `EU-15 countries`, `Euro Area countries`
- treat ambiguous `NA` as `unknown context` for now
- keep study-defined groups as groups rather than forcing them into countries

## Top normalized values

- `China` -> `China` | type `country` | granularity `country` | status `canonical` | count `10609`
- `United States` -> `United States` | type `country` | granularity `country` | status `canonical` | count `3521`
- `CHN` -> `China` | type `country` | granularity `country` | status `normalized_alias` | count `1989`
- `USA` -> `United States` | type `country` | granularity `country` | status `normalized_alias` | count `1858`
- `India` -> `India` | type `country` | granularity `country` | status `canonical` | count `1317`
- `OECD` -> `OECD countries` | type `bloc` | granularity `bloc` | status `canonical_bloc` | count `756`
- `United Kingdom` -> `United Kingdom` | type `country` | granularity `country` | status `canonical` | count `712`
- `Pakistan` -> `Pakistan` | type `country` | granularity `country` | status `canonical` | count `708`
- `Brazil` -> `Brazil` | type `country` | granularity `country` | status `canonical` | count `677`
- `Italy` -> `Italy` | type `country` | granularity `country` | status `canonical` | count `592`
- `Germany` -> `Germany` | type `country` | granularity `country` | status `canonical` | count `512`
- `Japan` -> `Japan` | type `country` | granularity `country` | status `canonical` | count `469`
- `Turkey` -> `Turkey` | type `country` | granularity `country` | status `canonical` | count `448`
- `GBR` -> `United Kingdom` | type `country` | granularity `country` | status `normalized_alias` | count `417`
- `BRICS` -> `BRICS countries` | type `bloc` | granularity `bloc` | status `canonical_bloc` | count `414`
- `South Africa` -> `South Africa` | type `country` | granularity `country` | status `canonical` | count `413`
- `Russia` -> `Russia` | type `country` | granularity `country` | status `canonical` | count `404`
- `Spain` -> `Spain` | type `country_or_place` | granularity `country` | status `fallback_passthrough` | count `379`
- `G7` -> `G7 countries` | type `bloc` | granularity `bloc` | status `canonical_bloc` | count `369`
- `Indonesia` -> `Indonesia` | type `country` | granularity `country` | status `canonical` | count `356`
- `IND` -> `India` | type `country` | granularity `country` | status `normalized_alias` | count `354`
- `Europe` -> `Europe` | type `region` | granularity `region` | status `canonical_region` | count `350`
- `France` -> `France` | type `country` | granularity `country` | status `canonical` | count `329`
- `Canada` -> `Canada` | type `country` | granularity `country` | status `canonical` | count `320`
- `Africa` -> `Africa` | type `region` | granularity `region` | status `canonical_region` | count `312`
- `Australia` -> `Australia` | type `country` | granularity `country` | status `canonical` | count `303`
- `Mexico` -> `Mexico` | type `country` | granularity `country` | status `canonical` | count `295`
- `European Union` -> `European Union countries` | type `bloc` | granularity `bloc` | status `canonical_bloc` | count `294`
- `NA` -> `unknown context` | type `unknown` | granularity `unknown` | status `ambiguous` | count `294`
- `Bangladesh` -> `Bangladesh` | type `country` | granularity `country` | status `canonical` | count `287`
- `BRA` -> `Brazil` | type `country` | granularity `country` | status `normalized_alias` | count `272`
- `Malaysia` -> `Malaysia` | type `country` | granularity `country` | status `canonical` | count `259`
- `Nigeria` -> `Nigeria` | type `country` | granularity `country` | status `canonical` | count `249`
- `Saudi Arabia` -> `Saudi Arabia` | type `country` | granularity `country` | status `canonical` | count `234`
- `Sub-Saharan Africa` -> `Sub-Saharan Africa` | type `region` | granularity `region` | status `canonical_region` | count `232`
- `developing countries` -> `developing countries` | type `bloc` | granularity `bloc` | status `canonical_bloc` | count `218`
- `Vietnam` -> `Vietnam` | type `country` | granularity `country` | status `canonical` | count `215`
- `EU` -> `European Union countries` | type `bloc` | granularity `bloc` | status `normalized_alias` | count `209`
- `RUS` -> `Russia` | type `country` | granularity `country` | status `normalized_alias` | count `209`
- `DEU` -> `Germany` | type `country` | granularity `country` | status `normalized_alias` | count `202`
