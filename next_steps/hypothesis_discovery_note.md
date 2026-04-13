# Hypothesis Discovery Results

Panel: 60000 pairs at h=10, 3760 positives (6.3%)

---

## Approach A: SHAP Values

### Global feature importance (mean |SHAP|)

| Rank | Feature | Mean |SHAP| | Coefficient |
|------|---------|-------------|-------------|
| 1 | target_recent_support_in_degree | 1.6711 | 2.4272 |
| 2 | source_recent_support_out_degree | 1.5536 | 2.4025 |
| 3 | target_support_in_degree | 1.2263 | -1.6395 |
| 4 | target_recent_incident_count | 1.0722 | -1.7388 |
| 5 | source_support_out_degree | 1.0284 | -1.4568 |
| 6 | source_recent_incident_count | 0.8705 | -1.5506 |
| 7 | target_direct_in_degree | 0.4964 | 0.8628 |
| 8 | source_direct_out_degree | 0.3143 | 0.6651 |
| 9 | support_age_years | 0.2429 | 0.2875 |
| 10 | pair_evidence_diversity_mean | 0.2173 | 0.2757 |
| 11 | cooc_trend_norm | 0.1931 | 0.3884 |
| 12 | target_evidence_diversity | 0.1830 | 0.2203 |
| 13 | support_degree_product | 0.1732 | -0.2414 |
| 14 | motif_bonus_norm | 0.1553 | -0.5415 |
| 15 | source_evidence_diversity | 0.1225 | 0.1465 |

### SHAP-based prediction clusters

- **Cluster 0** (n=689, positive rate=0.087): target_recent_support_in_degree=2.029, target_support_in_degree=-1.613, source_recent_support_out_degree=-0.953
- **Cluster 1** (n=624, positive rate=0.082): source_recent_support_out_degree=1.866, source_support_out_degree=-1.386, target_recent_support_in_degree=-1.211
- **Cluster 2** (n=2944, positive rate=0.047): target_recent_support_in_degree=-1.123, source_recent_support_out_degree=-0.822, target_support_in_degree=0.810
- **Cluster 3** (n=440, positive rate=0.136): source_recent_support_out_degree=6.912, source_recent_incident_count=-4.575, source_support_out_degree=-3.965
- **Cluster 4** (n=303, positive rate=0.086): target_recent_support_in_degree=7.046, target_recent_incident_count=-5.288, target_support_in_degree=-4.537

### Top SHAP interactions (feature pairs that co-contribute)

- motif_count × nearby_closure_density: r=1.000
- path_support_norm × hub_penalty: r=-0.996
- source_recent_support_out_degree × source_recent_incident_count: r=-0.985
- source_support_out_degree × source_recent_support_out_degree: r=-0.984
- target_recent_support_in_degree × target_recent_incident_count: r=-0.983
- target_support_in_degree × target_recent_support_in_degree: r=-0.982
- source_support_out_degree × source_recent_incident_count: r=0.954
- target_support_in_degree × target_recent_incident_count: r=0.947
- source_direct_out_degree × source_recent_incident_count: r=-0.945
- source_direct_out_degree × source_recent_support_out_degree: r=0.905

---

## Approach B: Interaction Discovery

### Top pairwise interactions by |correlation|

