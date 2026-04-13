"""HypotheSAEs analysis: discover what textual features predict link appearance.

Implements Ludwig/Mullainathan (2024) three-step procedure:
  Step 1: Train sparse autoencoders on text embeddings of candidate pairs
  Step 2: Use LLM to interpret predictive neurons as natural-language hypotheses
  Step 3: Validate hypotheses on held-out data

Uses async OpenAI calls for speed. Runs both text-embedding-3-small and
text-embedding-3-large in parallel.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load API key
KEY_PATH = Path("/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/key/openai_key_prashant.txt")
os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

import openai

PANEL_PATH = ROOT / "outputs/paper/37_benchmark_expansion/historical_feature_panel.parquet"
CORPUS_PATH = ROOT / "data/processed/research_allocation_v2/hybrid_corpus.parquet"
CONCEPTS_CSV = ROOT / "site/public/data/v2/central_concepts.csv"
OUT_DIR = ROOT / "outputs/paper/51_hypothesaes"
NOTE_PATH = ROOT / "next_steps/hypothesaes_note.md"

HORIZON = 10  # more positives = better signal
MAX_PAIRS = 15000  # keep it fast
EMBED_MODELS = ["text-embedding-3-small", "text-embedding-3-large"]
LLM_MODEL = "gpt-4.1-mini"  # fast + capable
FIDELITY_MODEL = "gpt-4.1-nano"  # cheapest
SAE_M = 256  # learnable concepts
SAE_K = 8   # active per example
TOP_NEURONS = 30  # interpret top N
CONCURRENCY = 10  # async concurrency (conservative to avoid timeouts)


# ======================================================================= #
# Step 0: Build text descriptions for each candidate pair
# ======================================================================= #
def build_pair_texts(panel_df: pd.DataFrame, corpus_df: pd.DataFrame) -> tuple[list[str], np.ndarray]:
    """Build a text description for each unique (u,v) pair."""
    print("Building pair texts...")
    concepts = pd.read_csv(CONCEPTS_CSV)
    label_map = dict(zip(concepts["concept_id"].astype(str), concepts["plain_label"].astype(str)))

    # Get recent titles per concept (last 10 years of corpus)
    recent = corpus_df[corpus_df["year"] >= 2015][["paper_id", "title", "src_code", "dst_code", "edge_kind", "evidence_type"]].copy()

    concept_titles: dict[str, list[str]] = {}
    concept_methods: dict[str, set[str]] = {}
    for _, row in recent.iterrows():
        for code_col in ["src_code", "dst_code"]:
            code = str(row[code_col])
            if code not in concept_titles:
                concept_titles[code] = []
                concept_methods[code] = set()
            if len(concept_titles[code]) < 5 and str(row["title"]) not in concept_titles[code]:
                concept_titles[code].append(str(row["title"])[:120])
            if pd.notna(row.get("evidence_type")):
                concept_methods[code].add(str(row["evidence_type"]))

    # Deduplicate pairs, use h=HORIZON slice
    h_panel = panel_df[panel_df["horizon"] == HORIZON].copy()
    pool_col = [c for c in h_panel.columns if c.startswith("in_pool_")]
    if pool_col:
        h_panel = h_panel[h_panel[pool_col[0]].astype(bool)]

    # Take most recent cutoffs for more signal
    pairs = h_panel.sort_values("cutoff_year_t", ascending=False).drop_duplicates(["u", "v"]).head(MAX_PAIRS)

    texts = []
    labels = pairs["appears_within_h"].astype(float).values

    for _, row in pairs.iterrows():
        u, v = str(row["u"]), str(row["v"])
        u_label = label_map.get(u, u)
        v_label = label_map.get(v, v)
        u_titles = concept_titles.get(u, [])[:3]
        v_titles = concept_titles.get(v, [])[:3]
        u_methods = ", ".join(list(concept_methods.get(u, set()))[:3]) or "not specified"
        v_methods = ", ".join(list(concept_methods.get(v, set()))[:3]) or "not specified"

        text = (
            f"Source concept: {u_label}. "
            f"Recent papers about {u_label}: {'; '.join(u_titles) if u_titles else 'none found'}. "
            f"Evidence methods for {u_label}: {u_methods}. "
            f"Target concept: {v_label}. "
            f"Recent papers about {v_label}: {'; '.join(v_titles) if v_titles else 'none found'}. "
            f"Evidence methods for {v_label}: {v_methods}. "
            f"Question: does a directed causal link from {u_label} to {v_label} appear within {HORIZON} years?"
        )
        texts.append(text)

    print(f"  Built {len(texts)} pair texts, {int(labels.sum())} positives ({labels.mean()*100:.1f}%)")
    return texts, labels


# ======================================================================= #
# Step 1: Async embedding generation
# ======================================================================= #
async def embed_batch_async(texts: list[str], model: str, batch_size: int = 500) -> np.ndarray:
    """Embed texts using OpenAI async API with retries."""
    client = openai.AsyncOpenAI(timeout=60.0)
    all_embeddings = []
    sem = asyncio.Semaphore(CONCURRENCY)

    async def embed_one_batch(batch: list[str], batch_idx: int) -> list[list[float]]:
        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.embeddings.create(input=batch, model=model)
                    return [d.embedding for d in resp.data]
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        print(f"    Batch {batch_idx} failed after 3 attempts: {e}")
                        raise

    batches = [texts[i:i+batch_size] for i in range(0, len(texts), batch_size)]
    print(f"  Embedding {len(texts)} texts in {len(batches)} batches with {model}...")
    t0 = time.time()

    tasks = [embed_one_batch(b, i) for i, b in enumerate(batches)]
    results = await asyncio.gather(*tasks)

    for batch_result in results:
        all_embeddings.extend(batch_result)

    arr = np.array(all_embeddings, dtype=np.float32)
    print(f"  Done: {arr.shape} in {time.time()-t0:.1f}s")
    return arr


# ======================================================================= #
# Step 2: Train SAE and select predictive neurons
# ======================================================================= #
def train_sae_and_select(embeddings: np.ndarray, labels: np.ndarray, model_name: str) -> dict:
    """Train SAE, select top predictive neurons."""
    import torch
    from hypothesaes import SparseAutoencoder
    from scipy.stats import pearsonr

    print(f"\n  Training SAE on {model_name} embeddings ({embeddings.shape})...")
    t0 = time.time()

    X = torch.tensor(embeddings, dtype=torch.float32)

    sae = SparseAutoencoder(
        input_dim=embeddings.shape[1],
        m_total_neurons=SAE_M,
        k_active_neurons=SAE_K,
    )
    sae.initialize_weights_(X[:1000])
    sae.fit(X, batch_size=256, n_epochs=10, learning_rate=1e-3, patience=3, show_progress=False)

    # Get activations
    activations = sae.get_activations(X, show_progress=False)
    if isinstance(activations, torch.Tensor):
        activations = activations.detach().cpu().numpy()
    print(f"  SAE trained in {time.time()-t0:.1f}s, activations shape: {activations.shape}")

    # Select top neurons by Pearson correlation with label
    correlations = []
    for j in range(activations.shape[1]):
        col = activations[:, j]
        if col.std() < 1e-10:
            correlations.append((j, 0.0, 1.0))
            continue
        r, p = pearsonr(col, labels)
        correlations.append((j, float(r), float(p)))

    correlations.sort(key=lambda x: abs(x[1]), reverse=True)
    top = correlations[:TOP_NEURONS]

    print(f"  Top 5 neurons by |correlation|:")
    for idx, (j, r, p) in enumerate(top[:5]):
        print(f"    Neuron {j}: r={r:.4f}, p={p:.4e}")

    return {
        "sae": sae,
        "activations": activations,
        "top_neurons": top,
        "model_name": model_name,
    }


# ======================================================================= #
# Step 3: Async LLM interpretation of top neurons
# ======================================================================= #
async def interpret_neurons_async(
    texts: list[str],
    labels: np.ndarray,
    activations: np.ndarray,
    top_neurons: list[tuple],
    n_examples: int = 15,
) -> list[dict]:
    """Use LLM to interpret what each top neuron captures."""
    client = openai.AsyncOpenAI(timeout=60.0)
    sem = asyncio.Semaphore(CONCURRENCY)
    hypotheses = []

    async def interpret_one(neuron_idx: int, corr: float, pval: float) -> dict:
        col = activations[:, neuron_idx]
        # Get top-activating examples
        top_indices = np.argsort(col)[-n_examples:][::-1]
        top_texts = [texts[i] for i in top_indices]
        top_labels = [int(labels[i]) for i in top_indices]

        # Also get bottom-activating examples for contrast
        bottom_indices = np.argsort(col)[:5]
        bottom_texts = [texts[i] for i in bottom_indices]

        prompt = f"""You are analyzing patterns in economics research data. Below are text descriptions of candidate research connections (pairs of economics concepts that might become linked in the literature).

