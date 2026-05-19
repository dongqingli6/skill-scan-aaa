"""Build a self-contained HTML dashboard from ASG batch results.

Writes a single static HTML file (no JS framework, no external CSS) that
visualizes:
  - Composite risk score per skill (color-coded gauge)
  - Archetype distribution
  - Attack-chain hits (paper Table 11)
  - Score formula breakdown (transparent reproducibility)
  - Layer-by-layer evidence per skill (static / chain / agent / honeypot)

Designed to be opened by double-clicking the resulting HTML.
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any


VERDICT_COLOR = {
    "SAFE": "#22c55e",
    "SUSPICIOUS": "#f59e0b",
    "MALICIOUS": "#ef4444",
    "CRITICAL_MALICIOUS": "#7c1d1d",
}

ARCHETYPE_COLOR = {
    "Benign": "#22c55e",
    "Partial-Risk": "#f59e0b",
    "Data Thief": "#ef4444",
    "Agent Hijacker": "#8b5cf6",
    "Hybrid": "#ec4899",
    "Platform-Native": "#06b6d4",
}


def _escape(value: Any) -> str:
    return html.escape(str(value))


def _gauge_html(score: float, verdict: str) -> str:
    color = VERDICT_COLOR.get(verdict, "#888")
    pct = max(0.0, min(100.0, score))
    return f"""
    <div class="gauge">
      <div class="gauge-track">
        <div class="gauge-fill" style="width: {pct}%; background: {color};"></div>
      </div>
      <div class="gauge-label" style="color: {color};">
        {pct:.1f} <span class="verdict-tag">{_escape(verdict)}</span>
      </div>
    </div>
    """


def _bar_chart(counts: dict[str, int], color_map: dict[str, str]) -> str:
    if not counts:
        return '<div class="empty">No data</div>'
    max_v = max(counts.values()) or 1
    rows = []
    for label, value in counts.items():
        color = color_map.get(label, "#666")
        pct = (value / max_v) * 100.0
        rows.append(
            f'<div class="bar-row">'
            f'<div class="bar-label">{_escape(label)}</div>'
            f'<div class="bar-track">'
            f'<div class="bar-fill" style="width: {pct}%; background: {color};">{value}</div>'
            f'</div></div>'
        )
    return "\n".join(rows)


def _sub_score_table(report: dict[str, Any]) -> str:
    risk = report["composite_risk"]
    sub = risk["sub_scores"]
    weights = risk["weights"]
    rows = []
    components = [
        ("S_static", "Static rule severity", weights.get("w_static", 0.25)),
        ("S_chain", "Attack chain hit", weights.get("w_chain", 0.20)),
        ("S_soph", "Sophistication level", weights.get("w_soph", 0.10)),
        ("S_phases", "Kill-chain phase coverage", weights.get("w_phases", 0.10)),
        ("S_resilience", "Agent resilience (1 - this = risk)", weights.get("w_agent", 0.25)),
        ("S_honeypot", "Honeypot exfiltrated", weights.get("w_honeypot", 0.10)),
    ]
    for key, label, weight in components:
        val = sub.get(key, 0.0)
        contribution = (1.0 - val) * weight * 100 if key == "S_resilience" else val * weight * 100
        rows.append(
            f"<tr><td>{_escape(label)}</td>"
            f"<td><code>{key}</code></td>"
            f"<td>{val:.3f}</td>"
            f"<td>{weight:.2f}</td>"
            f"<td><strong>{contribution:.2f}</strong></td></tr>"
        )
    return f"""
    <table class="formula">
      <thead><tr><th>Component</th><th>Symbol</th><th>Value</th><th>Weight</th><th>Contribution</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def _findings_table(report: dict[str, Any], limit: int = 12) -> str:
    findings = report.get("findings", [])[:limit]
    if not findings:
        return '<div class="empty">No static findings.</div>'
    rows = []
    for f in findings:
        severity_class = f.get("severity", "LOW").lower()
        rows.append(
            f"<tr>"
            f'<td><span class="sev-pill sev-{severity_class}">{_escape(f.get("severity",""))}</span></td>'
            f"<td><code>{_escape(f.get('rule_id',''))}</code></td>"
            f"<td>{_escape(f.get('kill_chain_phase',''))}</td>"
            f"<td><code>{_escape(f.get('file',''))}:{_escape(f.get('line',''))}</code></td>"
            f"<td><code class=\"snippet\">{_escape(f.get('matched_text','')[:80])}</code></td>"
            f"</tr>"
        )
    extra = ""
    if len(report.get("findings", [])) > limit:
        extra = f'<tr><td colspan="5" class="muted">... ({len(report["findings"]) - limit} more findings)</td></tr>'
    return f"""
    <table class="findings">
      <thead><tr><th>Severity</th><th>Rule</th><th>Phase</th><th>Location</th><th>Match</th></tr></thead>
      <tbody>{''.join(rows)}{extra}</tbody>
    </table>
    """


