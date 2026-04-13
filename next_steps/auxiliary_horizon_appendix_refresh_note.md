# Auxiliary Horizon Appendix Refresh

This appendix-only refresh extends the transparent benchmark comparison to auxiliary horizons.

- Main horizons (`h=5,10,15`) are taken from the locked current benchmark.
- Auxiliary horizons (`h=3,20`) are newly computed on the same effective-corpus stack.

## Mean performance

| Horizon | Model | Precision@100 | Recall@100 | Cutoffs |
|---------|-------|---------------|------------|---------|
| 3 | pref_attach | 0.0117 | 0.0566 | 6 |
| 3 | transparent | 0.0383 | 0.0956 | 6 |
| 5 | pref_attach | 0.0167 | 0.0377 | 6 |
| 5 | transparent | 0.0567 | 0.0852 | 6 |
| 10 | pref_attach | 0.0433 | 0.0450 | 6 |
| 10 | transparent | 0.1117 | 0.0890 | 6 |
| 15 | pref_attach | 0.0500 | 0.0362 | 5 |
| 15 | transparent | 0.1300 | 0.0839 | 5 |
| 20 | pref_attach | 0.0783 | 0.0341 | 6 |
| 20 | transparent | 0.1750 | 0.0791 | 6 |

## Interpretation

The horizon extension is not meant to redefine the paper's main benchmark. It shows how the
transparent graph score compares with popularity when the forecast horizon is made shorter or
longer than the main `5,10,15` design. The short-horizon cells speak more to near-term activation,
while the long-horizon cells speak more to slower closure in thicker literatures.
