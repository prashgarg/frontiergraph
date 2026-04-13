# V2 Threshold Strategy

## Question

How should `data/ontology_v2/extraction_label_mapping_v2.parquet` be interpreted
given that many extraction labels are compound operationalisation phrases while
the ontology is built from formal concept names?

## Recommendation

Use a **tiered confidence scheme**:

- `linked`: score `>= 0.85`
- `soft`: score `0.75–0.85`
- `candidate`: score `0.65–0.75`
- `unmatched`: score `< 0.65`

This keeps `0.75` as the primary "soft" threshold while adding a lower-confidence
candidate band for structurally common compound labels such as:

- `renewable energy consumption` → `Renewable Energy`
- `gdp per capita` → `GDP`
- `trade openness` → `Trade Liberalization`

The `candidate` tier should be described as:

- usable for exploratory downstream work
- not equivalent to the `soft` tier
- explicitly lower confidence and more vulnerable to semantic drift

## Why this is the right choice

### 1. The gap is structural, not a bug

The ontology vocabulary and extraction vocabulary are doing different things:

- ontology: formal concept names
- extraction: paper-local operationalisation phrases

So a large low-score tail is expected even when the nearest neighbor is still
directionally useful.

### 2. Keeping only `>= 0.75` leaves too much usable structure on the table

At the current primary threshold (`0.75`):

- matched labels: `316,292` (`22.76%`)
- matched occurrences: `553,015` (`31.37%`)

At `0.65`:

- matched labels: `840,843` (`60.50%`)
- matched occurrences: `1,181,683` (`67.03%`)

So the `0.65–0.75` band alone adds:

- `524,551` labels
- `628,668` occurrences

That is too large to ignore entirely if the goal is to explain the mapping
honestly.

### 3. But `0.65` should not replace `0.75`

The candidate band is large and visibly noisier.

Examples that look directionally plausible:

- `renewable energy consumption` → `Renewable Energy` (`0.732`)
- `gdp per capita` → `GDP` (`0.708`)
- `economic policy uncertainty` → `Policy uncertainty` (`0.723`)

Examples that look risky or over-broad:

- `carbon emissions` → `Carbon emission trading` (`0.690`)
- `firm productivity` → `Work productivity` (`0.686`)
- `exchange rate volatility` → `Exchange-rate flexibility` (`0.694`)
- `bank performance` → `Bank credit` (`0.702`)

So the candidate band is useful, but it is not clean enough to become the new
default "matched" threshold.

## Threshold sweep

| Threshold | Matched labels | % labels | Matched occurrences | % occurrences |
|---|---:|---:|---:|---:|
| `>= 0.60` | 1,130,209 | 81.32 | 1,494,119 | 84.75 |
| `>= 0.65` | 840,843 | 60.50 | 1,181,683 | 67.03 |
| `>= 0.70` | 547,146 | 39.37 | 842,747 | 47.80 |
| `>= 0.75` | 316,292 | 22.76 | 553,015 | 31.37 |
| `>= 0.80` | 169,240 | 12.18 | 352,149 | 19.98 |
| `>= 0.85` | 92,249 | 6.64 | 241,435 | 13.70 |

## Recommended bands

| Band | Labels | % labels | Occurrences | % occurrences |
|---|---:|---:|---:|---:|
| `linked` (`>= 0.85`) | 92,249 | 6.64 | 241,435 | 13.70 |
| `soft` (`0.75–0.85`) | 224,043 | 16.12 | 311,580 | 17.67 |
| `candidate` (`0.65–0.75`) | 524,551 | 37.74 | 628,668 | 35.66 |
| `unmatched` (`< 0.65`) | 549,064 | 39.50 | 581,216 | 32.97 |

## What changes across thresholds

### 0.75 as primary threshold

Best if the paper wants:

- stronger precision
- cleaner methodological story
- more conservative claim about ontology coverage

Weakness:

- only `31.37%` of occurrences are treated as matched
- this makes the structural gap look more severe than it functionally is

### 0.65 as primary threshold

Best if the goal were raw coverage.

Weakness:

- pulls in too many semantically loose nearest neighbors
- blurs the distinction between confident mapping and exploratory mapping

Conclusion:

- do **not** use `0.65` as the main "soft" threshold
- use it as an explicit lower-confidence `candidate` tier

## Candidate-band diagnostics

### Source mix by occurrence in `0.65–0.75`

- `openalex_keyword`: `230,431` (`36.65%`)
- `jel`: `182,862` (`29.09%`)
- `wikipedia`: `173,001` (`27.52%`)
- `wikidata`: `35,356` (`5.62%`)
- `openalex_topic`: `7,018` (`1.12%`)

Compared with the `soft` tier, the candidate band is relatively more
Wikipedia-heavy and remains keyword-heavy, which is consistent with it being a
broader and looser semantic layer.

### Ambiguity by rank-1 / rank-2 gap

Within the `candidate` band:

- gap `<= 0.005`: `12,444` labels, `20,496` occurrences
- gap `<= 0.010`: `25,249` labels, `40,073` occurrences
- gap `<= 0.020`: `52,068` labels, `80,451` occurrences
- gap `<= 0.050`: `137,105` labels, `194,599` occurrences

This is useful because the lowest-gap rows are the best place to aim a
false-positive filter.

## Nano-review scope

## Should a nano model review the candidate tier?

Yes, but **not** as a full review of all `524,551` candidate rows.

That would be too large, too noisy, and not obviously worth the cost before the
paper rewrite.

### What a nano review is good for

A nano model can act as a **false-positive filter** on the most ambiguous rows
inside the `0.65–0.75` band.

Best targets:

1. candidate-tier rows with small rank-1 / rank-2 gap
2. candidate-tier rows with high frequency
3. candidate-tier rows whose matched ontology label is obviously broader or of a
   different semantic type than the extraction label

### Practical review design

Input per row:

- extraction label
- rank-1 ontology label
- rank-1 score
- rank-2 ontology label
- rank-2 score
- ontology source

Prompt objective:

- Is rank-1 a plausible ontology grounding for this extracted label?
- Output:
  - `accept`
  - `reject`
  - `unclear`

### Best first pass

Do **not** review all candidate rows.

Instead, review one of:

- top-frequency candidate rows with gap `<= 0.02`
- or a capped set such as the top `5,000–20,000` most consequential ambiguous rows

That gives a cheap false-positive screen while preserving the paper's simple
methodological story.

## Paper-facing wording implication

The paper should not say:

- "we matched X% of labels to the ontology"

without qualification.

It should say something closer to:

- high-confidence and soft matches cover `31.4%` of occurrences at the primary
  threshold
- adding a lower-confidence candidate tier raises that to `67.0%`
- the remaining gap is structural because extracted labels are often
  paper-specific compound operationalisation phrases

## Final position

Use:

- `0.75` as the primary soft threshold
- `0.65` as a candidate tier
- optional targeted nano false-positive filtering on the ambiguous candidate rows

Do not:

- collapse `candidate` into `soft`
- present `0.65` as equally reliable
- pretend the unmatched tail is merely a pipeline bug