These {n_examples} examples MOST strongly activate a specific learned feature (neuron {neuron_idx}) in a sparse autoencoder. The feature has correlation {corr:.3f} with whether the connection actually appears in the literature within {HORIZON} years.

HIGH-ACTIVATION EXAMPLES (this feature fires strongly for these):
{chr(10).join(f'  [{i+1}] (realized={top_labels[i]}) {t[:300]}' for i, t in enumerate(top_texts))}

LOW-ACTIVATION EXAMPLES (this feature does NOT fire for these):
{chr(10).join(f'  [{i+1}] {t[:300]}' for i, t in enumerate(bottom_texts))}

What pattern do the high-activation examples share that the low-activation examples lack? State your answer as a single testable hypothesis about what predicts whether a research connection will materialize. Be specific and concrete — refer to concepts, methods, or topics, not generic features. Start with "Hypothesis: ..." """

        async with sem:
            for attempt in range(3):
                try:
                    resp = await client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=300,
                    )
                    hypothesis_text = resp.choices[0].message.content.strip()
                    break
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        hypothesis_text = f"[interpretation failed: {e}]"

        return {
            "neuron": neuron_idx,
            "correlation": corr,
            "p_value": pval,
            "hypothesis": hypothesis_text,
            "n_high_examples": n_examples,
            "positive_rate_in_top": float(np.mean(top_labels)),
        }

    print(f"\n  Interpreting {len(top_neurons)} neurons with {LLM_MODEL}...")
    t0 = time.time()
    tasks = [interpret_one(j, r, p) for j, r, p in top_neurons]
    hypotheses = await asyncio.gather(*tasks)
    print(f"  Done in {time.time()-t0:.1f}s")
    return hypotheses


# ======================================================================= #
# Step 4: Async fidelity validation
# ======================================================================= #
async def validate_fidelity_async(
    hypotheses: list[dict],
    texts: list[str],
    labels: np.ndarray,
    n_test: int = 200,
) -> list[dict]:
    """Validate each hypothesis on held-out texts."""
    client = openai.AsyncOpenAI(timeout=60.0)
    sem = asyncio.Semaphore(CONCURRENCY)

    # Use a random subset for validation
    rng = np.random.RandomState(42)
    test_idx = rng.choice(len(texts), size=min(n_test, len(texts)), replace=False)
    test_texts = [texts[i] for i in test_idx]
    test_labels = labels[test_idx]

    async def score_one(hypothesis: dict, text: str) -> int:
        prompt = f"""Does the following research connection description match this hypothesis?

