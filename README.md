# FrontierGraph

FrontierGraph is a deterministic metascience tool for ranking what economics should work on next.

- Public site: `https://frontiergraph.com`
- Public app: `https://frontiergraph-app-1058669339361.us-central1.run.app`
- HTML manuscript: `https://frontiergraph.com/paper/`
- Working paper PDF: `https://frontiergraph.com/downloads/frontiergraph-working-paper.pdf`
- Repository: `https://github.com/prashgarg/frontiergraph`

The project has three public layers:

1. an Astro-based public website for browsing questions and skimming the literature map,
2. a Streamlit app for deeper interactive inspection,
3. a paper-and-data layer with HTML paper pages, PDFs, and tiered downloads.

AI is used only to convert text into graph structure. Everything after graph extraction is deterministic and inspectable.

## Public release contents

- `site/`: Astro marketing site and static discovery pages
- `app/`: Streamlit public app
- `scripts/export_site_data_v2.py`: exports site-ready JSON/CSV from the canonical public release source
- `scripts/build_frontiergraph_public_release_bundle.py`: builds the canonical public SQLite bundle
- `scripts/sync_paper_site_assets.py`: syncs the paper markdown and figure assets into the site
- `data/demo/`: small demo dataset kept in the repo
- `site/public/downloads/`: PDFs, checksum, and manifest for the public graph bundle

See [DATA_README.md](DATA_README.md) and [DATA_PROVENANCE.md](DATA_PROVENANCE.md) for data packaging details.

## Quickstart

Install the package:

```bash
python -m pip install -e '.[dev]'
```

Run the app locally:

```bash
frontiergraph
```

The legacy alias still works:

```bash
economics-ranker
```

Useful flags:

```bash
frontiergraph --db data/production/frontiergraph_public_release/frontiergraph-economics-public.db
frontiergraph --port 8502
frontiergraph --headless
```

## Run the demo pipeline

```bash
python -m src.build_corpus --adapter demo --out data/processed/corpus.parquet --config config/config.yaml
python -m src.features_pairs --in data/processed/corpus.parquet --out data/processed/pairs.parquet --tau 2
python -m src.features_paths --in data/processed/corpus.parquet --out data/processed/missing_edges.parquet --max_len 2
python -m src.features_motifs --in data/processed/corpus.parquet --out data/processed/motif_gaps.parquet
python -m src.scoring --pairs data/processed/pairs.parquet --paths data/processed/missing_edges.parquet --motifs data/processed/motif_gaps.parquet --out data/processed/candidates.parquet
python -m src.store_sqlite --corpus data/processed/corpus.parquet --candidates data/processed/candidates.parquet --out data/processed/app.db
frontiergraph --db data/processed/app.db
```

## Build the site data, paper assets, and public bundle

The public site and deeper app share one canonical public release bundle. A typical refresh sequence is:

```bash
PYTHONPATH=. python scripts/export_site_data_v2.py
python scripts/build_frontiergraph_public_release_bundle.py
PYTHONPATH=. python scripts/export_site_data_v2.py
```

This writes:

- `site/src/generated/site-data.json`
- `site/src/generated/paper/*`
- `site/public/data/v2/*`
- `data/production/frontiergraph_public_release/frontiergraph-economics-public.db`
- `site/public/downloads/frontiergraph-economics-public.manifest.json`
- `site/public/downloads/frontiergraph-economics-public.sha256.txt`

If you have a live public DB mirror and app host, set:

```bash
export FRONTIERGRAPH_PUBLIC_DB_URL="https://..."
export FRONTIERGRAPH_PUBLIC_APP_URL="https://frontiergraph-app-1058669339361.us-central1.run.app"
```

before running the export so the site points at the live public artifacts.

## Build the Astro site

Node is required locally for the Astro build.

```bash
cd site
npm install
npm run build
```

Cloudflare Pages should use:

- Root directory: `site`
- Build command: `npm install && npm run build`
- Build output directory: `dist`

## Deployment architecture

- `frontiergraph.com`: Astro site on Cloudflare Pages
- `https://frontiergraph-app-1058669339361.us-central1.run.app`: Streamlit app on Google Cloud Run
- public SQLite bundle: hosted from Google Cloud Storage
- public static pages: generated into the Astro site from the same release source of truth

See [deploy/PUBLIC_RELEASE.md](deploy/PUBLIC_RELEASE.md) for deployment notes.

## Optional larger economics build

```bash
python -m src.build_corpus --adapter causalclaims --out data/processed/corpus_causalclaims.parquet --config config/config_causalclaims.yaml
python -m src.features_pairs --in data/processed/corpus_causalclaims.parquet --out data/processed/pairs_causalclaims.parquet --tau 2
python -m src.features_paths --in data/processed/corpus_causalclaims.parquet --out data/processed/missing_edges_causalclaims.parquet --max_len 2 --max_neighbors_per_mediator 120
python -m src.features_motifs --in data/processed/corpus_causalclaims.parquet --out data/processed/motif_gaps_causalclaims.parquet --max_neighbors_per_mediator 120
python -m src.scoring --pairs data/processed/pairs_causalclaims.parquet --paths data/processed/missing_edges_causalclaims.parquet --motifs data/processed/motif_gaps_causalclaims.parquet --out data/processed/candidates_causalclaims.parquet --config config/config_causalclaims.yaml
python -m src.store_sqlite --corpus data/processed/corpus_causalclaims.parquet --candidates data/processed/candidates_causalclaims.parquet --out data/processed/app_causalclaims.db --config config/config_causalclaims.yaml
```

## Optional LLM extractor

Estimate-only mode:

```bash
python -m src.adapters.llm_extractor_adapter --in data/raw/custom_docs.jsonl --out data/processed/corpus_llm.parquet --estimate_cost
```

Execution mode:

```bash
python -m src.adapters.llm_extractor_adapter --in data/raw/custom_docs.jsonl --out data/processed/corpus_llm.parquet --estimate_cost --execute
```

The extractor uses `OPENAI_API_KEY` if present, otherwise it reads the configured key-path file.

## Tests

```bash
python -m pytest -q
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile app/streamlit_app.py src/run_ranker.py src/opportunity_data.py scripts/export_site_data_v2.py scripts/build_frontiergraph_public_release_bundle.py
```

## Citation and license

- Citation: [CITATION.cff](CITATION.cff)
- Code license: Apache-2.0 in [LICENSE](LICENSE)
