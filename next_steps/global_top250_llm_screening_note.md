# Global Top-250 LLM Screening Note

Date: 2026-04-11

This pass applied the current `E/G/H` prompt family to the global top-250 package.

Inputs:

- prompt pack:
  - `outputs/paper/112_llm_screening_global_top250_prompt_pack`
- baseline run:
  - `outputs/paper/113_llm_screening_global_top250_none`
- pairwise repeats:
  - `outputs/paper/114_llm_screening_global_top250_repeat2`
  - `outputs/paper/115_llm_screening_global_top250_repeat3`
- analysis:
  - `outputs/paper/116_llm_screening_global_top250_analysis`

Observed API cost:

- baseline `E + G + H`: about `$5.58`
- pairwise repeat 2: about `$3.42`
- pairwise repeat 3: about `$3.42`
- total: about `$12.42`

Main findings:

- pairwise stability remains strong:
  - exact three-run agreement about `0.947`
  - stable preference share about `0.945`
- weak veto drops about `14.9%` of candidates
- weak veto still catches obvious high-ranked broad candidates in the global object
- local pairwise cleanup improves bucket quality on broadness and compression:
  - mean bucket-top10 broad share: about `0.536 -> 0.225`
  - mean bucket-top10 low-compression share: about `0.597 -> 0.313`
- but local pairwise cleanup does not automatically improve every concentration metric:
  - mean bucket-top10 top-target share rises slightly, about `0.238 -> 0.249`

Interpretation:

- the `E/G/H` architecture transfers to the global top-250 object
- but the clean operational object is still bucket-local cleanup inside the global universe,
  not a fully resolved new global rank
- some buckets are thin inside the global top-250 set, especially macro-finance and trade,
  so local pairwise reranking has limited room to work there

Current read:

- `E` remains useful as a weak veto
- `H` remains stable enough for local cleanup
- but the global top-250 object needs one more design decision before becoming a final
  LLM-ranked browse product:
  - either accept it as bucket-local cleanup only
  - or design a second-stage cross-bucket composition rule
