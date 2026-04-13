from __future__ import annotations

import argparse
import subprocess
import json
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keep resuming a node-alignment judge run until target rows are processed.")
    parser.add_argument("--target-total", type=int, required=True)
    parser.add_argument("--parsed-jsonl", required=True)
    parser.add_argument("--errors-jsonl", required=True)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--max-attempts", type=int, default=50)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def count_unique_pairs(*paths: Path) -> int:
    seen: set[tuple[str, str]] = set()
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                benchmark_id = str(row.get("benchmark_id"))
                prompt_family = str(row.get("prompt_family"))
                seen.add((prompt_family, benchmark_id))
    return len(seen)


def main() -> None:
    args = parse_args()
    if not args.command:
        raise SystemExit("No command provided.")
    command = args.command
    if command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("No command provided after '--'.")

    parsed_path = Path(args.parsed_jsonl)
    errors_path = Path(args.errors_jsonl)

    attempts = 0
    last_total = -1
    while attempts < args.max_attempts:
        parsed = count_rows(parsed_path)
        errors = count_rows(errors_path)
        total = count_unique_pairs(parsed_path, errors_path)
        print(
            f"[resume-loop] parsed={parsed} errors={errors} unique_total={total} target={args.target_total}",
            flush=True,
        )
        if total >= args.target_total:
            return

        attempts += 1
        result = subprocess.run(command, check=False)
        print(f"[resume-loop] attempt={attempts} exit_code={result.returncode}", flush=True)

        parsed = count_rows(parsed_path)
        errors = count_rows(errors_path)
        total = count_unique_pairs(parsed_path, errors_path)
        print(
            f"[resume-loop] after-attempt parsed={parsed} errors={errors} unique_total={total}",
            flush=True,
        )
        if total >= args.target_total:
            return

        if total <= last_total and result.returncode == 0:
            print("[resume-loop] no progress detected on a zero-exit attempt; stopping.", flush=True)
            return
        last_total = total
        time.sleep(args.sleep_seconds)

    raise SystemExit(f"Reached max attempts ({args.max_attempts}) before hitting target total.")


if __name__ == "__main__":
    main()
