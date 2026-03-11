# Deployment And Storage

## Purpose

This file records how the live site/app are deployed, what the buckets are for, and what storage decisions have already been made.

## Live Surfaces

- public site: Cloudflare Pages
- live app: Google Cloud Run

## Cloudflare Pages

The Astro site is built and deployed through the connected GitHub repo.

Important operational facts:

- successful deploys come from pushes to `main`
- the current rewritten site is already live

## Cloud Run

The live app is deployed on Cloud Run.

Current live runtime DB:

- `concept_exploratory_suppressed_top100k_app_20260309.sqlite`

This replaced the old live runtime use of `app_causalclaims.db`.

## Buckets

### Private app/runtime bucket

Bucket:

- `frontiergraph-ranker-data-1058669339361`

Purpose:

- mounted by Cloud Run
- holds runtime DB artifacts

Important objects:

- `concept_exploratory_suppressed_top100k_app_20260309.sqlite`
  - current live runtime DB
- `app_causalclaims.db`
  - old legacy DB, kept only as rollback

### Public downloads bucket

Bucket:

- `frontiergraph-public-downloads-1058669339361`

Purpose:

- public downloadable artifacts only
- not app runtime

Current state:

- left unchanged during the live app migration

## Current Deployment Decisions

- private bucket updated first for the live app migration
- public bucket intentionally left alone until the product-facing runtime was confirmed
- old runtime DB was not deleted immediately

## Storage Cleanup Already Done

Deleted safely:

- failed ontology runs
- wrong BigQuery shard
- duplicate fast review-pack folder
- extraction sample staging folder
- failed diagnostic ontology `v3`

These deletions were already made.

## Storage Policy

Keep local:

- canonical merged extraction DB/JSONL
- enriched OpenAlex SQLite
- baseline compare outputs
- current baseline suppressed app DB

Archive or online-only:

- raw batch inputs
- raw batch outputs
- broad/conservative compare DBs if space is tight

## Key Decisions

- current live app should not mention or depend on the old legacy DB as the product surface
- private bucket is runtime only
- public bucket is downloads only
- old `app_causalclaims.db` remains only as rollback until no longer needed

## Decision Log

- site redeployed from the rewritten concept graph version
- live app moved to the suppressed baseline DB
- public bucket intentionally not changed at the same time

## Open Questions

- whether to replace the public downloadable DB with the new baseline suppressed DB
- when to remove the rollback `app_causalclaims.db`
- whether to move more large artifacts online-only after the current product state stabilizes

## Recommended Next Actions

- leave rollback DB alone until there is no need for it
- change the public bucket only when you want downloads to match the new live app more explicitly
- preserve manifests and summaries before aggressive storage cleanup

