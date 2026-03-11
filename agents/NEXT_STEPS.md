# Next Steps

## Main Current Priority

The main priority is product and UX polish, not new backend infrastructure.

The core stack already exists:

- corpus
- extraction
- ontology comparison
- concept graph
- ranking
- suppression
- site
- live app

What remains is making the product clearer, simpler, and more compelling.

## Highest-Priority Tasks

### 1. Simplify the public experience

- reduce homepage density
- make the graph page feel more elegant and graph-first
- keep opportunities page more curated
- keep methods/comparison deeper and less mandatory

### 2. Validate the default product view

- continue testing `Baseline exploratory` as the public default
- use `Broad strict` as the main strict comparison reference
- confirm that the default actually produces the best visible recommendations

### 3. Keep duplicate cleanup practical

- preserve the top-slice suppression approach
- avoid full-table suppression attempts
- only tune the baseline top slice if needed

## Medium-Priority Tasks

### 4. Public downloads alignment

- decide whether the public downloads bucket should expose the new baseline suppressed DB

### 5. Search improvements

- lexical/alias search on the public site is enough for now
- future semantic search belongs in the app

### 6. Better public comparison communication

- comparison should stay available
- but not overwhelm the main product path

## Lower-Priority / Later Tasks

### 7. Revisit working papers

- NBER / CEPR can return later
- not the main blocker now

### 8. Broader ontology redesign

- not needed right now
- compare build is good enough for current product work

### 9. Broad strict exposure

- keep in reserve as the main strict reference
- can be exposed more later if users want robust comparison views

## Decision Log

- product is no longer blocked on ontology infrastructure
- product is now mostly blocked on clarity, design, and selective surfacing

## Recommended Resumption Order

If a new thread starts and there is no new urgent bug:

1. inspect homepage and graph page
2. simplify copy/layout
3. check baseline exploratory top recommendations
4. adjust only top-slice suppression if truly needed
5. defer deeper methodological extensions unless asked

