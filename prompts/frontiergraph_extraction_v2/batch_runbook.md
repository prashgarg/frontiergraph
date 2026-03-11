# FrontierGraph Extraction v2 Batch Runbook

These notes reflect the current official OpenAI batch flow checked on March 8, 2026.

## What gets created

Use:

- [build_frontiergraph_extraction_batch_inputs.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/build_frontiergraph_extraction_batch_inputs.py)

This creates one JSONL file per condition:

- `gpt5mini_low.jsonl`
- `gpt5mini_medium.jsonl`
- `gpt5nano_low.jsonl`
- `gpt5nano_medium.jsonl`

Each file:

- targets `POST /v1/responses`
- uses one model / reasoning condition
- contains one request per paper

## Validate before upload

Use:

- [validate_frontiergraph_batch_inputs.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/validate_frontiergraph_batch_inputs.py)

This checks:

- valid JSONL
- required keys present
- `custom_id` uniqueness within each file
- `url = /v1/responses`
- `method = POST`
- `text.format.type = json_schema`

## Upload and create batch

Use:

- [submit_frontiergraph_batch.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/submit_frontiergraph_batch.py)

The script:

- uploads the JSONL file with `purpose = "batch"`
- creates the batch with:
  - `endpoint = "/v1/responses"`
  - `completion_window = "24h"`
- saves submission metadata locally

## Poll and download outputs

Use:

- [poll_frontiergraph_batch.py](/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant%20Garg/GraphDir/scripts/poll_frontiergraph_batch.py)

When the batch is complete, this can download:

- `output_file_id`
- `error_file_id`

## Recommended operational pattern

1. Build a small smoke batch pack first.
2. Validate the files locally.
3. Upload only one condition first.
4. Confirm the batch reaches `completed`.
5. Download and inspect both output and error files.
6. Then submit the other three conditions.

## Current official references

- Batch guide: [developers.openai.com/api/docs/guides/batch](https://developers.openai.com/api/docs/guides/batch)
- Batch reference: [developers.openai.com/api/reference/resources/batches](https://developers.openai.com/api/reference/resources/batches)
- File upload reference: [developers.openai.com/api/reference/resources/files/methods/create](https://developers.openai.com/api/reference/resources/files/methods/create)

Useful current points from the docs:

- upload batch files with `purpose = "batch"`
- create the batch with `completion_window = "24h"`
- batch status includes `output_file_id`, `error_file_id`, and request counts