| Feature 1 | Feature 2 | Interaction r | Main r₁ | Main r₂ | Synergy |
|-----------|-----------|--------------|---------|---------|---------|
| direct_degree_product | pair_evidence_diversity_mean | 0.1933 | 0.2367 | 0.1757 | -0.0435 |
| direct_degree_product | source_evidence_diversity | 0.1820 | 0.2367 | 0.1271 | -0.0547 |
| direct_degree_product | support_age_years | 0.1797 | 0.2367 | 0.1557 | -0.0570 |
| direct_degree_product | target_evidence_diversity | 0.1618 | 0.2367 | 0.1067 | -0.0749 |
| support_degree_product | direct_degree_product | 0.1534 | 0.1745 | 0.2367 | -0.0834 |
| direct_degree_product | pair_mean_stability | 0.1506 | 0.2367 | 0.0893 | -0.0861 |
| cooc_count | pair_evidence_diversity_mean | 0.1486 | 0.1793 | 0.1757 | -0.0307 |
| direct_degree_product | source_mean_stability | 0.1475 | 0.2367 | 0.0650 | -0.0892 |
| direct_degree_product | recent_support_age_years | -0.1409 | 0.2367 | -0.0708 | -0.0958 |
| source_support_out_degree | support_degree_product | 0.1401 | 0.1063 | 0.1745 | -0.0343 |
| source_support_out_degree | direct_degree_product | 0.1391 | 0.1063 | 0.2367 | -0.0976 |
| support_degree_product | pair_evidence_diversity_mean | 0.1371 | 0.1745 | 0.1757 | -0.0386 |
| source_direct_out_degree | support_degree_product | 0.1342 | 0.1354 | 0.1745 | -0.0403 |
| support_degree_product | source_recent_support_out_degree | 0.1341 | 0.1745 | 0.0997 | -0.0403 |
| direct_degree_product | pair_mean_fwci | 0.1320 | 0.2367 | 0.0929 | -0.1047 |

### Top interactions by synergy (above main effects)

- target_recent_support_in_degree × target_recent_incident_count: synergy=0.0039 (interaction_r=0.0522)
- source_recent_support_out_degree × source_recent_incident_count: synergy=-0.0000 (interaction_r=0.1024)
- hub_penalty × target_support_in_degree: synergy=-0.0014 (interaction_r=0.0526)
- hub_penalty × target_recent_support_in_degree: synergy=-0.0022 (interaction_r=0.0497)
- path_support_norm × target_support_in_degree: synergy=-0.0023 (interaction_r=0.0540)
- target_support_in_degree × target_recent_incident_count: synergy=-0.0024 (interaction_r=0.0516)
- source_support_out_degree × source_recent_incident_count: synergy=-0.0035 (interaction_r=0.1028)
- source_support_out_degree × source_recent_support_out_degree: synergy=-0.0053 (interaction_r=0.1010)
- target_support_in_degree × target_recent_support_in_degree: synergy=-0.0056 (interaction_r=0.0484)
- path_support_norm × target_recent_support_in_degree: synergy=-0.0058 (interaction_r=0.0505)

### Top triple interactions

- direct_degree_product × pair_evidence_diversity_mean × source_evidence_diversity: r=0.1942
- direct_degree_product × pair_evidence_diversity_mean × support_age_years: r=0.1884
- direct_degree_product × pair_evidence_diversity_mean × target_evidence_diversity: r=0.1830
- direct_degree_product × support_age_years × source_evidence_diversity: r=0.1793
- pair_evidence_diversity_mean × support_degree_product × source_evidence_diversity: r=0.1740

---

## Approach C: SAE on Reranker Residuals

### Top neurons correlated with residuals (what the linear model misses)

- **Neuron 15** (resid_r=0.3691): gap_bonus=nan, mediator_count=nan, field_same_group=nan, pos_rate_when_active=0.018
- **Neuron 57** (resid_r=0.2506): gap_bonus=nan, mediator_count=nan, field_same_group=nan, pos_rate_when_active=0.024
- **Neuron 10** (resid_r=-0.1845): gap_bonus=nan, mediator_count=nan, field_same_group=nan, pos_rate_when_active=0.157
- **Neuron 29** (resid_r=-0.1803): gap_bonus=nan, mediator_count=nan, field_same_group=nan, pos_rate_when_active=0.125
- **Neuron 123** (resid_r=0.1771): gap_bonus=nan, mediator_count=nan, field_same_group=nan, pos_rate_when_active=0.026
- **Neuron 56** (resid_r=0.1692): gap_bonus=nan, mediator_count=nan, cooc_count=-0.21, pos_rate_when_active=0.024
- **Neuron 114** (resid_r=-0.1602): gap_bonus=nan, mediator_count=nan, field_same_group=nan, pos_rate_when_active=0.198
- **Neuron 86** (resid_r=-0.1415): gap_bonus=nan, mediator_count=nan, field_same_group=nan, pos_rate_when_active=0.118
- **Neuron 42** (resid_r=-0.1305): gap_bonus=nan, mediator_count=nan, field_same_group=nan, pos_rate_when_active=0.054
- **Neuron 99** (resid_r=-0.1247): gap_bonus=nan, mediator_count=nan, cooc_count=0.80, pos_rate_when_active=0.150

