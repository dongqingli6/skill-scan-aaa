from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


SAFE_SOURCES = {
    "scaled_metrics": "analysis_results/scaled_validation/metrics.json",
    "stage29_summary": "analysis_results/human_review_labeling/summary.json",
    "stage28_summary": "analysis_results/controlled_sinkhole_dynamic/summary.json",
    "stage27_summary": "analysis_results/scaled_validation/summary.json",
    "final_label_dataset": "analysis_results/human_review_labeling/final_label_dataset.csv",
}


def build_public_artifacts(repo_root: Path, public_root: Path) -> dict[str, Any]:
    public_root.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    for name, rel in SAFE_SOURCES.items():
        src = repo_root / rel
        if not src.exists():
            continue
        if src.suffix == ".json":
            data = json.loads(src.read_text(encoding="utf-8"))
            target = public_root / f"{name}.json"
            target.write_text(json.dumps(_sanitize_obj(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        elif src.suffix == ".csv":
            target = public_root / f"{name}.csv"
            _sanitize_csv(src, target)
        else:
            target = public_root / f"{name}.txt"
            target.write_text(_sanitize_text(src.read_text(encoding="utf-8", errors="ignore")), encoding="utf-8")
        generated.append(str(target.relative_to(repo_root)))
    descriptions = public_root / "synthetic_sample_descriptions.md"
    descriptions.write_text(_synthetic_descriptions(), encoding="utf-8")
    generated.append(str(descriptions.relative_to(repo_root)))
    placeholders = public_root / "demo_screenshots_placeholder.md"
    placeholders.write_text("# Demo Screenshots Placeholder\n\nAdd sanitized screenshots before submission.\n", encoding="utf-8")
    generated.append(str(placeholders.relative_to(repo_root)))
    return {"public_artifacts": generated, "sensitive_files_copied": False}


def _sanitize_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_obj(item) for key, item in value.items() if key not in {"raw_skill_text", "body_preview"}}
    if isinstance(value, list):
        return [_sanitize_obj(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _sanitize_text(text: str) -> str:
    return text.replace("/home/empty/Desktop/MaliciousAgentSkillsBench-Codex/", "<repo>/").replace("/home/empty", "<home>")


def _sanitize_csv(src: Path, target: Path) -> None:
    with src.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else ["empty"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _sanitize_text(value) for key, value in row.items()})


def _synthetic_descriptions() -> str:
    return """# Synthetic Sample Descriptions

This project uses synthetic benign, suspicious, and attack-like fixtures for repeatable detector validation.
Attack-like fixtures contain fake tokens, fake env paths, fake SSH markers, and fake docker socket text only.
Real skill archives are intentionally excluded from public artifacts.
"""
