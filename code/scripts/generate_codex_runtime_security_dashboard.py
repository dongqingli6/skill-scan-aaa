#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = ROOT / "dashboard"
DATA_PATH = DASHBOARD_DIR / "dashboard_data.json"
HTML_PATH = DASHBOARD_DIR / "index.html"
CSS_PATH = DASHBOARD_DIR / "style.css"
README_PATH = DASHBOARD_DIR / "README.md"


COMPLETED_STAGES = [
    "Static-only Codex scan",
    "Dynamic evidence integration",
    "Safe Docker sandbox smoke",
    "Runtime monitor and kill path",
    "Sandbox hardening",
    "Egress proxy / allowlist design",
    "Syscall policy classification",
    "Policy-driven enforcement regression",
    "Evidence schema",
    "Synthetic attack matrix",
    "Release freeze",
    "CI/CD safe regression integration",
    "Release audit",
]

RECOMMENDED_NEXT_STEPS = [
    "production seccomp tuning",
    "AppArmor loading and audit",
    "controlled egress proxy",
    "syscall allowlist refinement",
    "resource telemetry",
    "isolated VM malicious sample evaluation",
    "CI/CD hardening",
]

SAFETY_BOUNDARIES = {
    "no_docker_execution_in_current_static_suite": True,
    "no_codex_execution": True,
    "no_strace_execution": True,
    "no_real_samples": True,
    "no_network_enabling": True,
    "no_real_tokens": True,
    "no_docker_sock_mount": True,
    "no_privileged_container": True,
    "no_network_host": True,
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def audit_summary(audit_text: str) -> dict:
    blocking = "### Blocking findings\n\nNone." in audit_text
    verdict = "Release audit passed for research prototype handoff."
    return {
        "blocking_findings": 0 if blocking else None,
        "non_blocking_findings": [
            "Pre-existing modified and untracked files exist outside the Stage 9 audit scope.",
            "summary.json records final_status as PASS.",
        ],
        "documentation_only_matches": True,
        "final_verdict": verdict if verdict in audit_text else "Review required",
    }


def matrix_summary(matrix: dict) -> dict:
    cases = matrix.get("cases", [])
    return {
        "total_cases": matrix.get("total_cases", len(cases)),
        "passed_cases": matrix.get("passed_cases", 0),
        "failed_cases": matrix.get("failed_cases", 0),
        "all_passed": matrix.get("all_passed", False),
        "cases": [
            {
                "case_id": case.get("case_id"),
                "expected_severity": case.get("expected_severity"),
                "actual_severity": case.get("actual_severity"),
                "expected_action": case.get("expected_action"),
                "actual_action": case.get("actual_action"),
                "matched_rule": case.get("matched_rule"),
                "passed": case.get("passed"),
            }
            for case in cases
        ],
        "safety_boundaries": matrix.get("safety_boundaries", {}),
    }


def risk_summary(matrix: dict) -> dict:
    counts = Counter()
    for case in matrix.get("cases", []):
        severity = str(case.get("actual_severity", "UNKNOWN")).upper()
        counts[severity] += 1
    return {
        "LOW": counts.get("LOW", 0),
        "MEDIUM": counts.get("MEDIUM", 0),
        "HIGH": counts.get("HIGH", 0),
        "CRITICAL": counts.get("CRITICAL", 0),
    }


def build_data() -> dict:
    safe_summary = read_json(ROOT / "analysis_results/codex_safe_regression_static_only/summary.json")
    matrix = read_json(ROOT / "analysis_results/codex_synthetic_attack_matrix/matrix_result.json")
    release_notes = read_text(ROOT / "RELEASE_NOTES_CODEX_RUNTIME_SECURITY_PROTOTYPE.md")
    audit_text = read_text(ROOT / "RELEASE_AUDIT_CODEX_RUNTIME_SECURITY.md")

    return {
        "release_name": "Codex Runtime Security Prototype",
        "current_stage": "Stage 11: Offline Dashboard / Visual Report",
        "completed_stages": COMPLETED_STAGES,
        "safety_boundaries": SAFETY_BOUNDARIES,
        "safe_regression_summary": {
            "total_tests": safe_summary.get("total_tests"),
            "passed": safe_summary.get("passed"),
            "failed": safe_summary.get("failed"),
            "final_status": safe_summary.get("final_status"),
            "docker_executed": safe_summary.get("docker_executed"),
            "codex_executed": safe_summary.get("codex_executed"),
            "strace_executed": safe_summary.get("strace_executed"),
            "real_samples_executed": safe_summary.get("real_samples_executed"),
            "network_enabled": safe_summary.get("network_enabled"),
        },
        "synthetic_attack_matrix_summary": matrix_summary(matrix),
        "audit_summary": audit_summary(audit_text),
        "risk_summary": risk_summary(matrix),
        "generated_files": [
            "dashboard/index.html",
            "dashboard/dashboard_data.json",
            "dashboard/style.css",
            "dashboard/README.md",
        ],
        "recommended_next_steps": RECOMMENDED_NEXT_STEPS,
        "source_documents": [
            "RELEASE_NOTES_CODEX_RUNTIME_SECURITY_PROTOTYPE.md",
            "FINAL_ACCEPTANCE_REPORT_CODEX.md",
            "RELEASE_AUDIT_CODEX_RUNTIME_SECURITY.md",
            "analysis_results/codex_safe_regression_static_only/summary.json",
            "analysis_results/codex_synthetic_attack_matrix/matrix_result.json",
        ],
        "release_note_excerpt": release_notes.split("## Remaining Work", 1)[0].strip(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def status_text(data: dict) -> str:
    regression = data["safe_regression_summary"]
    audit = data["audit_summary"]
    return (
        f"Release Audit Passed / Safe Regression {regression['final_status']} "
        f"{regression['passed']}/{regression['total_tests']}"
        if audit["blocking_findings"] == 0
        else "Release Audit Review Required"
    )


def render_badge(value: object) -> str:
    if value is True:
        return '<span class="badge good">confirmed</span>'
    if value is False:
        return '<span class="badge muted">false</span>'
    return f'<span class="badge">{escape(str(value))}</span>'


def render_html(data: dict) -> str:
    regression = data["safe_regression_summary"]
    matrix = data["synthetic_attack_matrix_summary"]
    risk = data["risk_summary"]
    audit = data["audit_summary"]

    stages = "\n".join(
        f"<li><span>{escape(stage)}</span></li>" for stage in data["completed_stages"]
    )
    boundaries = "\n".join(
        f"<li><span>{escape(key.replace('_', ' '))}</span>{render_badge(value)}</li>"
        for key, value in data["safety_boundaries"].items()
    )
    cases = "\n".join(
        "<tr>"
        f"<td>{escape(str(case['case_id']))}</td>"
        f"<td>{escape(str(case['expected_severity']))}</td>"
        f"<td>{escape(str(case['actual_severity']))}</td>"
        f"<td>{escape(str(case['expected_action']))}</td>"
        f"<td>{escape(str(case['actual_action']))}</td>"
        f"<td>{escape(str(case['matched_rule']))}</td>"
        f"<td>{'PASS' if case['passed'] else 'FAIL'}</td>"
        "</tr>"
        for case in matrix["cases"]
    )
    next_steps = "\n".join(
        f"<li>{escape(step)}</li>" for step in data["recommended_next_steps"]
    )

    embedded = json.dumps(data, indent=2)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Codex Runtime Security Prototype</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyebrow">Offline Visual Report</p>
      <h1>Codex Runtime Security Prototype</h1>
      <p class="status">{escape(status_text(data))}</p>
    </div>
    <div class="summary-card">
      <span>Current Stage</span>
      <strong>{escape(data["current_stage"])}</strong>
    </div>
  </header>

  <main>
    <section class="metrics" aria-label="Regression summary">
      <article>
        <span>Total Tests</span>
        <strong>{regression["total_tests"]}</strong>
      </article>
      <article>
        <span>Passed</span>
        <strong>{regression["passed"]}</strong>
      </article>
      <article>
        <span>Failed</span>
        <strong>{regression["failed"]}</strong>
      </article>
      <article>
        <span>Final Status</span>
        <strong>{escape(str(regression["final_status"]))}</strong>
      </article>
    </section>

    <section class="panel">
      <h2>Completed Stages</h2>
      <ol class="timeline">{stages}</ol>
    </section>

    <section class="panel">
      <h2>Safety Boundary</h2>
      <ul class="boundary-list">{boundaries}</ul>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>Risk Summary</h2>
        <div class="risk-grid">
          <div><span>LOW</span><strong>{risk["LOW"]}</strong></div>
          <div><span>MEDIUM</span><strong>{risk["MEDIUM"]}</strong></div>
          <div><span>HIGH</span><strong>{risk["HIGH"]}</strong></div>
          <div><span>CRITICAL</span><strong>{risk["CRITICAL"]}</strong></div>
        </div>
      </article>
      <article class="panel">
        <h2>Release Audit</h2>
        <p><strong>Blocking findings:</strong> {audit["blocking_findings"]}</p>
        <p><strong>Final verdict:</strong> {escape(audit["final_verdict"])}</p>
      </article>
    </section>

    <section class="panel">
      <h2>Synthetic Attack Matrix</h2>
      <p class="subtle">Cases passed: {matrix["passed_cases"]}/{matrix["total_cases"]}</p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Case</th>
              <th>Expected Severity</th>
              <th>Actual Severity</th>
              <th>Expected Action</th>
              <th>Actual Action</th>
              <th>Rule</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>{cases}</tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <h2>Remaining Work</h2>
      <ul class="work-list">{next_steps}</ul>
    </section>
  </main>

  <script type="application/json" id="dashboard-data">
{escape(embedded)}
  </script>
</body>
</html>
"""


def render_css() -> str:
    return """* {
  box-sizing: border-box;
}

body {
  margin: 0;
  color: #17202a;
  background: #f6f7f9;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 40px 48px 28px;
  background: #ffffff;
  border-bottom: 1px solid #dfe4ea;
}

.eyebrow,
.subtle,
.summary-card span,
.metrics span,
.risk-grid span {
  color: #5f6b7a;
}

h1 {
  margin: 8px 0;
  font-size: 34px;
  line-height: 1.1;
}

h2 {
  margin: 0 0 18px;
  font-size: 20px;
}

.status {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #155f3b;
}

.summary-card,
.panel,
.metrics article {
  background: #ffffff;
  border: 1px solid #dfe4ea;
  border-radius: 8px;
}

.summary-card {
  width: min(360px, 100%);
  padding: 18px;
}

.summary-card strong {
  display: block;
  margin-top: 6px;
}

main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 24px 48px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.metrics article,
.panel {
  padding: 20px;
}

.metrics strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
}

.panel {
  margin-bottom: 18px;
}

.timeline {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 18px;
  margin: 0;
  padding-left: 22px;
}

.timeline li,
.work-list li {
  padding: 4px 0;
}

.boundary-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.boundary-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 44px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e4e8ee;
  border-radius: 6px;
}

.badge {
  white-space: nowrap;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef1f5;
  font-size: 12px;
  font-weight: 700;
}

.badge.good {
  color: #155f3b;
  background: #dff5e8;
}

.badge.muted {
  color: #5f6b7a;
}

.grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 18px;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.risk-grid div {
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #e4e8ee;
  border-radius: 6px;
}

.risk-grid strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 860px;
}

