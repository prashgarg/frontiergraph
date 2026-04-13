# Grounding Rescue Audit v2

This is the first open-world grounding rescue pass for ontology v2.

Key design choices:
- raw extracted labels are always preserved
- broader grounding is acceptable
- low-score labels are not silently deleted
- clustering backend in this no-spend pass: `tfidf_char_fallback`
- clustering universe mode: `audit_top_truncated`
- clustered labels in this pass: `10,000`

## broader_concept_available

- `renewable energy consumption` | freq `1027` | papers `1027` | score `0.732` | rank-1 `Renewable Energy` | proposal `Renewable Energy`
- `carbon emissions` | freq `845` | papers `845` | score `0.690` | rank-1 `Carbon emission trading` | proposal `Emissions`
- `trade openness` | freq `850` | papers `850` | score `0.714` | rank-1 `Trade Liberalization` | proposal `Openness`
- `gdp per capita` | freq `342` | papers `342` | score `0.708` | rank-1 `GDP` | proposal `GDP`
- `economic policy uncertainty (epu)` | freq `280` | papers `280` | score `0.654` | rank-1 `Policy uncertainty` | proposal `Policy uncertainty`
- `economic policy uncertainty` | freq `297` | papers `297` | score `0.723` | rank-1 `Policy uncertainty` | proposal `Policy uncertainty`
- `firm productivity` | freq `254` | papers `254` | score `0.686` | rank-1 `Work productivity` | proposal `Productivity`
- `exchange rate volatility` | freq `209` | papers `209` | score `0.694` | rank-1 `Exchange-rate flexibility` | proposal `Exchange Rate`
- `monte carlo experiments` | freq `198` | papers `198` | score `0.687` | rank-1 `Monte Carlo` | proposal `Monte Carlo`
- `stock market returns` | freq `151` | papers `151` | score `0.732` | rank-1 `Stock Returns` | proposal `Stock Returns`
- `non-renewable energy consumption` | freq `154` | papers `154` | score `0.724` | rank-1 `Non-renewable resource` | proposal `Energy Consumption`
- `simulation study` | freq `175` | papers `175` | score `0.708` | rank-1 `Simulation.` | proposal `Simulation.`
- `green total factor productivity (gtfp)` | freq `118` | papers `118` | score `0.668` | rank-1 `Total factor productivity` | proposal `Total factor productivity`
- `price volatility` | freq `141` | papers `141` | score `0.746` | rank-1 `Volatility risk` | proposal `Volatility (finance)`
- `industrial agglomeration` | freq `126` | papers `126` | score `0.741` | rank-1 `Agglomeration` | proposal `Agglomeration`
- `firm value` | freq `128` | papers `128` | score `0.629` | rank-1 `Value of Firm.` | proposal `Value.`
- `future stock returns` | freq `117` | papers `117` | score `0.715` | rank-1 `Stock Returns` | proposal `Stock Returns`
- `expected inflation` | freq `125` | papers `125` | score `0.706` | rank-1 `Inflation` | proposal `Inflation`
- `education level` | freq `135` | papers `135` | score `0.712` | rank-1 `Educational attainment` | proposal `Education`
- `regional economic growth` | freq `109` | papers `109` | score `0.734` | rank-1 `Economic Development and Regional Competitiveness` | proposal `Economic Growth`

## missing_alias

- `institutional quality` | freq `446` | papers `446` | score `0.656` | rank-1 `Institutional Reform` | proposal `Quality (philosophy)`
- `financial constraints` | freq `212` | papers `212` | score `0.608` | rank-1 `Financial distress` | proposal `Financial distress`
- `policy implications` | freq `208` | papers `208` | score `0.670` | rank-1 `Policy Issues` | proposal `Policy`
- `theoretical model` | freq `143` | papers `143` | score `0.721` | rank-1 `Conceptual model` | proposal `Model (art)`
- `small firms` | freq `171` | papers `171` | score `0.678` | rank-1 `Small business` | proposal `Firms`
- `coal consumption` | freq `124` | papers `124` | score `0.686` | rank-1 `coal industry` | proposal `Consumption`
- `united states` | freq `155` | papers `155` | score `0.740` | rank-1 `United States domestic market` | proposal `United States Postal Service.`
- `aggregate output` | freq `125` | papers `125` | score `0.712` | rank-1 `Net output` | proposal `Aggregate Input-Output`
- `industry concentration` | freq `103` | papers `103` | score `0.697` | rank-1 `Market concentration` | proposal `Concentration`
- `digital inclusive finance` | freq `77` | papers `77` | score `0.672` | rank-1 `Digital inclusion` | proposal `Finance`
- `inflation volatility` | freq `95` | papers `95` | score `0.687` | rank-1 `Volatility risk` | proposal `Inflation`
- `financial openness` | freq `87` | papers `87` | score `0.665` | rank-1 `Financial inclusion` | proposal `Openness`
- `short-term interest rates` | freq `89` | papers `89` | score `0.691` | rank-1 `Short rate` | proposal `Interest Rates`
- `market conditions` | freq `96` | papers `96` | score `0.749` | rank-1 `Market environment` | proposal `Labor Market Conditions`
- `distance` | freq `89` | papers `89` | score `0.750` | rank-1 `Distance decay` | proposal `Distance decay`
- `trading activity` | freq `75` | papers `75` | score `0.678` | rank-1 `Pairs trade` | proposal `Pairs trade`
- `markups` | freq `69` | papers `69` | score `0.725` | rank-1 `Spatial heterogeneity` | proposal `Spatial heterogeneity`
- `long-term interest rates` | freq `73` | papers `73` | score `0.680` | rank-1 `Forward interest rate` | proposal `Interest Rates`
- `private information` | freq `80` | papers `80` | score `0.704` | rank-1 `Private information retrieval` | proposal `Information`
- `hospitals` | freq `76` | papers `76` | score `0.663` | rank-1 `Public hospital` | proposal `Public hospital`

