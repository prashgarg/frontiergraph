# FrontierGraph

FrontierGraph is a deterministic metascience tool for ranking what economics should work on next.

- Public site: `https://frontiergraph.com`
- Public beta app: `https://economics-opportunity-ranker-beta-1058669339361.us-central1.run.app`
- Repository: `https://github.com/prashgarg/frontiergraph`

The project has three public layers:

1. an Astro-based public website,
2. a static discovery layer with ranked pages by field and discovery mode,
3. a Streamlit app for deeper interactive inspection.

AI is used only to convert text into graph structure. Everything after graph extraction is deterministic and inspectable.

## Public release contents

- `site/`: Astro marketing site and static discovery pages
- `app/`: Streamlit beta app
- `scripts/export_site_data.py`: exports site-ready JSON/CSV from the beta SQLite database
- `data/demo/`: small demo dataset kept in the repo
- `site/public/downloads/`: checksum and manifest for the full beta database package

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
frontiergraph --db data/processed/app_causalclaims.db
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

## Build the static site data

The public site is backed by generated JSON/CSV derived from the full beta SQLite database.

```bash
PYTHONPATH=. python scripts/export_site_data.py
```

This writes:

- `site/src/generated/site-data.json`
- `site/public/data/*.csv`
- `site/public/downloads/frontiergraph-economics-beta.manifest.json`
- `site/public/downloads/frontiergraph-economics-beta.sha256.txt`

If you have a public mirror for the full beta DB, set:

```bash
export FRONTIERGRAPH_PUBLIC_DB_URL="https://..."
```

before running the export so the downloads page points to the live artifact.

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
- beta app: Streamlit on Google Cloud Run
- beta SQLite database: mounted read-only from Google Cloud Storage
- public static discovery layer: generated into the Astro site from the SQLite DB

See [deploy/PUBLIC_BETA.md](deploy/PUBLIC_BETA.md) for deployment notes.

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
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile app/streamlit_app.py src/run_ranker.py src/opportunity_data.py scripts/export_site_data.py
```

## Citation and license

- Citation: [CITATION.cff](CITATION.cff)
- Code license: Apache-2.0 in [LICENSE](LICENSE)
