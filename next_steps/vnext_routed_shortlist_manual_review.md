# vNext Routed Shortlist Manual Review

## What changed

The conservative routing layer changed:

- `27` shortlist rows
- `14` unique pairs

Most rows stayed on the baseline path/mechanism object.
That is good. It means the richer ontology is only taking over when its signal is unusually strong.

## Overall judgment

This is a real improvement.

The routing layer makes the shortlist better in exactly the right way:

- it does **not** replace the whole frontier object
- it upgrades a small subset of rows into more specific and more actionable question types

So this looks like a good internal architecture:

1. baseline path/mechanism object as default
2. richer routed object when ontology-vNext signal is strong

## Best improvements

### 1. `financial development -> green innovation`

Baseline:

- `Through which nearby pathways might financial development shape green innovation?`

Routed:

- `Where should we test the financial development -> green innovation relation next?`

Why the routed object is better:

- the pair evidence is narrow (`South Africa`)
- the endpoints themselves live in much broader settings
- the new object is more empirical and more actionable

This is one of the strongest examples of context-transfer working well.

### 2. `CO2 emissions -> exports`

Baseline:

- `Through which nearby pathways might CO2 emissions shape exports?`

Routed:

- `Where should we test the CO2 emissions -> exports relation next?`

Why the routed object is better:

- the baseline is still broad
- the routed version identifies a concrete next question: move beyond the `EU-15` evidence concentration

This is also a very strong context-transfer example.

### 3. `willingness to pay -> CO2 emissions`

Baseline:

- `Through which nearby pathways might willingness to pay shape CO2 emissions?`

Routed:

- `What evidence should come next for the willingness to pay -> CO2 emissions relation?`

Why the routed object is better:

- the evidence profile is dominated by descriptive observation
- the routed version gives a much more useful follow-up direction: stronger empirical design

This is one of the strongest evidence-expansion examples.

### 4. `price changes -> CO2 emissions`

Baseline:

- `Through which nearby pathways might price changes shape CO2 emissions?`

Routed:

- `What evidence should come next for the price changes -> CO2 emissions relation?`

Why the routed object is better:

- the baseline path question is plausible but vague
- the routed version says what would actually move the literature: stronger evidence than repeated descriptive work

## Improvements that are real but weaker

These reroutes are directionally right, but less compelling:

- `output -> CO2 emissions`
- `willingness to pay -> housing prices`
- `technological innovation -> green finance`

Why weaker:

- the routing logic is real
- but the endpoints are more generic or less intrinsically sharp

So the routed object becomes more specific, but not always more interesting.

## Main new bottleneck

The current routing layer still needs one more guardrail:

- **endpoint genericity**

Right now a pair can qualify for context-transfer even if the endpoint labels are still too broad to make the rerouted object feel crisp.

So the next refinement should be:

- keep the routing logic
- add a general generic-endpoint penalty or exclusion for routed objects

That would likely improve the weaker context-transfer cases without damaging the strongest ones.

## What this means

The key architectural conclusion is now stronger:

- path/mechanism remains the right default object
- routed ontology-vNext objects are the right second-layer specialization

That looks much better than either extreme:

- only flat path/mechanism objects forever
- or replacing everything with the new ontology-vNext objects immediately

## Recommendation

The next internal move should be:

1. keep the conservative routing structure
2. add a generic-endpoint guardrail for routed objects
3. rerun the routed shortlist
4. then decide whether the routed layer is strong enough to mention as a methodological extension in the paper

## Bottom line

This pass is successful.

The routed shortlist is better than the baseline shortlist on the changed rows.
But it also revealed the next refinement clearly, which is exactly what we want at this stage.
