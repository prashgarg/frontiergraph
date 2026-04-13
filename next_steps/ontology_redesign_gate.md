# Ontology Redesign Gate

Date: 2026-04-05

This note records when ontology redesign should begin, and when it should stay deferred.

## Default rule

Do **not** redesign ontology during the current paper pass unless the downstream evidence says it is still the binding bottleneck after:

- the paper object rewrite
- the reranker
- the path/mechanism formalization
- the ripeness panel

## Evidence that counts as a real ontology trigger

### 1. Repeated high-cost merge failures

Examples:

- a few broad nodes keep generating generic false positives
- manual review repeatedly says a promoted candidate is broad only because the node already merged several distinct concepts

### 2. Repeated audit labels of the right kind

Specifically:

- `ontology_merge_problem`
- `split_endpoint_concepts`
- similar failure labels that are not better explained by path/mechanism reframing

### 3. Reranker cannot separate good from bad candidates because endpoint identity is too coarse

This is a real ontology problem if:

- strong reranker features still cannot distinguish useful from generic candidates
- and manual review says the issue is not ranking but concept collapse

### 4. Path/mechanism phrasing remains awkward for the same repeated nodes

If the same endpoint labels repeatedly read badly even after the object is improved, those nodes become the first redesign targets.

## What does not count as a redesign trigger

- external benchmark mismatch by itself
- path-vs-direct object mismatch
- genericity that can be handled by reranking
- bad product wording that is really a display-label issue

## Redesign variants

### Variant A. Minimal patch

- split or relabel only the highest-cost nodes
- add explicit do-not-merge rules

Use when:

- only a small set of nodes is repeatedly causing problems

### Variant B. Layered frontier ontology

Store:

- paper-local mention
- canonical concept
- parent/family concept
- mapping type:
  - exact
  - synonym
  - broader
  - narrower
  - related

Use when:

- repeated failures show the current flat ontology is the problem

### Variant C. Full redesign

Use only if:

- minimal patch fails
- layered ontology still leaves major downstream failures

## Decision rule

Start with the smallest redesign that fixes repeated high-cost errors.

The ontology should only become the next main workstream once the frozen-ontology paper pass has shown that ranking and object improvements are not enough on their own.