---

## Approach D: Enriched HypotheSAEs (graph-feature text)

### Hypothesis 1 (r=0.132, top-10 positive rate=0.20)

Hypothesis: Candidate research connections that strongly activate neuron 53 are characterized by dense co-occurrence of concepts, gap-like graph structures with zero or near-zero path support and maximal gap values, consistently high evidence diversity and stability, high or moderate to high impact (FWCI typically above 4.8), and very recent support (within the last 1-2 years); in contrast, low-activation connections exhibit sparser co-occurrence, similarly gap-like but generally less dense structures, older recency (often 4+ years ago), and while evidence diversity and impact can remain moderate to high, these factors alone without density and recency correspond to low neuron activation.

### Hypothesis 2 (r=-0.098, top-10 positive rate=0.00)

Hypothesis: Candidate research connections that strongly activate neuron 4 are characterized by dense co-occurrence but consistently exhibit a "gap-like" graph structure with very low or zero path support (near 0.00), moderate evidence diversity, moderate impact metrics, and recent but not immediate last support timestamps, whereas low-activation connections, despite also being dense, have higher path support values allowing numerous motifs (indicating more complete connecting paths), generally higher or more variable impact, similar or slightly higher evidence diversity, and more varied recency patterns; thus, neuron 4 activation is driven by candidate pairs that form structurally sparse but densely co-occurring, stable, moderate-impact "gap-like" patterns with low path connectivity.

### Hypothesis 3 (r=0.077, top-10 positive rate=0.00)

Hypothesis: Candidate research connections that strongly activate neuron 66 tend to exhibit a dense co-occurrence pattern combined with a gap-like graph structure characterized by a high number of motifs and a maximal gap value (gap=1.00), along with high evidence diversity and moderate impact, and generally more recent or ongoing support; in contrast, low-activation examples correspond to sparser or moderate co-occurrences with fewer motifs despite also having a gap-like structure, and although they may have comparable or higher impact and diversity, they show less consistent recent support and lower node degree product values—thus, dense co-occurrence and rich motif connectivity within a gap-like structure coupled with sustained diverse evidence and recent activity distinguish high-activation from low-activation cases.

### Hypothesis 4 (r=-0.069, top-10 positive rate=0.00)

Hypothesis: Candidate research connections that strongly activate neuron 98 tend to have sparse co-occurrence with very low or zero path support and few motifs, forming clear "gap-like" structures with maximum gap values (around 1.00), coupled with high evidence diversity but moderate to low impact and generally older or less recent support; whereas connections with low neuron 98 activation show denser or moderate co-occurrence, higher path support, many motifs, and greater popularity (high directed and support degree products), with similarly high evidence diversity but moderate impact and more recent support. Thus, neuron 98 activation is primarily driven by sparse, structurally minimal "gap" patterns in low-popularity, high-diversity, moderate-impact, and variably recent candidate pairs.

### Hypothesis 5 (r=0.069, top-10 positive rate=0.10)