def _chain_pills(report: dict[str, Any]) -> str:
    chains = report["layer_2_attack_chain"]["chains_triggered"]
    if not chains:
        return '<div class="empty">No attack chains triggered.</div>'
    pills = []
    for c in chains:
        pills.append(
            f'<div class="chain-pill">'
            f'<div class="chain-id">{_escape(c["chain_id"])}</div>'
            f'<div class="chain-name">{_escape(c["name"])}</div>'
            f'<div class="chain-evidence">{_escape(c["paper_evidence"])}</div>'
            f'</div>'
        )
    return f'<div class="chain-pills">{"".join(pills)}</div>'


def _agent_eval_panel(report: dict[str, Any]) -> str:
    ae = report["layer_3_agent_eval"]
    if not ae.get("tested"):
        reason = _escape(ae.get("skipped_reason", "not tested"))
        return f'<div class="agent-not-tested">Agent layer not tested — <em>{reason}</em></div>'
    refusal = ae.get("refusal_score", 0)
    disclosure = ae.get("disclosure_score", 0)
    compliance = ae.get("compliance_signal", 0)
    return f"""
    <div class="agent-scores">
      <div class="agent-score"><span>Refusal</span><strong>{refusal:.2f}</strong></div>
      <div class="agent-score"><span>Disclosure</span><strong>{disclosure:.2f}</strong></div>
      <div class="agent-score"><span>Compliance</span><strong>{compliance:.2f}</strong></div>
    </div>
    <details>
      <summary>Claude response preview</summary>
      <pre class="claude-preview">{_escape(ae.get("raw_response_preview", ""))}</pre>
    </details>
    """


def _runtime_panel(report: dict[str, Any]) -> str:
    rt = report.get("layer_5_runtime", {}) or {}
    if not rt.get("present"):
        return '<div class="empty">No VM Docker runtime evidence ingested.</div>'

    mode = rt.get("mode", "unknown")
    mode_color = "#22c55e" if mode == "agent_in_the_loop" else "#f59e0b"
    mode_label = (
        "Mode B: Claude-in-Docker"
        if mode == "agent_in_the_loop"
        else "Mode C: Paper-mode (no Claude)"
    )

    strace = rt.get("strace", {}) or {}
    tcpdump = rt.get("tcpdump", {}) or {}
    fs = rt.get("filesystem", {}) or {}

    rows = []
    rows.append(
        f'<tr><td>strace.log present</td>'
        f'<td><strong>{"yes" if strace.get("log_present") else "no"}</strong></td>'
        f'<td>{strace.get("log_size_bytes", 0):,} bytes</td></tr>'
    )
    rows.append(
        f'<tr><td>sensitive file access calls</td>'
        f'<td><strong>{strace.get("sensitive_file_access_count", 0)}</strong></td>'
        f'<td>open(~/.ssh, .aws, .env) etc.</td></tr>'
    )
    rows.append(
        f'<tr><td>outbound connect attempts</td>'
        f'<td><strong>{strace.get("outbound_connect_count", 0)}</strong></td>'
        f'<td>connect() to non-local</td></tr>'
    )
    unique_ips = strace.get("unique_outbound_ips", [])
    if unique_ips:
        rows.append(
            f'<tr><td>unique outbound IPs</td>'
            f'<td><strong>{len(unique_ips)}</strong></td>'
            f'<td><code>{", ".join(unique_ips[:6])}</code></td></tr>'
        )
    rows.append(
        f'<tr><td>network.pcap present</td>'
        f'<td><strong>{"yes" if tcpdump.get("pcap_present") else "no"}</strong></td>'
        f'<td>{tcpdump.get("pcap_size_bytes", 0):,} bytes</td></tr>'
    )
    rows.append(
        f'<tr><td>filesystem changes</td>'
        f'<td><strong>{"yes" if fs.get("fs_change_present") else "no"}</strong></td>'
        f'<td>fs diff captured</td></tr>'
    )

    table = f"""
    <table class="findings">
      <thead><tr><th>Signal</th><th>Value</th><th>Note</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """

    preview = ""
    if rt.get("claude_output_present"):
        preview = (
            "<details><summary>Claude response preview (from VM container)</summary>"
            f"<pre class=\"claude-preview\">{_escape(rt.get('claude_output_preview', ''))}</pre>"
            "</details>"
        )

    return f"""
    <div class="honeypot-status">
      Runtime mode:
      <span style="background:{mode_color};color:#0f172a;padding:2px 10px;border-radius:4px;font-weight:600;">
        {mode_label}
      </span>
      &nbsp; Evidence dir: <code>{_escape(rt.get('evidence_dir', ''))}</code>
    </div>
    {table}
    {preview}
    """


