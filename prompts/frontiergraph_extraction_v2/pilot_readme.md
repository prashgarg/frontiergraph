# FrontierGraph Extraction v2 Pilot

This directory defines the extraction prompt pack and the first comparison pilot.

## Recommended pilot size

Best default:

- `96` papers total
- stratified across:
  - `core` vs `adjacent`
  - `2024`, `2025`, `2026`

That gives:

- `16` papers per `(bucket, year)` stratum when possible
- `384` total Responses API calls across the 4 model conditions

Why `96`:

- large enough to compare extraction behavior across 4 conditions
- small enough for close manual review
- balanced across recent years and across core vs adjacent journals

If a smaller smoke test is needed first, use:

- `24` papers total
- `4` per `(bucket, year)` stratum

## Four pilot conditions

Defined in [pilot_conditions.json](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/prompts/frontiergraph_extraction_v2/pilot_conditions.json):

- `gpt5mini_low`
- `gpt5mini_medium`
- `gpt5nano_low`
- `gpt5nano_medium`

## Scripts

Build the sample:

- [build_frontiergraph_extraction_pilot_sample.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/build_frontiergraph_extraction_pilot_sample.py)

Run the pilot:

- [run_frontiergraph_extraction_pilot.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/run_frontiergraph_extraction_pilot.py)

## Key note

The pilot uses the OpenAI API key, not the OpenAlex key.

Recommended key file:

- `../key/openai_key_prashant.txt`

## Attachments

For this pilot, no file attachments are needed. The title and abstract should be sent as text in the Responses API `input` payload.
