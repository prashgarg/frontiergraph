# Too-Broad Intermediate Parent Inspection (v2.2)

- reviewed too-broad rows inspected: `727`
- suggestion rows written: `1,711`
- parents represented: `245`
- top-k suggestions per row: `3`
- plausible threshold: `score >= 0.30` and `lexical_jaccard >= 0.20`

## Row Status Counts

- `has_plausible_intermediate`: `362`
- `low_confidence_intermediate_only`: `196`
- `missing_intermediate_candidate`: `169`

## Parents With Most Missing/Low-Confidence Intermediate Coverage

| candidate_parent_id                                   | candidate_parent_label   |   cases |   cases_with_plausible |   missing_cases |   low_confidence_cases |   avg_top_score |   weighted_child_mass |   plausible_rate |
|:------------------------------------------------------|:-------------------------|--------:|-----------------------:|----------------:|-----------------------:|----------------:|----------------------:|-----------------:|
| jel:C99:Behavioral                                    | Behavioral               |      11 |                      0 |              11 |                      0 |       0         |                   626 |        0         |
| Q8134                                                 | economics                |      41 |                     24 |               6 |                     11 |       0.274966  |                  8792 |        0.585366  |
| jel:O:Economic Development                            | Economic Development     |       9 |                      2 |               6 |                      1 |       0.128181  |                   955 |        0.222222  |
| https://openalex.org/keywords/mathematics             | Mathematics              |      18 |                      0 |               3 |                     15 |       0.132765  |                   280 |        0         |
| https://openalex.org/keywords/chemistry               | Chemistry                |       3 |                      0 |               3 |                      0 |       0         |                    21 |        0         |
| jel:I12:Disability                                    | Disability               |       3 |                      0 |               3 |                      0 |       0         |                    55 |        0         |
| jel:C50:Econometric Modeling                          | Econometric Modeling     |       3 |                      0 |               3 |                      0 |       0         |                   205 |        0         |
| https://openalex.org/keywords/epidemiology            | Epidemiology             |       3 |                      0 |               3 |                      0 |       0         |                    12 |        0         |
| jel:C70:Strategic.                                    | Strategic.               |       3 |                      0 |               3 |                      0 |       0         |                    89 |        0         |
| https://openalex.org/keywords/environmental-science   | Environmental science    |      11 |                      1 |               2 |                      8 |       0.145428  |                   107 |        0.0909091 |
| jel:J10:Demographic Economics                         | Demographic Economics    |       3 |                      0 |               2 |                      1 |       0.0800783 |                   395 |        0         |
| jel:C55:Big data                                      | Big data                 |       2 |                      0 |               2 |                      0 |       0         |                    15 |        0         |
| https://openalex.org/keywords/chemical-engineering    | Chemical engineering     |       2 |                      0 |               2 |                      0 |       0         |                     1 |        0         |
| FGV21FAM:economic-fundamentals:5ea12eb3fd             | Economic Fundamentals    |       2 |                      0 |               2 |                      0 |       0         |                     6 |        0         |
| jel:O18:Rural Development                             | Rural Development        |       2 |                      0 |               2 |                      0 |       0         |                    31 |        0         |
| jel:R12:Urban Rural                                   | Urban Rural              |       2 |                      0 |               2 |                      0 |       0         |                    64 |        0         |
| https://openalex.org/keywords/world-economy           | World economy            |       2 |                      0 |               2 |                      0 |       0         |                    42 |        0         |
| https://openalex.org/keywords/health-professions      | Health professions       |      16 |                      3 |               1 |                     12 |       0.201561  |                   228 |        0.1875    |
| jel:A12:Computer Science                              | Computer Science         |       6 |                      0 |               1 |                      5 |       0.100912  |                    26 |        0         |
| https://openalex.org/keywords/artificial-intelligence | Artificial intelligence  |       3 |                      0 |               1 |                      2 |       0.0789809 |                    26 |        0         |
| jel:F:Trade                                           | Trade                    |       3 |                      1 |               1 |                      1 |       0.164597  |                   250 |        0.333333  |
| jel:H51:Health                                        | Health                   |       2 |                      0 |               1 |                      1 |       0.137387  |                    20 |        0         |
| jel:F63:Development                                   | Development              |       3 |                      2 |               1 |                      0 |       0.233876  |                   136 |        0.666667  |
| jel:G34:Acquisition                                   | Acquisition              |       1 |                      0 |               1 |                      0 |       0         |                     0 |        0         |
| jel:Q14:Agricultural Bank                             | Agricultural Bank        |       1 |                      0 |               1 |                      0 |       0         |                     0 |        0         |

## Frequent Gap Tokens In Missing/Low-Confidence Cases

- `economy`: `13`
- `policy`: `13`
- `management`: `11`
- `research`: `9`
- `studies`: `9`
- `analysis`: `8`
- `methods`: `8`
- `health`: `7`
- `economic`: `6`
- `statistical`: `6`
- `mathematical`: `6`
- `education`: `6`
- `development`: `5`
- `equations`: `5`
- `cancer`: `5`
- `theory`: `4`
- `income`: `4`
- `models`: `4`
- `public`: `4`
- `financial`: `4`
- `markets`: `4`
- `advanced`: `4`
- `healthcare`: `4`
- `intelligence`: `4`
- `law`: `4`
- `19`: `4`
- `covid`: `4`
- `market`: `4`
- `global`: `3`
- `ratio`: `3`
