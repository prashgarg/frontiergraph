# Website And Product

## Purpose

This file records the current public product story, site/app architecture, and the main design judgments already reached.

## Current Public Story

FrontierGraph should be presented as:

- a concept graph of economics and adjacent literature
- a deterministic system that ranks what to study next
- a product where AI extracts graph structure from text, but ranking and cleanup are deterministic and inspectable

The old JEL-first public story is historical only.

## Current Public Default

- ontology regime: `Baseline`
- mapping mode: `Exploratory`
- surfaced recommendation list: suppressed top-100k baseline exploratory ranking

Advanced comparison options exist but are not the main narrative.

## Public Architecture

- public site: Astro
- deeper explorer: Streamlit

Public routes:

- `/`
- `/graph/`
- `/opportunities/`
- `/method/`
- `/compare/`
- `/downloads/`

## Main Product Judgments

### Good

- dark graph-native theme is directionally right
- serious, non-hype framing is right
- compare functionality is useful as advanced depth

### Still important

- reduce density
- show one main thing at a time
- hide complexity until asked
- graph page should feel graph-first, not dashboard-first
- homepage should orient, not overwhelm

## Current Design Direction

Keep:

- dark theme
- graph-native visual language
- serious typography
- data/research-tool feeling

Change:

- fewer simultaneous panels
- lighter first screens
- more progressive disclosure
- shorter copy on primary pages

## Page-Specific Judgment

### Homepage

Should answer:

1. what it is
2. why it matters
3. what you can do with it
4. why it is not just a chatbot prompt

Need:

- one graph preview
- one opportunity/example block
- one benchmark/trust block
- less stacked proof content

### Graph page

Should be the hero interaction.

Need:

- graph dominance
- slimmer side panel
- stronger selected-node behavior
- selective labels
- no metric-wall feeling

### Opportunities page

Should feel like a curated recommendation surface, not a score dump.

Need:

- concept search near top
- top opportunities visible first
- slices behind tabs/accordions
- fewer repeated metric pills

### Method page

Should feel credible without requiring study.

Need:

- one-paragraph top summary
- collapsible sections
- deeper detail only on demand

### Compare page

Should stay advanced.

Need:

- short intro
- compact regime cards
- overlap tables secondary, not primary

## Current App Judgment

The app should:

- default to baseline exploratory
- keep compare modes available as advanced controls
- make concept search primary
- keep raw vs adjusted scoring inspectable for the suppressed baseline surface

## Key Decisions

- public default = `Baseline exploratory`
- Broad / Conservative remain advanced comparison views
- site and app should no longer present the old JEL beta as the main story
- suppression layer is product cleanup and should help the visible ranking feel more sensible

## Decision Log

- concept graph replaced JEL-first framing
- compare view preserved as a feature, not a bug
- public default narrowed to baseline exploratory
- duplicate suppression adopted to clean recommendation surface

## Open Questions

- how far to take semantic search in the app
- how prominent the graph viewer should be relative to opportunities on the homepage
- whether public comparison content should stay compact or become a larger educational page

## Recommended Next Actions

- continue page-by-page simplification
- polish graph page visual hierarchy
- keep public site shallow and readable
- keep deeper technical content behind expanders or secondary pages

