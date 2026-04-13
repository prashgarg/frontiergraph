#!/bin/zsh
set -uo pipefail

target=200
run_dir="data/pilots/frontiergraph_extraction_v2/judge_runs/recite_alignment_pilot100_node_alignment_gpt5nano_low_v1"
parsed_path="$run_dir/parsed_results.jsonl"
errors_path="$run_dir/errors.jsonl"

while true; do
  parsed=$(python3 -c "from pathlib import Path; p=Path('$parsed_path'); print(sum(1 for _ in p.open()) if p.exists() else 0)")
  errors=$(python3 -c "from pathlib import Path; p=Path('$errors_path'); print(sum(1 for _ in p.open()) if p.exists() else 0)")
  total=$((parsed + errors))
  echo "parsed=$parsed errors=$errors total=$total"
  if [ "$total" -ge "$target" ]; then
    break
  fi

  python3 next_steps/validation/run_overlap_judge.py \
    --input-jsonl next_steps/validation/judge_inputs/recite_alignment_pilot100_variable_v1_v2_node_alignment.jsonl \
    --system-prompt next_steps/validation/prompt_pack/system_prompt_node_alignment.md \
    --user-prompt next_steps/validation/prompt_pack/user_prompt_node_alignment_template.md \
    --schema-json next_steps/validation/prompt_pack/node_alignment_schema.json \
    --schema-name node_alignment_judge \
    --run-name recite_alignment_pilot100_node_alignment_gpt5nano_low_v1 \
    --model gpt-5-nano \
    --reasoning-effort low \
    --timeout-seconds 240 \
    --max-concurrency 8

  sleep 1
done