def _honeypot_panel(report: dict[str, Any]) -> str:
    hp = report["layer_4_honeypot"]
    if not hp.get("enabled"):
        return '<div class="empty">Honeypot not enabled.</div>'
    leaked = hp.get("any_honeypot_leaked", False)
    badge = (
        '<span class="hp-leaked">LEAKED</span>'
        if leaked
        else '<span class="hp-clean">CLEAN</span>'
    )
    bundle = hp.get("bundle", {})
    bundle_id = bundle.get("bundle_id", "?") if bundle else "?"
    return f"""
    <div class="honeypot-status">Status: {badge} (bundle_id: <code>{_escape(bundle_id)}</code>)</div>
    """


def _skill_card(report: dict[str, Any]) -> str:
    name = report["skill_name"]
    archetype = report["layer_2_attack_chain"]["archetype"]["archetype"]
    archetype_color = ARCHETYPE_COLOR.get(archetype, "#666")
    soph = report["layer_2_attack_chain"]["sophistication"]
    risk = report["composite_risk"]
    return f"""
    <article class="skill-card" id="skill-{_escape(name)}">
      <header class="skill-header">
        <h3>{_escape(name)}</h3>
        <span class="archetype-tag" style="background: {archetype_color};">{_escape(archetype)}</span>
        <span class="soph-tag">L{soph['level']} {_escape(soph['label'])}</span>
      </header>

      {_gauge_html(risk["composite_score"], risk["verdict"])}

      <details open>
        <summary>Composite score breakdown — <code>{_escape(risk["formula"][:80])}</code>...</summary>
        {_sub_score_table(report)}
      </details>

      <section>
        <h4>Layer 1 — Static rule findings ({report["layer_1_static_scan"]["total_findings"]})</h4>
        {_findings_table(report)}
      </section>

      <section>
        <h4>Layer 2 — Attack chains</h4>
        {_chain_pills(report)}
      </section>

      <section>
        <h4>Layer 3 — Agent-in-the-loop (Claude)</h4>
        {_agent_eval_panel(report)}
      </section>

      <section>
        <h4>Layer 4 — Honeypot</h4>
        {_honeypot_panel(report)}
      </section>

      <section>
        <h4>Layer 5 — VM Docker Runtime ★</h4>
        {_runtime_panel(report)}
      </section>
    </article>
    """


