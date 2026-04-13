# Family Candidate Review

This note records the reviewed seed layer plus the reusable candidate-family queue.

## Design rule

Active family membership still comes only from reviewed seeds.
Candidate families are a reusable review queue, not live ontology membership.

## Active reviewed seeds

- `innovation and technology concepts` | type `outcome_family` | members `6`  
  Members: digital economy, digital economy development, digital transformation, innovation level, technological innovation, technological progress
- `macro cycle and price concepts` | type `outcome_family` | members `6`  
  Members: house prices, inflation, output growth, price changes, rate of growth, state of the business cycle
- `environmental outcomes` | type `outcome_family` | members `5`  
  Members: CO2 emissions, ecological footprint, environmental degradation, environmental pollution, environmental quality
- `structural transformation and urbanization concepts` | type `outcome_family` | members `3`  
  Members: industrial structure, industrial structure upgrading, urbanization
- `trade flow and openness concepts` | type `outcome_family` | members `3`  
  Members: exports, imports, trade openness
- `uncertainty and risk concepts` | type `mechanism_family` | members `2`  
  Members: uncertainty, uncertainty measures

## What the candidate generator uses

- semantic overlap across preferred labels and aliases
- bucket-hint / bucket-profile similarity
- shortlist partner overlap
- co-mentions across internal review notes

## Top candidate families

- `environment climate concepts` | type `outcome_family` | members `6` | semantic `0.38` | collision `0.25` | combined `0.33`  
  Members: energy consumption, energy intensity, environmental regulation, green innovation, renewable energy, renewable energy consumption
- `labor income demand concepts` | type `outcome_family` | members `3` | semantic `0.16` | collision `0.19` | combined `0.17`  
  Members: income distribution, income inequality, willingness to pay (WTP)