th,
td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #e4e8ee;
  vertical-align: top;
}

th {
  color: #344054;
  background: #f8fafc;
}

.work-list {
  columns: 2;
  margin: 0;
  padding-left: 20px;
}

@media (max-width: 820px) {
  .topbar,
  .grid {
    display: block;
  }

  .summary-card {
    margin-top: 18px;
  }

  .metrics,
  .timeline,
  .boundary-list,
  .risk-grid {
    grid-template-columns: 1fr;
  }

  .work-list {
    columns: 1;
  }
}
"""


def render_readme() -> str:
    return """# Codex Runtime Security Dashboard

This directory contains an offline HTML dashboard for the Codex Runtime
Security Prototype.

Generated files:

- `index.html`
- `dashboard_data.json`
- `style.css`

The dashboard is generated only from existing JSON and Markdown results. It
does not run Docker, Codex, strace, real samples, network-enabled commands, or
real-token workflows. It does not reference external CDN assets.

Regenerate locally with:

```bash
python3 code/scripts/generate_codex_runtime_security_dashboard.py
```
"""


def main() -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    data = build_data()
    DATA_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    HTML_PATH.write_text(render_html(data), encoding="utf-8")
    CSS_PATH.write_text(render_css(), encoding="utf-8")
    README_PATH.write_text(render_readme(), encoding="utf-8")
    print(f"Wrote {DATA_PATH.relative_to(ROOT)}")
    print(f"Wrote {HTML_PATH.relative_to(ROOT)}")
    print(f"Wrote {CSS_PATH.relative_to(ROOT)}")
    print(f"Wrote {README_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
