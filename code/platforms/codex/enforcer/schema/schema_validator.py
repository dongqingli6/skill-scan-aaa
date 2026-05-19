"""Prototype schema validator for Codex security evidence reports.

The validator intentionally uses only the Python standard library. It reads
explicit report and schema paths, validates required top-level keys, and does
not inspect host HOME, credentials, Docker, Codex, or runtime traces.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_schema(path: str | Path) -> dict[str, Any]:
    schema_path = Path(path)
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"schema must be a JSON object: {schema_path}")
    data.setdefault("required", [])
    return data


def _type_matches(value: Any, expected: Any) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    checks = {
        "object": dict,
        "array": list,
        "string": str,
        "boolean": bool,
        "integer": int,
        "number": (int, float),
        "null": type(None),
    }
    for name in names:
        expected_type = checks.get(name)
        if expected_type and isinstance(value, expected_type):
            if name == "integer" and isinstance(value, bool):
                continue
            return True
    return False


def validate_required_keys(data: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    required = list(schema.get("required", []))
    missing = [key for key in required if key not in data]
    type_errors: list[dict[str, str]] = []
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        for key, spec in properties.items():
            if key not in data or not isinstance(spec, dict) or "type" not in spec:
                continue
            if not _type_matches(data[key], spec["type"]):
                type_errors.append({"key": key, "expected": str(spec["type"]), "actual": type(data[key]).__name__})
    return {
        "valid": not missing and not type_errors,
        "missing_required_keys": missing,
        "type_errors": type_errors,
        "schema_name": schema.get("schema_name"),
    }


def validate_report_file(report_path: str | Path, schema_path: str | Path) -> dict[str, Any]:
    report_file = Path(report_path)
    schema_file = Path(schema_path)
    data = json.loads(report_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {
            "valid": False,
            "report_path": str(report_file),
            "schema_path": str(schema_file),
            "error": "report must be a JSON object",
        }
    result = validate_required_keys(data, load_schema(schema_file))
    result.update({"report_path": str(report_file), "schema_path": str(schema_file)})
    return result


def summarize_schema_validation(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "valid": all(item.get("valid") for item in results),
        "total": len(results),
        "passed": sum(1 for item in results if item.get("valid")),
        "failed": sum(1 for item in results if not item.get("valid")),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Codex evidence report against a prototype schema")
    parser.add_argument("--report", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    result = validate_report_file(args.report, args.schema)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
