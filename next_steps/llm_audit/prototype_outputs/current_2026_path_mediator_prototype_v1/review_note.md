# Internal Path/Mediator Prototype Review

## Route counts and shares

- `promote_path_question`: 81 (67.5%)
- `downrank_path_question`: 29 (24.2%)
- `promote_mediator_question`: 7 (5.8%)
- `downrank_mediator_question`: 2 (1.7%)
- `keep_direct_edge`: 1 (0.8%)

## Top 10 promoted path questions

- `FG3C000246__FG3C004338`: Through which nearby pathways might international trade (trade flows) shape green growth?  
  Before: How might international trade (trade flows) change green growth?
- `FG3C000028__FG3C004458`: Through which nearby pathways might high-frequency trading shape prices?  
  Before: How might high-frequency trading change prices?
- `FG3C000015__FG3C001452`: Through which nearby pathways might foreign direct investments shape catastrophic health expenditures?  
  Before: How might foreign direct investments change catastrophic health expenditures?
- `FG3C000247__FG3C004458`: Through which nearby pathways might high-frequency trading shape cost of capital?  
  Before: How might high-frequency trading change cost of capital?
- `FG3C000013__FG3C002623`: Through which nearby pathways might U.S. economic policy uncertainty shape technological innovation?  
  Before: How might U.S. economic policy uncertainty change technological innovation?
- `FG3C000061__FG3C000425`: Through which nearby pathways might digital inclusive finance shape total factor productivity (TFP)?  
  Before: How might digital inclusive finance change total factor productivity (TFP)?
- `FG3C000015__FG3C000176`: Through which nearby pathways might foreign direct investments shape real wages?  
  Before: How might foreign direct investments change real wages?
- `FG3C000132__FG3C002438`: Through which nearby pathways might Special economic zones shape inequality?  
  Before: How might Special economic zones change inequality?
- `FG3C000100__FG3C004458`: Through which nearby pathways might high-frequency trading shape investor sentiment?  
  Before: How might high-frequency trading change investor sentiment?
- `FG3C000089__FG3C000215`: Through which nearby pathways might R&D investment shape green total factor productivity (GTFP)?  
  Before: How might R&D investment change green total factor productivity (GTFP)?

## Top 5 promoted mediator questions

- `FG3C000015__FG3C000271`: Which nearby mechanisms most plausibly link foreign direct investments to life expectancy?  
  Before: How might foreign direct investments change life expectancy?
- `FG3C000004__FG3C005928`: Which nearby mechanisms most plausibly link negative news sentiment to welfare?  
  Before: How might negative news sentiment change welfare?
- `FG3C000039__FG3C001452`: Which nearby mechanisms most plausibly link globalization to catastrophic health expenditures?  
  Before: How might globalization change catastrophic health expenditures?
- `FG3C002438__FG3C006191`: Which nearby mechanisms most plausibly link Special economic zones to land rents?  
  Before: How might Special economic zones change land rents?
- `FG3C002487__FG3C005256`: Which nearby mechanisms most plausibly link free trade agreements to welfare level?  
  Before: How might free trade agreements change welfare level?

## Rare direct-edge case

- `FG3C000159__FG3C005155`: How might monetary policy shocks change cyclical component?
  Why: monetary policy shocks and cyclical component are already linked by 3 nearby intermediate topics.

## Side-by-side examples

### FG3C000246__FG3C004338
- Route: `promote_path_question`
- Before: How might international trade (trade flows) change green growth?
- After: Through which nearby pathways might international trade (trade flows) shape green growth?
- Why: Nearby papers already suggest routes through trade openness, energy consumption, and export diversification.
- First step: Start with a short synthesis or pilot that follows the nearest mediating topics.

### FG3C000028__FG3C004458
- Route: `promote_path_question`
- Before: How might high-frequency trading change prices?
- After: Through which nearby pathways might high-frequency trading shape prices?
- Why: Nearby papers already suggest routes through liquidity, volatility, and adverse selection.
- First step: Start with a short synthesis or pilot that follows the nearest mediating topics.

### FG3C000015__FG3C001452
- Route: `promote_path_question`
- Before: How might foreign direct investments change catastrophic health expenditures?
- After: Through which nearby pathways might foreign direct investments shape catastrophic health expenditures?
- Why: Nearby papers already suggest routes through income inequality and poverty.
- First step: Start with a short synthesis or pilot that follows the nearest mediating topics.

### FG3C000053__FG3C002799
- Route: `downrank_path_question`
- Before: How might renewable portfolio standards change green innovation?
- After: Through which nearby pathways might renewable portfolio standards shape green innovation?
- Why: Nearby papers already suggest routes through carbon emissions, carbon emissions trading, and green bonds.
- First step: Treat this as a lower-priority path question unless stronger local support appears.

### FG3C000015__FG3C000271
- Route: `promote_mediator_question`
- Before: How might foreign direct investments change life expectancy?
- After: Which nearby mechanisms most plausibly link foreign direct investments to life expectancy?
- Why: The main open question is which channel does the work: CO2 emissions, carbon emissions, and renewable energy consumption.
- First step: Start by testing which nearby channel carries the effect.

### FG3C000159__FG3C005155
- Route: `keep_direct_edge`
- Before: How might monetary policy shocks change cyclical component?
- After: How might monetary policy shocks change cyclical component?
- Why: monetary policy shocks and cyclical component are already linked by 3 nearby intermediate topics.
- First step: A short synthesis or pilot design looks like the sensible first move.
