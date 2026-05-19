from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import kill_chain_mapper
import taxonomy


OUTPUT_ROOT = Path("analysis_results/human_review_labeling")


def write_labeling_outputs(cards: list[dict[str, Any]], output_root: Path | None = None) -> dict[str, Any]:
    root = output_root or OUTPUT_ROOT
    cards_dir = root / "review_cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    for card in cards:
        (cards_dir / f"{_slug(card['sample'])}.json").write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = _summary(cards)
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "review_cards.json").write_text(json.dumps(cards, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "vulnerability_taxonomy.json").write_text(json.dumps(taxonomy.taxonomy_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    matrix = kill_chain_mapper.matrix(cards)
    (root / "kill_chain_matrix.json").write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "manual_review_queue.md").write_text(_manual_review_queue(cards), encoding="utf-8")
    (root / "final_label_dataset.json").write_text(json.dumps(cards, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(root / "final_label_dataset.csv", cards)
    (root / "report.md").write_text(_report(cards, summary, matrix), encoding="utf-8")
    return summary


def _summary(cards: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = Counter(card["recommended_verdict"] for card in cards)
    labels = Counter(label for card in cards for label in card["taxonomy_labels"])
    severities = Counter(card["severity"] for card in cards)
    return {
        "stage": "Big Stage 29 Human Review and Vulnerability Labeling Layer",
        "total_samples": len(cards),
        "verdict_distribution": dict(verdicts),
        "taxonomy_distribution": dict(labels),
        "severity_distribution": dict(severities),
        "manual_verdict_empty": all(card["manual_verdict"] == "" for card in cards),
        "docker_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "real_skill_executed": False,
        "network_enabled": False,
        "real_api_called": False,
        "final_status": "pass",
    }


def _manual_review_queue(cards: list[dict[str, Any]]) -> str:
    queued = [card for card in cards if card["recommended_verdict"] in {"manual_review_required", "blocked", "malicious"}]
    lines = ["# Stage 29 Manual Review Queue", ""]
    for card in queued:
        lines.append(f"## {card['sample']}")
        lines.append(f"- source_type: {card['source_type']}")
        lines.append(f"- severity: {card['severity']}")
        lines.append(f"- recommended_verdict: {card['recommended_verdict']}")
        lines.append(f"- taxonomy_labels: `{', '.join(card['taxonomy_labels'])}`")
        lines.append(f"- kill_chain_phases: `{', '.join(card['kill_chain_phases'])}`")
        lines.append("- manual_verdict: ``")
        lines.append("")
    return "\n".join(lines)


def _write_csv(path: Path, cards: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample", "source_type", "severity", "confidence", "recommended_verdict", "manual_verdict", "taxonomy_labels", "kill_chain_phases", "evidence_paths"],
        )
        writer.writeheader()
        for card in cards:
            writer.writerow(
                {
                    "sample": card["sample"],
                    "source_type": card["source_type"],
                    "severity": card["severity"],
                    "confidence": card["confidence"],
                    "recommended_verdict": card["recommended_verdict"],
                    "manual_verdict": card["manual_verdict"],
                    "taxonomy_labels": ";".join(card["taxonomy_labels"]),
                    "kill_chain_phases": ";".join(card["kill_chain_phases"]),
                    "evidence_paths": ";".join(card["evidence_paths"]),
                }
            )


def _report(cards: list[dict[str, Any]], summary: dict[str, Any], matrix: dict[str, Any]) -> str:
    lines = [
        "# Big Stage 29 Human Review and Vulnerability Labeling Layer",
        "",
        "## Sample-level Review Summary",
        "",
    ]
    for card in cards:
        lines.append(f"- `{card['sample']}`: severity `{card['severity']}`, recommended `{card['recommended_verdict']}`, labels `{', '.join(card['taxonomy_labels'])}`")
    lines.extend(
        [
            "",
            "## Taxonomy Distribution",
            "",
            json.dumps(summary["taxonomy_distribution"], indent=2, sort_keys=True),
            "",
            "## Kill Chain Matrix",
            "",
            json.dumps(matrix, indent=2, sort_keys=True),
            "",
            "## Limitations",
            "",
            "Stage 29 does not execute samples and does not replace human judgment. `manual_verdict` remains blank for reviewer input. Synthetic attack-like samples are validation fixtures, not real-world malicious conclusions.",
            "",
        ]
    )
    return "\n".join(lines)


def _slug(name: str) -> str:
    return name.replace("/", "_").replace(".", "_").replace("-", "_")