Hypothesis: {hypothesis['hypothesis'][:500]}

Research connection: {text[:400]}

Answer with just YES or NO."""

        async with sem:
            try:
                resp = await client.chat.completions.create(
                    model=FIDELITY_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=5,
                )
                answer = resp.choices[0].message.content.strip().upper()
                return 1 if "YES" in answer else 0
            except Exception:
                return 0

    print(f"\n  Validating {len(hypotheses)} hypotheses on {len(test_texts)} held-out texts...")
    t0 = time.time()

    validated = []
    for h_idx, hyp in enumerate(hypotheses[:15]):  # top 15 only for speed
        tasks = [score_one(hyp, t) for t in test_texts]
        scores = await asyncio.gather(*tasks)
        scores_arr = np.array(scores)
        test_positive = test_labels.astype(bool)

        # Compute fidelity: does the hypothesis predict the outcome?
        matches = scores_arr.astype(bool)
        tp = (matches & test_positive).sum()
        fp = (matches & ~test_positive).sum()
        fn = (~matches & test_positive).sum()
        tn = (~matches & ~test_positive).sum()

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        match_rate = matches.mean()
        positive_rate_among_matches = tp / max(tp + fp, 1)
        positive_rate_overall = test_positive.mean()

        validated.append({
            **hyp,
            "fidelity_precision": float(precision),
            "fidelity_recall": float(recall),
            "match_rate": float(match_rate),
            "positive_rate_if_match": float(positive_rate_among_matches),
            "positive_rate_baseline": float(positive_rate_overall),
            "lift": float(positive_rate_among_matches / max(positive_rate_overall, 0.001)),
        })

        if h_idx < 5:
            print(f"    Hyp {h_idx+1}: match_rate={match_rate:.2f}, lift={validated[-1]['lift']:.2f}x")

    print(f"  Validation done in {time.time()-t0:.1f}s")
    return validated


# ======================================================================= #
# Main
# ======================================================================= #
async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print("Loading data...")
    panel_df = pd.read_parquet(PANEL_PATH)
    corpus_df = pd.read_parquet(CORPUS_PATH)

    # Build texts
    texts, labels = build_pair_texts(panel_df, corpus_df)

    # Step 1: Embed with both models (sequentially to avoid connection overload)
    print("\n=== STEP 1: Embedding ===")
    embed_results = {}
    for model in EMBED_MODELS:
        embed_results[model] = await embed_batch_async(texts, model)

    # Save embeddings
    for model, emb in embed_results.items():
        safe_name = model.replace("-", "_")
        np.save(OUT_DIR / f"embeddings_{safe_name}.npy", emb)

    # Step 2: Train SAE on each embedding
    print("\n=== STEP 2: SAE Training ===")
    sae_results = {}
    for model, emb in embed_results.items():
        sae_results[model] = train_sae_and_select(emb, labels, model)

    # Step 3: Interpret top neurons (use small model's SAE for interpretation)
    print("\n=== STEP 3: Interpretation ===")
    all_hypotheses = {}
    for model in EMBED_MODELS:
        sr = sae_results[model]
        hypotheses = await interpret_neurons_async(
            texts, labels, sr["activations"], sr["top_neurons"]
        )
        all_hypotheses[model] = hypotheses

    # Step 4: Validate (use small model for speed)
    print("\n=== STEP 4: Fidelity Validation ===")
    validated = {}
    for model in EMBED_MODELS:
        validated[model] = await validate_fidelity_async(
            all_hypotheses[model], texts, labels
        )

    # Save results
    for model in EMBED_MODELS:
        safe_name = model.replace("-", "_")
        pd.DataFrame(validated[model]).to_csv(
            OUT_DIR / f"hypotheses_{safe_name}.csv", index=False
        )

    # Write note
    lines = [
        "# HypotheSAEs Analysis Results",
        "",
        f"Horizon: h={HORIZON}",
        f"Pairs analyzed: {len(texts)}",
        f"Positive rate: {labels.mean()*100:.1f}%",
        f"SAE config: M={SAE_M}, K={SAE_K}",
        f"Interpretation model: {LLM_MODEL}",
        f"Fidelity model: {FIDELITY_MODEL}",
        "",
    ]

    for model in EMBED_MODELS:
        lines.append(f"## Embedding model: {model}")
        lines.append("")
        lines.append("| Rank | Hypothesis | Correlation | Lift | Match Rate |")
        lines.append("|------|-----------|------------|------|------------|")
        for i, h in enumerate(validated[model], 1):
            hyp_short = h["hypothesis"][:150].replace("|", "/").replace("\n", " ")
            lines.append(
                f"| {i} | {hyp_short} | {h['correlation']:.3f} | {h['lift']:.1f}x | {h['match_rate']:.2f} |"
            )
        lines.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Print summary
    print("\n=== RESULTS ===\n")
    for model in EMBED_MODELS:
        print(f"--- {model} ---")
        for i, h in enumerate(validated[model][:10], 1):
            hyp_short = h["hypothesis"][:120].replace("\n", " ")
            print(f"  {i:2d}. [r={h['correlation']:.3f}, lift={h['lift']:.1f}x] {hyp_short}")
        print()

    print(f"Outputs: {OUT_DIR}")
    print(f"Note: {NOTE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
