from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair sample batch submission tracking after duplicate uploads.")
    parser.add_argument("--spec-json", required=True)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iso_from_unix(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def canonical_submission(
    *,
    existing_submission: dict[str, Any],
    kept_poll: dict[str, Any],
    canceled_duplicate_batch_ids: list[str],
) -> dict[str, Any]:
    batch = kept_poll["batch"]
    created_at = batch.get("created_at")
    return {
        "submitted_at_utc": iso_from_unix(created_at),
        "jsonl_path": existing_submission["jsonl_path"],
        "uploaded_file": None,
        "batch": batch,
        "tracking": {
            "repaired_at_utc": datetime.now(timezone.utc).isoformat(),
            "repair_reason": "Initial local receipt pointed to a duplicate batch. Canonical batch repaired from kept poll metadata.",
            "canonical_batch_id": batch["id"],
            "canceled_duplicate_batch_ids": canceled_duplicate_batch_ids,
            "original_local_batch_id": existing_submission.get("batch", {}).get("id"),
        },
    }


def main() -> None:
    args = parse_args()
    spec_path = Path(args.spec_json)
    spec = load_json(spec_path)
    tracking_root = spec_path.parent
    results: list[dict[str, Any]] = []

    for item in spec["repairs"]:
        batch_dir = Path(item["batch_dir"])
        submission_path = batch_dir / "submission.json"
        backup_path = batch_dir / "submission.duplicate_receipt.json"

        existing_submission = load_json(submission_path)
        kept_poll = load_json(Path(item["kept_poll"]))
        duplicate_polls = [load_json(Path(path)) for path in item["duplicate_polls"]]
        canceled_duplicate_batch_ids = [poll["batch"]["id"] for poll in duplicate_polls]

        if not backup_path.exists():
            backup_path.write_text(
                json.dumps(existing_submission, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        repaired = canonical_submission(
            existing_submission=existing_submission,
            kept_poll=kept_poll,
            canceled_duplicate_batch_ids=canceled_duplicate_batch_ids,
        )
        submission_path.write_text(
            json.dumps(repaired, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        results.append(
            {
                "batch_dir": str(batch_dir),
                "canonical_batch_id": repaired["batch"]["id"],
                "canceled_duplicate_batch_ids": canceled_duplicate_batch_ids,
                "backup_path": str(backup_path),
                "submission_path": str(submission_path),
            }
        )

    ledger = {
        "repaired_at_utc": datetime.now(timezone.utc).isoformat(),
        "spec_json": str(spec_path),
        "results": results,
    }
    ledger_path = tracking_root / "submission_tracking_repair_ledger.json"
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(ledger, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
