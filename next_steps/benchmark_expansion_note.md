# Benchmark Expansion Note

## Scope

- stronger transparent baselines on the historical candidate panel
- same graph candidate universe used by the current benchmark path

## Main read

This pass asks whether the graph score is only beating preferential attachment because that benchmark is too weak.

The answer is: **yes, that is now a real concern**.

### Horizon 5
- Graph score beats only `lexical_similarity` and `cooc_gap` on mean precision@100.
- It does **not** beat `degree_recency`, `pref_attach`, or `directed_closure`.
- Strongest transparent alternative here is `degree_recency` with precision@100=0.141667.
- The closest top-100 alternative is `directed_closure` with graph coverage=0.595.

### Horizon 10
- Graph score beats only `lexical_similarity` and `cooc_gap` on mean precision@100.
- It does **not** beat `degree_recency`, `pref_attach`, or `directed_closure`.
- Strongest transparent alternative here is `degree_recency` with precision@100=0.270000.
- The closest top-100 alternative is `directed_closure` with graph coverage=0.595.

## Interpretation

This is the first recent result that materially weakens the current benchmark claim.

The graph score still beats the weakest transparent baselines, but once the benchmark family is widened, it no longer looks like the clear winner.

That means the paper's next core problem is now:

- benchmark strength

not:

- ontology
- surface wording
- extension layering

## Recommendation

Do:

1. treat this as the next benchmark-strengthening layer for the paper
2. use the strongest transparent alternative as a real benchmark challenge, not as a footnote robustness check
3. keep the benchmark family small and interpretable

Do not:

- turn this into a broad benchmark zoo
- add opaque semantic or embedding baselines before the transparent layer is interpreted