Hypothesis: Research connection pairs that strongly activate neuron 117 tend to exhibit a gap-like graph structure characterized by zero or near-zero path support and a high number of motifs that suggest structural holes (gaps), combined with moderate to dense co-occurrence (at least moderate number of papers), high evidence diversity (diversity ≥ 10), generally higher impact metrics (FWCI often above 4, frequently above 6), and relatively recent or ongoing support, whereas low-activation pairs display similar gap-like structures but with sparser co-occurrence, lower directed and support degree products, and less recent support, resulting in weaker overall impact and stability signals.

### Hypothesis 6 (r=0.065, top-10 positive rate=0.10)

Hypothesis: Candidate research connections that strongly activate neuron 55 tend to exhibit moderate co-occurrence density coupled with a predominately gap-like structural pattern characterized by zero path support but multiple motifs, consistently high evidence diversity and stability, moderate FWCI impact, and very recent or ongoing support; in contrast, low-activation connections often have either sparser or denser co-occurrence but less motif richness, lower directed degree product (popularity) variance, similarly high diversity but slightly older recency, and do not combine these features into the same structural signature.

### Hypothesis 7 (r=-0.063, top-10 positive rate=0.00)

Hypothesis: Candidate research connections that strongly activate neuron 95 tend to exhibit a graph-structural pattern characterized by sparse to moderate co-occurrence density combined with a strictly gap-like structure having zero path support (path_support = 0.00) and fewer motifs, along with high but not maximal diversity scores and generally low to moderate impact (FWCI), often with recent support (within 1-3 years). In contrast, connections associated with low neuron 95 activation show higher co-occurrence densities (often dense), retain the gap-like structure but with substantial path support (path_support > 0), more numerous motifs, higher directed and support degree products indicating greater popularity, higher diversity and impact metrics, and varying recency that is less tightly concentrated.

### Hypothesis 8 (r=-0.062, top-10 positive rate=0.10)

Hypothesis: High-activation examples are characterized by sparse to moderate co-occurrence with strictly gap-like structures exhibiting very low or zero path support and low motif counts, combined with consistently high evidence diversity, high impact (FWCI), and recent last support (typically within 1-3 years). In contrast, low-activation examples tend to show dense co-occurrence with gap-like structures that have maximal path support and high motif counts, paired with moderate to low impact and less recent support, despite also having relatively high evidence diversity. Thus, the presence of sparse or moderate co-occurrence and low path support gap-like structures, together with recent and high-impact evidence diversity, distinguishes high-activation patterns from low-activation ones.

### Hypothesis 9 (r=0.059, top-10 positive rate=0.10)

Hypothesis: Candidate research connections that strongly activate neuron 57 are characterized by dense co-occurrence patterns with consistently gap-like, motif-rich structures where the directed and support degree products are very high, accompanied by high-diversity and stable evidence, moderate to high impact (FWCI), and recent or ongoing scholarly attention; in contrast, low-activation connections show sparse to moderate co-occurrence with fewer motifs, lower degree products, and older or less recent support, despite similarly high evidence diversity and moderate impact.

### Hypothesis 10 (r=-0.056, top-10 positive rate=0.10)

Hypothesis: Research connection pairs that strongly activate neuron 49 tend to exhibit moderate co-occurrence densities with a predominantly gap-like graph structure characterized by low path support, numerous motifs, and a maximum gap of 1.0, coupled with high diversity and stability in evidence and relatively high impact (FWCI frequently above 4), and recent last support (generally within the last 1–3 years). In contrast, low-activation pairs tend to show higher co-occurrence densities (dense connections), similarly gap-like structures but with substantially higher path support values and many more motifs, higher popularity measures, comparable evidence diversity but somewhat lower or moderate impact values, and similarly recent but slightly less consistently recent last support. Thus, the key distinguishing graph-structural pattern is that high-activation pairs have moderate co-occurrence and low path support indicative of sparser or less direct connection paths within densely connected motifs (gap-rich but path-poor), whereas low-activation pairs are more densely co-occurring with stronger path support indicating more established and well-integrated connections.

