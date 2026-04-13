# Ontology v2.1 Promotion Note

This pass promotes a conservative subset of reviewed round-3 new-family proposals into ontology v2.1.

Promotion rule:
- start from `propose_new_concept_family` rows in the round-3 reviewed overlay
- collapse by normalized family label
- exclude exact label overlaps already present in base ontology v2
- promote only families with either `row_support >= 2`, `freq_support >= 50`, or an explicit hard-case/manual reviewed source

- base ontology size: `153,800`
- promoted family candidates considered: `13,739`
- promoted family nodes added: `767`
- ontology v2.1 size: `154,567`

## Mapping actions in v2.1
- `carry_forward_base_mapping`: `1,349,818`
- `attach_existing_broad`: `21,725`
- `unpromoted_family`: `12,972`
- `add_alias_to_existing`: `2,354`
- `promoted_family`: `1,265`
- `keep_unresolved`: `932`
- `reject_cluster`: `841`

## Top promoted families
- `Financial Constraints`: row_support=14, freq_support=309, domain=`econ_core`, sources=`["cluster_review", "remaining_row_majority_review"]`
- `Profitability`: row_support=2, freq_support=279, domain=`econ_applied`, sources=`["remaining_row_majority_review"]`
- `industrial structure upgrading`: row_support=2, freq_support=277, domain=`econ_core`, sources=`["remaining_row_majority_review", "row_review"]`
- `Characteristics`: row_support=32, freq_support=261, domain=`econ_core`, sources=`["cluster_review", "row_review"]`
- `Economic Fundamentals`: row_support=11, freq_support=206, domain=`econ_core`, sources=`["cluster_review", "row_review"]`
- `persistence`: row_support=11, freq_support=184, domain=`econ_core`, sources=`["cluster_review", "remaining_row_majority_review"]`
- `technology`: row_support=2, freq_support=181, domain=`econ_core`, sources=`["remaining_hard_modal_review", "row_review"]`
- `Profits`: row_support=1, freq_support=158, domain=`econ_core`, sources=`["remaining_row_majority_review"]`
- `Market and financial conditions`: row_support=6, freq_support=157, domain=`finance`, sources=`["cluster_review"]`
- `labor`: row_support=1, freq_support=156, domain=`econ_core`, sources=`["row_review"]`
- `access to care`: row_support=3, freq_support=154, domain=`other_valid`, sources=`["remaining_row_majority_review", "row_review"]`
- `Climate policy uncertainty`: row_support=6, freq_support=150, domain=`econ_core`, sources=`["cluster_review", "row_review"]`
- `returns`: row_support=1, freq_support=119, domain=`econ_core`, sources=`["row_review"]`
- `financial frictions`: row_support=1, freq_support=106, domain=`health`, sources=`["row_review"]`
- `Bank profitability`: row_support=1, freq_support=100, domain=`econ_core`, sources=`["remaining_row_majority_review"]`
- `inflation volatility`: row_support=1, freq_support=95, domain=`other_valid`, sources=`["row_review"]`
- `Dependence structures and dependency relations`: row_support=12, freq_support=93, domain=`econ_core`, sources=`["cluster_review"]`
- `Usual source of care`: row_support=6, freq_support=91, domain=`health`, sources=`["cluster_review", "remaining_row_majority_review"]`
- `Institutional Quality`: row_support=8, freq_support=90, domain=`econ_core`, sources=`["cluster_review"]`
- `Asset price bubbles`: row_support=7, freq_support=88, domain=`finance`, sources=`["cluster_review", "row_review"]`
- `Bitcoin market outcomes`: row_support=5, freq_support=88, domain=`finance`, sources=`["cluster_review"]`
- `Dynamics measures`: row_support=8, freq_support=86, domain=`econ_core`, sources=`["cluster_review"]`
- `Carbon emission efficiency`: row_support=2, freq_support=86, domain=`environment`, sources=`["remaining_row_majority_review", "row_review"]`
- `economic factors`: row_support=1, freq_support=86, domain=`econ_core`, sources=`["row_review"]`
- `monetary shocks`: row_support=1, freq_support=86, domain=`econ_core`, sources=`["row_review"]`
- `Extensive and intensive margins`: row_support=6, freq_support=85, domain=`econ_applied`, sources=`["cluster_review"]`
- `digital inclusive finance`: row_support=1, freq_support=77, domain=`other_valid`, sources=`["row_review"]`
- `Trading activity`: row_support=1, freq_support=75, domain=`other_valid`, sources=`["row_review"]`
- `Time-varying risk and premia`: row_support=9, freq_support=74, domain=`econ_core`, sources=`["cluster_review"]`
- `Oil rents`: row_support=1, freq_support=74, domain=`econ_core`, sources=`["row_review"]`
- `Skill premium`: row_support=5, freq_support=73, domain=`econ_core`, sources=`["remaining_row_majority_review", "row_review"]`
- `Chinese stock market`: row_support=2, freq_support=72, domain=`finance`, sources=`["remaining_hard_modal_review", "remaining_row_majority_review"]`
- `Market quality`: row_support=1, freq_support=70, domain=`other_valid`, sources=`["row_review"]`
- `Firm characteristics`: row_support=1, freq_support=68, domain=`econ_core`, sources=`["row_review"]`
- `short-sale constraints`: row_support=4, freq_support=67, domain=`finance`, sources=`["cluster_review"]`
- `complexity across domains`: row_support=8, freq_support=66, domain=`econ_core`, sources=`["cluster_review"]`
- `Household size`: row_support=1, freq_support=64, domain=`econ_core`, sources=`["remaining_row_majority_review"]`
- `Earnings announcements`: row_support=5, freq_support=63, domain=`finance`, sources=`["cluster_review"]`
- `Per capita CO2 emissions`: row_support=1, freq_support=63, domain=`other_valid`, sources=`["remaining_row_majority_review"]`
- `Economic sentiment`: row_support=8, freq_support=62, domain=`other_valid`, sources=`["cluster_review"]`
