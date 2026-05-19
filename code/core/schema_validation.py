#!/usr/bin/env python3
"""Schema validation helpers for static-only scan artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class SchemaError(ValueError):
    pass


def _load_json(path: str | Path) -> Dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise SchemaError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SchemaError(f"{path}: expected top-level object")
    return data


def _require_keys(obj: Dict[str, Any], keys: Iterable[str], context: str) -> None:
    missing = [key for key in keys if key not in obj]
    if missing:
        raise SchemaError(f"{context}: missing keys: {', '.join(missing)}")


def validate_static(path: str | Path) -> None:
    data = _load_json(path)
    _require_keys(data, ["platform", "root", "summary", "skills"], str(path))
    if not isinstance(data["skills"], list):
        raise SchemaError(f"{path}: skills must be a list")
    _require_keys(data["summary"], ["total_skills", "total_findings", "by_severity"], f"{path}:summary")


def iter_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    rows = []
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"{path}:{lineno}: invalid JSONL row: {exc}") from exc
        if not isinstance(row, dict):
            raise SchemaError(f"{path}:{lineno}: expected object row")
        rows.append(row)
    return rows


def validate_jsonl(path: str | Path) -> None:
    rows = iter_jsonl(path)
    if not rows:
        raise SchemaError(f"{path}: expected at least one JSONL row")
    audit_keys = {"platform", "skill_name", "source_path", "classification", "severity", "confidence", "static_findings"}
    for index, row in enumerate(rows, 1):
        if "mode" in row and row.get("mode") == "static-only":
            _require_keys(row, ["platform", "skill_name", "source_path"], f"{path}:row {index}")
        else:
            _require_keys(row, audit_keys, f"{path}:row {index}")


def validate_summary(path: str | Path) -> None:
    data = _load_json(path)
    _require_keys(data, ["platform", "total_skills", "total_findings", "by_severity", "by_classification"], str(path))
    if not isinstance(data["by_severity"], dict):
        raise SchemaError(f"{path}: by_severity must be an object")
    if not isinstance(data["by_classification"], dict):
        raise SchemaError(f"{path}: by_classification must be an object")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate static scan artifacts")
    parser.add_argument("--static", help="Validate static_scan_results.json")
    parser.add_argument("--jsonl", help="Validate a JSONL queue or audit result")
    parser.add_argument("--summary", help="Validate summary.json")
    args = parser.parse_args()

    try:
        if args.static:
            validate_static(args.static)
            print(f"Valid static scan JSON: {args.static}")
        if args.jsonl:
            validate_jsonl(args.jsonl)
            print(f"Valid JSONL: {args.jsonl}")
        if args.summary:
            validate_summary(args.summary)
            print(f"Valid summary JSON: {args.summary}")
        if not any([args.static, args.jsonl, args.summary]):
            parser.error("provide --static, --jsonl, or --summary")
    except SchemaError as exc:
        print(f"Schema validation failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
