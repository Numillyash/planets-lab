from __future__ import annotations

import argparse
import json

from planets_lab.validation.real_game import latest_batches_by_stream_turn, load_jsonl, summarize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    batches = load_jsonl(args.dataset)
    summary = summarize(batches)
    latest = latest_batches_by_stream_turn(batches)

    imported = 0
    failures = []
    for batch in latest:
        try:
            batch.import_state()
        except Exception as exc:
            failures.append({"batch_id": batch.batch_id, "turn": batch.turn, "slot": batch.stream.source_player_slot_id, "error": f"{type(exc).__name__}: {exc}"})
        else:
            imported += 1

    report = {
        "records": summary.records,
        "streams": summary.streams,
        "turn_range": [summary.min_turn, summary.max_turn],
        "duplicate_turn_snapshots": summary.duplicate_turn_snapshots,
        "consecutive_transitions": summary.consecutive_transitions,
        "canonical_import": {"ok": imported, "failed": len(failures)},
        "failures": failures[:20],
    }

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"records:                 {summary.records}")
        print(f"streams:                 {summary.streams}")
        print(f"turn range:              {summary.min_turn}..{summary.max_turn}")
        print(f"duplicate snapshots:     {summary.duplicate_turn_snapshots}")
        print(f"consecutive transitions: {summary.consecutive_transitions}")
        print(f"canonical import:        {imported} ok / {len(failures)} failed")
        for failure in failures[:20]:
            print(f"  turn={failure['turn']} slot={failure['slot']} batch={failure['batch_id']}: {failure['error']}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