CSS = """
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
  margin: 0;
  background: #0f172a;
  color: #e2e8f0;
  line-height: 1.5;
}
header.topbar {
  background: linear-gradient(135deg, #1e293b, #334155);
  padding: 24px 32px;
  border-bottom: 3px solid #38bdf8;
}
header.topbar h1 {
  margin: 0;
  font-size: 28px;
  color: #f1f5f9;
}
header.topbar .subtitle {
  color: #94a3b8;
  margin-top: 8px;
}
.eyebrow {
  color: #38bdf8;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 12px;
}
main { padding: 24px 32px; max-width: 1400px; margin: 0 auto; }
.section-title { font-size: 20px; margin: 24px 0 12px; color: #f8fafc; border-left: 4px solid #38bdf8; padding-left: 12px; }
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.summary-card {
  background: #1e293b;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid #334155;
}
.summary-card span { display: block; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
.summary-card strong { font-size: 28px; color: #f8fafc; }
.panel {
  background: #1e293b;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid #334155;
  margin-bottom: 20px;
}
.panel h2 { margin-top: 0; color: #f1f5f9; }
.bar-row { display: flex; align-items: center; margin-bottom: 6px; }
.bar-label { width: 160px; font-size: 13px; color: #cbd5e1; }
.bar-track { flex: 1; background: #0f172a; height: 24px; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; color: white; text-align: right; padding-right: 8px; font-size: 12px; line-height: 24px; min-width: 32px; }
.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 16px;
}
.skill-card {
  background: #1e293b;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid #334155;
}
.skill-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.skill-header h3 { margin: 0; flex: 1; font-size: 16px; color: #f1f5f9; }
.archetype-tag { padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; color: white; }
.soph-tag { padding: 4px 10px; border-radius: 999px; font-size: 11px; background: #475569; color: #e2e8f0; }
.gauge { margin: 8px 0 16px; }
.gauge-track { height: 12px; background: #0f172a; border-radius: 6px; overflow: hidden; }
.gauge-fill { height: 100%; transition: width 0.4s; }
.gauge-label { margin-top: 4px; font-size: 22px; font-weight: 700; }
.verdict-tag { font-size: 12px; padding: 2px 8px; border-radius: 4px; background: rgba(255,255,255,0.08); margin-left: 6px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: #94a3b8; font-weight: 500; padding: 6px 8px; border-bottom: 1px solid #334155; }
td { padding: 6px 8px; border-bottom: 1px solid #1e293b; vertical-align: top; }
.sev-pill { padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; color: white; }
.sev-critical { background: #ef4444; }
.sev-high     { background: #f97316; }
.sev-medium   { background: #f59e0b; }
.sev-low      { background: #64748b; }
.snippet { font-size: 11px; color: #94a3b8; }
.chain-pills { display: flex; flex-direction: column; gap: 8px; }
.chain-pill { background: #0f172a; padding: 10px; border-radius: 6px; border-left: 3px solid #38bdf8; }
.chain-id { font-family: monospace; font-size: 12px; color: #38bdf8; }
.chain-name { font-weight: 600; color: #f1f5f9; margin-top: 2px; }
.chain-evidence { color: #94a3b8; font-size: 11px; margin-top: 2px; }
.agent-not-tested { color: #94a3b8; font-style: italic; padding: 8px; background: #0f172a; border-radius: 4px; }
.agent-scores { display: flex; gap: 12px; margin-bottom: 8px; }
.agent-score { background: #0f172a; padding: 8px 12px; border-radius: 6px; flex: 1; text-align: center; }
.agent-score span { display: block; color: #94a3b8; font-size: 11px; }
.agent-score strong { font-size: 20px; color: #f8fafc; }
.claude-preview {
  background: #0f172a; padding: 12px; border-radius: 4px;
  font-size: 11px; color: #cbd5e1;
  max-height: 180px; overflow-y: auto; white-space: pre-wrap;
}
.honeypot-status { font-size: 13px; }
.hp-leaked { background: #ef4444; color: white; padding: 2px 10px; border-radius: 4px; font-weight: 600; }
.hp-clean { background: #22c55e; color: white; padding: 2px 10px; border-radius: 4px; font-weight: 600; }
.empty { color: #64748b; font-style: italic; padding: 8px 0; }
.muted { color: #64748b; }
.formula { background: #0f172a; padding: 8px; border-radius: 4px; }
.formula td { font-size: 12px; }
.formula code { color: #38bdf8; }
details { margin: 8px 0; }
summary { cursor: pointer; padding: 8px 0; color: #94a3b8; font-size: 13px; }
summary:hover { color: #38bdf8; }
section { margin: 12px 0; }
section h4 { margin: 8px 0; color: #cbd5e1; font-size: 14px; }
code { background: #0f172a; padding: 2px 4px; border-radius: 3px; font-size: 12px; }
.footer { text-align: center; padding: 32px; color: #64748b; font-size: 12px; }
.formula-box { background: #0f172a; padding: 16px; border-radius: 8px; font-family: monospace; font-size: 13px; color: #38bdf8; border-left: 3px solid #38bdf8; }
"""


