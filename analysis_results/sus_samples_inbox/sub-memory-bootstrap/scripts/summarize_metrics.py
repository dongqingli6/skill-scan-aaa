#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def avg(records: list[dict], key: str) -> float:
    values = [float(record.get(key, 0) or 0) for record in records]
    return round(mean(values), 3) if values else 0.0


def total(records: list[dict], key: str) -> int:
    return int(sum(float(record.get(key, 0) or 0) for record in records))


def summarize(records: list[dict]) -> dict:
    by_type = Counter(record.get("event_type", "unknown") for record in records)
    agent_turns = [record for record in records if record.get("event_type") == "agent_turn"]
    mcp_recalls = [record for record in records if record.get("event_type") == "mcp_recall"]
    mcp_stores = [record for record in records if record.get("event_type") == "mcp_store"]
    mcp_reinforces = [
        record for record in records if record.get("event_type") == "mcp_reinforce"
    ]

    return {
        "record_count": len(records),
        "event_counts": dict(by_type),
        "agent_turn_summary": {
            "count": len(agent_turns),
            "avg_input_tokens": avg(agent_turns, "input_tokens"),
            "avg_output_tokens": avg(agent_turns, "output_tokens"),
            "avg_total_tokens": avg(agent_turns, "total_tokens"),
            "avg_memory_context_tokens": avg(
                agent_turns,
                "estimated_memory_context_tokens",
            ),
            "avg_recalled_memory_count": avg(agent_turns, "recalled_memory_count"),
        },
        "mcp_recall_summary": {
            "count": len(mcp_recalls),
            "avg_estimated_memory_tokens": avg(
                mcp_recalls,
                "estimated_memory_tokens",
            ),
            "avg_node_count": avg(mcp_recalls, "node_count"),
            "avg_memory_chars": avg(mcp_recalls, "memory_chars"),
            "max_estimated_memory_tokens": max(
                (int(record.get("estimated_memory_tokens", 0) or 0) for record in mcp_recalls),
                default=0,
            ),
        },
        "mcp_store_summary": {
            "count": len(mcp_stores),
            "total_stored_chars": total(mcp_stores, "stored_chars"),
        },
        "mcp_reinforce_summary": {
            "count": len(mcp_reinforces),
            "total_updated_edges": total(mcp_reinforces, "updated_edge_count"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize sub-memory metrics.jsonl")
    parser.add_argument(
        "--path",
        default=".sub-memory/metrics.jsonl",
        help="Path to metrics JSONL file.",
    )
    args = parser.parse_args()

    summary = summarize(load_records(Path(args.path)))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
