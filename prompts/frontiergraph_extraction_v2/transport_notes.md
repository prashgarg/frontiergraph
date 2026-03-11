# FrontierGraph Extraction v2: Responses and Batch Transport Notes

These notes reflect current official OpenAI documentation as checked on March 8, 2026.

## Recommended synchronous API shape

Use the Responses API with:

- `model`
- `reasoning: {"effort": "..."}`
- `instructions` for the system prompt
- `input` for the user message
- `text.format` with `type = "json_schema"`
- `max_output_tokens` set generously

Recommended `max_output_tokens` for the pilot:

- `25000`

Reason:
- OpenAI's current reasoning-model guidance notes that `max_output_tokens` is an upper bound that includes both reasoning tokens and visible output tokens.
- For a structured extraction task on long abstracts, a generous cap is safer than risking truncation.

Example request body for `/v1/responses`:

```json
{
  "model": "gpt-5-mini",
  "reasoning": {
    "effort": "low"
  },
  "instructions": "<contents of system_prompt.md>",
  "input": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "Extract a paper-local research graph from the following title and abstract.\n\nUse only the information in the title and abstract.\nReturn only the structured output that matches the supplied JSON schema.\n\nTitle:\n{{paper_title}}\n\nAbstract:\n{{paper_abstract}}"
        }
      ]
    }
  ],
  "text": {
    "format": {
      "type": "json_schema",
      "name": "frontiergraph_paper_graph_v2",
      "strict": true,
      "schema": "<contents of schema.json>"
    }
  },
  "max_output_tokens": 25000
}
```

## Recommended batch shape

For batches, use:

- uploaded JSONL file with `purpose = "batch"`
- `endpoint = "/v1/responses"`
- `completion_window = "24h"`

Each JSONL line should contain:

- `custom_id`
- `method`
- `url`
- `body`

Example JSONL line:

```json
{"custom_id":"W2088490799__gpt5mini_low","method":"POST","url":"/v1/responses","body":{"model":"gpt-5-mini","reasoning":{"effort":"low"},"instructions":"<contents of system_prompt.md>","input":[{"role":"user","content":[{"type":"input_text","text":"Extract a paper-local research graph from the following title and abstract.\n\nUse only the information in the title and abstract.\nReturn only the structured output that matches the supplied JSON schema.\n\nTitle:\n{{paper_title}}\n\nAbstract:\n{{paper_abstract}}"}]}],"text":{"format":{"type":"json_schema","name":"frontiergraph_paper_graph_v2","strict":true,"schema":"<contents of schema.json>"}},"max_output_tokens":25000}}
```

## `custom_id` recommendation

If a batch contains one request per paper, then the OpenAlex work ID can be the basis of `custom_id`.

Recommended convention:

- pilot and multi-condition runs:
  - `W2088490799__gpt5mini_low`
  - `W2088490799__gpt5mini_medium`
  - `W2088490799__gpt5nano_low`
  - `W2088490799__gpt5nano_medium`

- production single-condition batches:
  - `W2088490799`

The important current Batch rule is that `custom_id` must be unique within a batch input file.

## Batch operational notes

- Each batch input file should target one endpoint.
- Each batch input file should use one model.
- For the pilot, do not batch.
- For production, batching is appropriate once the prompt and schema are stable.
- For production, upload a first small batch as a smoke test before sending the full set.

## Official references used

- Structured outputs guide:
  - https://platform.openai.com/docs/guides/structured-outputs
- Batch guide:
  - https://platform.openai.com/docs/guides/batch
- Batch API reference:
  - https://platform.openai.com/docs/api-reference/batch
- GPT-5 model docs:
  - https://platform.openai.com/docs/models/gpt-5
- GPT-5 mini model docs:
  - https://platform.openai.com/docs/models/gpt-5-mini
- Reasoning guide:
  - https://platform.openai.com/docs/guides/reasoning
