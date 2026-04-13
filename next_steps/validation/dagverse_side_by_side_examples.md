# DAGverse Side-by-Side Examples

Date: 2026-04-01

This note puts three DAGverse papers side by side with FrontierGraph's extracted graph so we can see where the mismatch is coming from.

The main takeaway is that there are at least three different mismatch modes:

1. **Comparable semantic graph**
2. **Ontology / abstraction-level mismatch**
3. **Symbolic variable graph vs semantic graph**

## 1. Comparable semantic graph

### Paper

`arxiv_2208_04144_0`  
*An Urban Population Health Observatory for Disease Causal Pathway Analysis and Decision Support*

### DAGverse gold graph: sample edges

- Lack of Physical Activity -> Obesity Prevalence
- Poverty -> Obesity Prevalence
- Unemployment -> Obesity Prevalence
- Without High School Diploma -> Obesity Prevalence
- % Black population -> Obesity Prevalence
- Low income > 0.5 mile from supermarket -> Obesity Prevalence
- Obesity Prevalence -> Diabetes
- Memphis population -> Lack of Physical Activity
- Memphis population -> Poverty
- Memphis population -> Unemployment

### FrontierGraph extracted graph: sample edges

- Urban Population Health Observatory (UPHO) -> semantics layer / knowledge graph
- Urban Population Health Observatory (UPHO) -> machine learning and semantic/logical inference approach
- machine learning and semantic/logical inference approach -> pathways leading to diseases (disease causal pathways)
- CDC 500 Cities data set -> support vector regression model
- poverty -> obesity prevalence
- lack of physical activity -> obesity prevalence
- education (socioenvironmental determinant) -> obesity prevalence
- unemployment -> obesity prevalence
- Urban Population Health Observatory (UPHO) -> dashboard prototype (UPHO)
- clinical case scenarios -> dashboard prototype (UPHO)

### What we learn

This is the cleanest example where the two graph objects are genuinely comparable.

There is real overlap at the causal-variable level:
- `Poverty -> Obesity Prevalence`
- `Lack of Physical Activity -> Obesity Prevalence`
- `Unemployment -> Obesity Prevalence`

The main difference is that FrontierGraph also pulls in:
- system-level nodes
- dataset nodes
- method nodes
- interface or decision-support nodes

So this is not a pure failure. It is closer to a **superset semantic graph** built from the abstract.

## 2. Ontology / abstraction-level mismatch

### Paper

`arxiv_2205_01057_0`  
*Causal Discovery on the Effect of Antipsychotic Drugs on Delirium Patients in the ICU using Large EHR Dataset*

### DAGverse gold graph: sample edges

- airway obstruction -> chronic obstructive pulmonary disease
- prior mechanical ventilation count -> mechanical ventilation (indicator)
- patient race -> mechanical ventilation (indicator)
- time to initiation of mechanical ventilation -> duration on mechanical ventilation
- mechanical ventilation (indicator) -> duration on mechanical ventilation
- duration on mechanical ventilation -> length of stay in hospital (days)
- surgical procedure -> length of stay in hospital (days)
- antipsychotic drug group -> length of stay in hospital (days)
- antipsychotic drug group -> in-hospital death
- antipsychotic drug group -> mortality timeline (30/90/365 days, survived>1y)

### FrontierGraph extracted graph: sample edges

- Haloperidol drug group -> Length-of-stay (mean and max)
- Haloperidol drug group -> One-year mortality
- Antipsychotic drugs (APD) treatment -> Length-of-stay (mean and max)
- Antipsychotic drugs (APD) treatment -> One-year mortality
- MIMIC III EHR dataset -> Retrospective cohort / exploratory ML and causal analysis
- Retrospective cohort / exploratory ML and causal analysis -> Causal model / causal discovery
- Causal model / causal discovery -> Covariates correlated with delirium

### What we learn

This is the kind of example that makes the ontology issue obvious.

DAGverse is mostly preserving a more detailed variable DAG:
- ventilation variables
- severity scores
- surgery
- demographic covariates
- multiple mortality endpoints

FrontierGraph instead extracts the higher-level paper-summary structure:
- treatment groups
- outcome summaries
- dataset
- analysis design
- causal-discovery framing

There is still semantic overlap:
- `antipsychotic drug group -> length of stay`
- `antipsychotic drug group -> mortality`

But the graph object is not the same. FrontierGraph is compressing the paper into a more interpretable research-summary graph, while DAGverse is staying much closer to the internal variable DAG.

## 3. Symbolic variable graph vs semantic graph

### Paper

`arxiv_2303_04339_0`  
*Learning the Finer Things: Bayesian Structure Learning at the Instantiation Level*

### DAGverse gold graph: sample edges

- A state a1 -> B state b1
- A state a1 -> B state b2
- A state a1 -> B state b3
- A state a2 -> B state b2
- C state c1 -> B state b2
- C state c2 -> B state b2
- B state b2 -> D state d1
- B state b2 -> D state d2
- D state d2 -> C state c3

### FrontierGraph extracted graph: sample edges

- probabilistic graphical model structure learning approach -> random variable instantiation level operation
- Minimum Description Length (MDL) decomposition over training exemplars -> final knowledge base
- minimal entropy inferences -> final knowledge base
- Bayesian Knowledge Bases (BKBs) -> random variable instantiation level operation
- Bayesian Knowledge Bases (BKBs) -> Bayesian Networks (BNs)
- MDL score and structure learning algorithm -> learned BNs on 40 benchmark datasets
- MDL score and structure learning algorithm -> off-the-shelf DAG learning techniques
- off-the-shelf DAG learning techniques -> final knowledge base
- probabilistic graphical model structure learning approach -> gene regulatory networks learned from breast cancer gene mutational data (TCGA)

### What we learn

Here the mismatch is not just ontology. It is the graph object itself.

DAGverse gold graph:
- is symbolic
- is instantiation-level
- uses state variables as nodes

FrontierGraph graph:
- is semantic
- is paper-summary oriented
- uses method, benchmark, and application concepts

So exact or alias-based overlap is close to meaningless here. This is not because FrontierGraph extracted nonsense. It is because the two systems are answering different questions about the same paper.

## Bottom line

These examples suggest:

- some DAGverse papers are fair external validation targets for FrontierGraph
- some are only partially fair because of abstraction-level compression
- some are not fair targets at all unless we build a second prompt that explicitly aims to recover variable-level or symbolic DAGs

So yes, a lot of what we are seeing is ontology-related, but it is not just ontology in the narrow sense of label normalization.

It is also:
- graph-object choice
- abstraction level
- whether the target graph is meant to summarize the paper or reproduce a figure-level variable DAG
