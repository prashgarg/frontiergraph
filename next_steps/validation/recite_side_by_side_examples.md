# ReCITE Side-by-Side Examples

Date: 2026-04-01

This note puts three ReCITE papers side by side with FrontierGraph's extracted graph so we can see what the mismatch actually looks like.

The three examples cover:

1. a semantically alignable paper
2. a node-alignable but edge-misaligned paper
3. an abstract-insufficient paper

## 1. Semantically alignable paper

### Paper

`203`  
*A Review of Agricultural Technology Transfer in Africa: Lessons from Japan and China Case Projects in Tanzania and Kenya*

### ReCITE gold graph: sample edges

- Autonomy, self-reliance and utilization of local resources -> Sustainability of agricultural technical cooperation projects
- Sustainability of agricultural technical cooperation projects -> Autonomy, self-reliance and utilization of local resources
- Autonomy, self-reliance and utilization of local resources -> Perceived benefits of transferred technology in local community
- Perceived benefits of transferred technology in local community -> Sustainability of agricultural technical cooperation projects
- Operating project environment -> Autonomy, self-reliance and utilization of local resources
- Operating project environment -> Stakeholders linkages, supports and commitment
- Stakeholders linkages, supports and commitment -> Operating project environment

### FrontierGraph extracted graph: sample edges

- Agricultural technology transfer -> Agricultural productivity / farm production
- Agricultural technology transfer -> Effectiveness and sustainability challenges
- Agricultural technology transfer -> Responsiveness to local demand
- Japanese agricultural technical cooperation (SHEP, RIDS) -> Agricultural productivity / farm production
- Chinese agricultural technical cooperation (ATDC) -> Agricultural productivity / farm production
- Stakeholder linkages, commitment, and participation -> Project sustainability in recipient countries
- Beneficiary autonomy (knowledge and capacity of production) -> Agricultural technology transfer
- Local government policy and institutional frameworks -> Agricultural technology transfer

### What we learn

This is a good example of real semantic overlap despite low exact metrics.

Strong alignments include:
- `Agricultural technology transfer`
- `Agricultural productivity`
- `Stakeholder linkages / commitment`
- `Project sustainability`
- `Beneficiary autonomy`

The main difference is graph style:
- ReCITE uses a tighter causal-loop or CLD-like variable graph
- FrontierGraph uses a paper-summary mechanism graph

This is not a "wrong extraction" case. It is a **graph-object mismatch with recoverable semantic overlap**.

## 2. Node-alignable but edge-misaligned paper

### Paper

`258`  
*The Sustainable Development of the Economic-Energy-Environment (3E) System under the Carbon Trading (CT) Mechanism: A Chinese Case*

### ReCITE gold graph: sample edges

- GDP -> Energy investment
- GDP -> Energy consumption
- GDP -> Fixed assets investment
- GDP -> Industrial profits
- GDP -> Environmental investment
- Energy consumption -> CO2 emissions
- Energy consumption -> Energy gap
- Energy gap -> Energy policies
- Energy policies -> Energy intensity
- Energy intensity -> Energy consumption
- Environmental investment -> CO2 emissions
- CO2 emissions -> Environmental governance costs

### FrontierGraph extracted graph: sample edges

- Carbon trading (CT) mechanism -> Energy consumption
- Carbon trading (CT) mechanism -> CO2 emissions
- Carbon trading (CT) mechanism -> Gross domestic product (GDP)
- Total quota (CT) -> CO2 emissions
- Free quota (CT) -> CO2 emissions
- Carbon trading price (CT price) -> CO2 emissions
- CO2 emissions -> Sustainable development of the 3E system
- Carbon trading (CT) mechanism -> Sustainable development of the 3E system
- 3E system simulation model (system dynamics) -> Carbon trading (CT) mechanism

### What we learn

This is the clearest example where node overlap is much better than edge overlap.

Semantically, many nodes line up very well:
- `GDP`
- `Energy consumption`
- `CO2 emissions`
- `Total quota`
- `Free quota amount`
- `CT price`

But the edge structure differs because:
- ReCITE preserves the more decomposed internal mechanism graph
- FrontierGraph summarizes the paper around the policy mechanism and higher-level system outcomes

So this is a **same-topic but different-resolution** case.

## 3. Abstract-insufficient paper

### Paper

`90`  
*Hydropolitical System Archetypes: Feedback Structures, Physical Environments, Unintended Behaviors, and a Diagnostic Checklist*

### ReCITE gold graph: sample edges

- The US's water-based development -> The US's unilateral water capturing
- The US's unilateral water capturing -> Water flowing to the US than the DS
- Water flowing to the US than the DS -> The US's water-based development
- Water flowing to the US than the DS -> The DS's water-based development
- The DS's water-based development -> The DS's unilateral water capturing
- The DS's unilateral water capturing -> Water flowing to the US than the DS

### FrontierGraph extracted graph: sample edges

- System structure -> Hydropolitical behavior (patterns over time)
- System archetypes (hydropolitical) -> Feedback loop structures
- System archetypes (hydropolitical) -> Required physical environments
- System archetypes (hydropolitical) -> Unintended behaviors
- System thinking / system dynamics approach -> Hydropolitics (study of conflict and cooperation)
- Diagnostic checklist -> Riparian states' recognition of behavior patterns
- System archetypes (hydropolitical) -> Projecting plausible hydropolitical behaviors / understanding past behaviors
- Hydropolitics (study of conflict and cooperation) -> Transboundary water basin

### What we learn

This is not really a fair abstract-level comparison.

The ReCITE gold graph is a specific archetype loop with five low-level loop variables. The abstract does not present those five variables directly. It talks instead about:
- hydropolitics
- system archetypes
- feedback structures
- unintended behaviors
- a diagnostic checklist

That is exactly what FrontierGraph extracts.

So here the correct judgment is not "bad extraction."
It is:
- **gold graph not recoverable from title + abstract alone**

## Bottom line

These ReCITE examples point to three different cases:

1. **Semantically comparable but differently framed**
2. **Node-alignable but edge-resolution mismatch**
3. **Abstract-insufficient for the gold graph**

That means ontology is a large part of the issue, but not only in the narrow label-matching sense.

The deeper issues are:
- graph object
- abstraction level
- whether the benchmark target is truly recoverable from title + abstract
