# Deferred Public Integration Note: Path/Mediator Output Layer

Date: 2026-04-05

This note records the public-integration work that should be deferred until the paper direction is more settled.

## What is being deferred

Do **not** change the public site or export pipeline yet.

Specifically defer changes to:

- `scripts/export_site_data_v2.py`
- generated `display_question_title` fields
- Astro question cards and question pages
- Streamlit question summaries

## Why it is deferred

The internal prototype strongly suggests that the surfaced object should usually be:

- a **path question**
- or a **mediator question**

But before shipping that publicly, we still want:

1. a stronger pass on the paper's full argument
2. a better sense of how the learned reranker will rank within the new object families
3. a cleaner read on which endpoint labels remain awkward or too generic

So public integration should come **after** the paper and reranker pass, not before.

## What to do later

When we return to public integration, the likely sequence should be:

### 1. Update export generation

Add exported internal/public fields such as:

- object family
- route label
- path/mediator display title
- path/mediator display why
- path/mediator first step

### 2. Update question cards and detail pages

Use:

- path-question titles for the path bucket
- mediator-question titles for the mediator bucket
- rare direct-edge wording only for direct exceptions

### 3. Add presentation logic for awkward labels

Before public release, review endpoint display labels that still read badly, especially cases like:

- `welfare`
- `welfare level`
- `cyclical component`
- `TVP-SV-VAR model`
- other method-like or low-level labels

### 4. Recheck shortlist readability

Before shipping:

- reread the top 50 public questions
- check that the new titles make the shortlist feel more specific and less misleading

## Current evidence supporting the eventual change

From the internal full-window prototype:

- `81` promote path questions
- `29` downrank path questions
- `7` promote mediator questions
- `2` downrank mediator questions
- `1` keep direct-edge

So the default future public object should almost certainly not remain the current direct-edge wording.