## missing_concept_family

- `financial frictions` | freq `106` | papers `106` | score `0.610` | rank-1 `Financial toxicity` | proposal `add_alias_to_existing`
- `monetary shocks` | freq `86` | papers `86` | score `0.659` | rank-1 `monetary economics` | proposal `Monetary`
- `inflation persistence` | freq `73` | papers `73` | score `0.672` | rank-1 `Chronic inflation` | proposal `Inflation`
- `firm characteristics` | freq `68` | papers `68` | score `0.573` | rank-1 `Firm Behavior` | proposal `Firm`
- `economic fundamentals` | freq `69` | papers `69` | score `0.719` | rank-1 `Basic Economics` | proposal `Economic (cyclecar)`
- `unobserved heterogeneity` | freq `59` | papers `59` | score `0.588` | rank-1 `Spatial heterogeneity` | proposal `keep_unresolved`
- `rate of inflation` | freq `52` | papers `52` | score `0.745` | rank-1 `Inflation rate` | proposal `Inflation`
- `monetary policy shock` | freq `50` | papers `50` | score `0.673` | rank-1 `Monetary Policy` | proposal `Monetary Policy`
- `fundamentals` | freq `57` | papers `57` | score `0.740` | rank-1 `Equilibrium Conditions` | proposal `propose_new_concept_family`
- `volatility persistence` | freq `46` | papers `46` | score `0.710` | rank-1 `Volatility risk` | proposal `Volatility (finance)`
- `expansionary monetary policy` | freq `36` | papers `36` | score `0.662` | rank-1 `Expansionary fiscal contraction` | proposal `Monetary Policy`
- `price dynamics` | freq `33` | papers `33` | score `0.660` | rank-1 `Price equation` | proposal `Dynamics`
- `demographic characteristics` | freq `37` | papers `37` | score `0.744` | rank-1 `Demographic Data` | proposal `propose_new_concept_family`
- `administrative costs` | freq `33` | papers `33` | score `0.716` | rank-1 `Management` | proposal `propose_new_concept_family`
- `time-varying risk premia` | freq `31` | papers `31` | score `0.689` | rank-1 `Risk Premia` | proposal `Risk Premia`
- `household characteristics` | freq `35` | papers `35` | score `0.704` | rank-1 `Household Data` | proposal `Household.`
- `usual source of care` | freq `32` | papers `32` | score `0.692` | rank-1 `Direct care` | proposal `propose_new_concept_family`
- `patient age` | freq `33` | papers `33` | score `0.630` | rank-1 `Age structure` | proposal `keep_unresolved`
- `asset price bubbles` | freq `27` | papers `27` | score `0.725` | rank-1 `Asset price inflation` | proposal `Asset Price`
- `agricultural sector` | freq `30` | papers `30` | score `0.660` | rank-1 `Economic sector` | proposal `propose_new_concept_family`

## bad_match_or_noise

