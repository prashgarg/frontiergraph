# Flexible Endpoint Guardrail

This note adds a second-stage guardrail over the `study_subfamily_candidate` regime so that multi-cluster structure does not automatically become ontology growth.

## Endpoint Guardrail Counts

- `substantive_family_candidate`: `26`
- `generic_behavior_or_theory_container`: `13`
- `method_or_measurement_container`: `7`
- `contextual_bucket`: `6`

## Significant Cluster Guardrail Counts

- `substantive_child_candidate`: `56`
- `contextual_cluster`: `21`
- `method_or_measurement_cluster`: `16`
- `generic_modifier_cluster`: `9`
- `alias_or_surface_cluster`: `2`

## Child Promotion Results

- promoted or attached child clusters: `33`
- new child families to add: `32`
- existing ontology child attachments: `1`
- distinct parent endpoints with promoted children: `20`

## Examples

- `Political risk` -> `geopolitical risk` | attach_existing_ontology_child | freq=167 share=0.346 | candidate child label already exists in the ontology and can be used directly
- `Inflation` -> `expected inflation` | promote_new_child_family | freq=498 share=0.565 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Consumption` -> `consumption growth` | promote_new_child_family | freq=432 share=0.346 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Government debt` -> `public debt` | promote_new_child_family | freq=359 share=0.526 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `real gross domestic product growth rate` -> `economic growth rate` | promote_new_child_family | freq=279 share=0.487 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Electricity demand` -> `electricity consumption` | promote_new_child_family | freq=200 share=0.385 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Environmental Degradation` -> `greenhouse gas emissions` | promote_new_child_family | freq=196 share=0.415 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Environmental Degradation` -> `environmental pressure` | promote_new_child_family | freq=191 share=0.405 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Market concentration` -> `hospital market concentration` | promote_new_child_family | freq=164 share=0.299 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `New Firms` -> `entry of new firms` | promote_new_child_family | freq=149 share=0.284 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Interest rate` -> `market interest rates` | promote_new_child_family | freq=147 share=0.304 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Stock Market` -> `us stock market` | promote_new_child_family | freq=141 share=0.296 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Natural gas prices` -> `natural gas price volatility` | promote_new_child_family | freq=134 share=0.282 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Financial inclusion` -> `digital financial inclusion` | promote_new_child_family | freq=132 share=0.343 | cluster is substantively narrower and has enough support to justify a guarded child concept
- `Consumption` -> `coal consumption` | promote_new_child_family | freq=124 share=0.099 | cluster is substantively narrower and has enough support to justify a guarded child concept