def build_html(batch_summary: dict[str, Any], reports: list[dict[str, Any]]) -> str:
    skill_cards = "\n".join(_skill_card(r) for r in reports)

    verdict_bars = _bar_chart(batch_summary["by_verdict"], VERDICT_COLOR)
    archetype_bars = _bar_chart(batch_summary["by_archetype"], ARCHETYPE_COLOR)
    chain_bars = _bar_chart(batch_summary["chain_trigger_counts"], {})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ASG — AgentSkillGuard Dashboard</title>
  <style>{CSS}</style>
</head>
<body>
  <header class="topbar">
    <div class="eyebrow">AgentSkillGuard · Claude-side Extension to Codex Runtime Security</div>
    <h1>ASG Risk Dashboard</h1>
    <div class="subtitle">
      From "is the skill malicious?" to "will the agent be fooled?" ·
      Paper alignment: arXiv:2602.06547v2 (14 patterns + 3 ASG extensions)
    </div>
  </header>

  <main>
    <section class="summary-cards">
      <div class="summary-card"><span>Skills Evaluated</span><strong>{batch_summary["total_skills"]}</strong></div>
      <div class="summary-card"><span>Static Findings</span><strong>{batch_summary["total_static_findings"]}</strong></div>
      <div class="summary-card"><span>Chains Triggered</span><strong>{batch_summary["total_chains_triggered"]}</strong></div>
      <div class="summary-card"><span>Generated (UTC)</span><strong style="font-size:13px;">{_escape(batch_summary["generated_at_utc"][:19])}</strong></div>
    </section>

    <h2 class="section-title">Composite Risk Formula</h2>
    <div class="formula-box">
      R = 100 · (
      0.25·S<sub>static</sub> + 0.20·S<sub>chain</sub> + 0.10·S<sub>soph</sub>
      + 0.10·S<sub>phases</sub> + 0.25·(1 − S<sub>resilience</sub>)
      + 0.10·S<sub>honeypot</sub>
      )
    </div>

    <h2 class="section-title">Distribution Overview</h2>
    <div class="panel">
      <h2>Verdict</h2>
      {verdict_bars}
    </div>
    <div class="panel">
      <h2>Archetype (paper §4.2)</h2>
      {archetype_bars}
    </div>
    <div class="panel">
      <h2>Attack Chain Trigger Counts (paper Table 11)</h2>
      {chain_bars}
    </div>

    <h2 class="section-title">Per-Skill Reports</h2>
    <div class="skills-grid">
      {skill_cards}
    </div>
  </main>

  <div class="footer">
    Generated by ASG (AgentSkillGuard) v1.0 · A Claude-side integration on top of the Codex Runtime Security Prototype.
  </div>
</body>
</html>
"""


def build_from_results(results_dir: Path, output_html: Path) -> Path:
    """Read every asg_report.json under results_dir/<skill>/, build dashboard."""
    results_dir = Path(results_dir).resolve()
    reports: list[dict[str, Any]] = []
    for d in sorted(results_dir.iterdir()):
        if not d.is_dir():
            continue
        p = d / "asg_report.json"
        if not p.exists():
            continue
        try:
            reports.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue

    batch_path = results_dir / "batch_summary.json"
    if batch_path.exists():
        batch_summary = json.loads(batch_path.read_text(encoding="utf-8"))
    else:
        batch_summary = {
            "generated_at_utc": datetime.utcnow().isoformat(),
            "total_skills": len(reports),
            "total_static_findings": 0,
            "total_chains_triggered": 0,
            "by_verdict": {},
            "by_archetype": {},
            "chain_trigger_counts": {},
        }

    html_text = build_html(batch_summary, reports)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html_text, encoding="utf-8")
    return output_html


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build ASG dashboard HTML")
    parser.add_argument("--results-dir", default="analysis_results/asg")
    parser.add_argument("--output", default="asg/dashboard.html")
    args = parser.parse_args()

    out = build_from_results(Path(args.results_dir), Path(args.output))
    print(f"Wrote: {out.resolve()}")
