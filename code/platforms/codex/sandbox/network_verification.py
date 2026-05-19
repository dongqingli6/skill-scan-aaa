"""Generate no-network verification from safe smoke dynamic evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def build_network_verification(input_dir: str | Path) -> Dict[str, Any]:
    base = Path(input_dir)
    evidence = json.loads((base / "dynamic_evidence.json").read_text(encoding="utf-8"))
    evidence_lines = evidence.get("evidence_lines", {}).get("api_connection", [])
    external_attempt = evidence.get("api_connection_blocked", False)
    external_blocked = evidence.get("network_disabled_observed", False)
    status = "passed" if external_attempt and external_blocked else "inconclusive"
    if external_attempt and not external_blocked:
        status = "failed"
    return {
        "verification_type": "network_disabled_safe_smoke",
        "note": "This is safe_skill smoke test network-boundary verification, not malicious sample dynamic verification.",
        "network_mode_expected": "none",
        "external_api_attempt_observed": bool(external_attempt),
        "external_api_blocked": bool(external_blocked),
        "verification_status": status,
        "evidence_lines": evidence_lines[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Codex no-network verification")
    parser.add_argument("--input-dir", required=True)
    args = parser.parse_args()
    base = Path(args.input_dir)
    report = build_network_verification(base)
    out = base / "network_disabled_verification.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