- `industrial structure upgrading` | freq `267` | papers `267` | score `0.637` | rank-1 `Macroeconomic Industrial Structure` | proposal `reject_cluster`
- `profitability` | freq `274` | papers `274` | score `0.730` | rank-1 `Profitability analysis` | proposal `reject_cluster`
- `technology` | freq `177` | papers `177` | score `0.691` | rank-1 `Technology innovation` | proposal `reject_cluster`
- `profits` | freq `158` | papers `158` | score `0.701` | rank-1 `Revenue` | proposal `reject_cluster`
- `access to care` | freq `150` | papers `150` | score `0.607` | rank-1 `Access to medicines` | proposal `reject_cluster`
- `labor` | freq `156` | papers `156` | score `0.642` | rank-1 `Skill (labor)` | proposal `keep_unresolved`
- `returns` | freq `119` | papers `119` | score `0.607` | rank-1 `Output` | proposal `reject_cluster`
- `temperature` | freq `64` | papers `64` | score `0.624` | rank-1 `Climate` | proposal `keep_unresolved`
- `financial shocks` | freq `60` | papers `60` | score `0.739` | rank-1 `Bill shock` | proposal `reject_cluster`
- `industry` | freq `60` | papers `60` | score `0.613` | rank-1 `Industry Characteristics` | proposal `reject_cluster`
- `geopolitical risks` | freq `47` | papers `47` | score `0.748` | rank-1 `Political risk` | proposal `reject_cluster`
- `stability` | freq `41` | papers `43` | score `0.730` | rank-1 `Stability Conditions` | proposal `reject_cluster`
- `upgrading of industrial structure` | freq `34` | papers `34` | score `0.740` | rank-1 `Macroeconomic Industrial Structure` | proposal `reject_cluster`
- `momentum` | freq `38` | papers `38` | score `0.656` | rank-1 `Momentum (finance)` | proposal `reject_cluster`
- `regional disparities` | freq `36` | papers `36` | score `0.718` | rank-1 `Regional Inequality` | proposal `reject_cluster`
- `volume` | freq `31` | papers `31` | score `0.552` | rank-1 `Volume (thermodynamics)` | proposal `keep_unresolved`
- `common factors` | freq `30` | papers `30` | score `0.663` | rank-1 `Exposure assessment` | proposal `reject_cluster`
- `macroeconomic outcomes` | freq `29` | papers `29` | score `0.747` | rank-1 `macroeconomic analysis` | proposal `reject_cluster`
- `emission reductions` | freq `20` | papers `20` | score `0.747` | rank-1 `Carbon Emission Reduction Target` | proposal `reject_cluster`
- `structural parameters` | freq `21` | papers `21` | score `0.693` | rank-1 `Structural estimation` | proposal `reject_cluster`

## unclear

- `costs` | freq `137` | papers `137` | score `0.689` | rank-1 `Cost` | proposal `keep_unresolved`
- `competitiveness` | freq `82` | papers `82` | score `0.732` | rank-1 `International Competitiveness` | proposal `keep_unresolved`
- `rents` | freq `74` | papers `74` | score `0.676` | rank-1 `Renting` | proposal `keep_unresolved`
- `eastern region` | freq `84` | papers `84` | score `0.673` | rank-1 `Enterprises` | proposal `keep_unresolved`
- `trust` | freq `54` | papers `54` | score `0.697` | rank-1 `Trust.` | proposal `keep_unresolved`
- `increasing returns` | freq `58` | papers `58` | score `0.697` | rank-1 `Diminishing returns` | proposal `keep_unresolved`
- `japan` | freq `61` | papers `61` | score `0.734` | rank-1 `Japanese mon` | proposal `keep_unresolved`
- `inventories` | freq `52` | papers `52` | score `0.648` | rank-1 `Inventory` | proposal `keep_unresolved`
- `adjustment costs` | freq `52` | papers `52` | score `0.736` | rank-1 `Matching adjustment` | proposal `keep_unresolved`
- `regional heterogeneity` | freq `65` | papers `65` | score `0.699` | rank-1 `Regional variation` | proposal `keep_unresolved`
- `mispricing` | freq `48` | papers `48` | score `0.623` | rank-1 `Misrepresentation` | proposal `keep_unresolved`
- `accessibility` | freq `48` | papers `48` | score `0.685` | rank-1 `Capitalization` | proposal `keep_unresolved`
- `older age` | freq `50` | papers `50` | score `0.724` | rank-1 `Old Age` | proposal `keep_unresolved`
- `size` | freq `48` | papers `48` | score `0.730` | rank-1 `REITS` | proposal `keep_unresolved`
- `eastern region (china)` | freq `62` | papers `62` | score `0.661` | rank-1 `European region` | proposal `keep_unresolved`
- `workers` | freq `48` | papers `48` | score `0.742` | rank-1 `Workers.` | proposal `keep_unresolved`
- `specialization` | freq `41` | papers `41` | score `0.684` | rank-1 `Overspecialization` | proposal `keep_unresolved`
- `demographic factors` | freq `44` | papers `44` | score `0.684` | rank-1 `Demographics` | proposal `keep_unresolved`
- `ethereum` | freq `38` | papers `38` | score `0.704` | rank-1 `Bitcoin` | proposal `keep_unresolved`
- `heterogeneous agents` | freq `42` | papers `42` | score `0.716` | rank-1 `Study heterogeneity` | proposal `keep_unresolved`

