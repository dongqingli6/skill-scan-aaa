"""ASG unified CLI entry point.

Usage:
    python -m asg.asg_cli scan <skill_path> [--output-dir DIR] [--enable-claude] [--enable-honeypot]
    python -m asg.asg_cli scan-all-samples [--output-dir DIR] [--enable-claude]
    python -m asg.asg_cli build-dashboard [--output dashboard/dashboard_data.json]

The CLI performs a 4-layer analysis and writes a dashboard-compatible
JSON report:

    1. Static rule scan        (asg/rules.py — 17 paper-aligned patterns)
    2. Attack chain analysis   (asg/attack_chain.py — paper Table 11)
    3. Composite risk scoring  (asg/risk_scorer.py — math formula)
    4. Optional Claude eval    (asg/claude_runner.py — agent-in-the-loop)

Honeypot detection is integrated when --enable-honeypot is set: markers
are generated, optionally injected into a fake-HOME tree under the
output dir, and the Claude evaluator looks for marker leakage.

The CLI is fail-open: if anthropic SDK / API key is missing, the Claude
layer is skipped with a neutral score (0.5).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Module imports work whether invoked via `python -m asg.asg_cli ...`
# or `python asg/asg_cli.py ...`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asg import (
    attack_chain,
    claude_runner,
    dashboard_builder,
    honeypot,
    risk_scorer,
    rules,
    vm_evidence,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "analysis_results" / "asg"


# ============================================================
# Single-skill analysis
# ============================================================
def analyze_skill(
    skill_path: Path,
    output_dir: Path,
    enable_claude: bool = False,
    enable_honeypot: bool = False,
    claude_model: str = "claude-sonnet-4-5",
    vm_evidence_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the full 4-layer analysis for one skill.

    Writes:
        <output_dir>/<skill_name>/scan_result.json
        <output_dir>/<skill_name>/chain_result.json
        <output_dir>/<skill_name>/agent_eval.json
        <output_dir>/<skill_name>/honeypot_bundle.json
        <output_dir>/<skill_name>/asg_report.json    (canonical bundle)
    Returns the asg_report dict.
    """
    skill_path = Path(skill_path).resolve()
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill path does not exist: {skill_path}")

    skill_out = output_dir / skill_path.name
    skill_out.mkdir(parents=True, exist_ok=True)

    # === Layer 1: Static scan ===
    scan_result = rules.scan_skill_directory(skill_path)
    (skill_out / "scan_result.json").write_text(
        json.dumps(scan_result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # === Layer 2: Attack chain analysis ===
    chain_result = attack_chain.analyze(scan_result)
    (skill_out / "chain_result.json").write_text(
        json.dumps(chain_result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # === Layer 4 (computed before risk scoring): honeypot bundle ===
    honeypot_record: dict[str, Any] = {
        "enabled": enable_honeypot,
        "bundle": None,
        "any_honeypot_leaked": False,
    }
    honeypot_markers: list[str] = []
    if enable_honeypot:
        bundle = honeypot.generate_bundle()
        honeypot_record["bundle"] = bundle.to_dict()
        honeypot_markers = bundle.all_markers()
        (skill_out / "honeypot_bundle.json").write_text(
            json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # === Layer 3: Claude agent eval (live API OR ingested VM evidence) ===
    vm_record: dict[str, Any] | None = None
    if vm_evidence_dir:
        try:
            vm_record = vm_evidence.ingest_evidence_dir(
                vm_evidence_dir,
                honeypot_markers=honeypot_markers or None,
            )
            (skill_out / "vm_evidence.json").write_text(
                json.dumps(vm_record, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            agent_eval = vm_evidence.vm_evidence_to_agent_eval(vm_record)
            # Honeypot leak status from VM evidence overrides synthetic bundle
            if honeypot_record.get("enabled") and vm_record.get("honeypot_evidence", {}).get("any_honeypot_leaked"):
                honeypot_record["any_honeypot_leaked"] = True
                honeypot_record["leaked_from_vm_evidence"] = True
        except FileNotFoundError as exc:
            agent_eval = {
                "tested": False,
                "skipped_reason": f"vm_evidence_dir invalid: {exc}",
                "refusal_score": 0.5,
                "disclosure_score": 0.5,
                "compliance_signal": 0.0,
                "raw_response_preview": "",
                "model": claude_model,
            }
    elif enable_claude:
        agent_eval = claude_runner.evaluate_skill(
            skill_path=skill_path,
            honeypot_markers=honeypot_markers or None,
            model=claude_model,
        )
    else:
        agent_eval = {
            "tested": False,
            "skipped_reason": "--enable-claude not set and no VM evidence provided",
            "refusal_score": 0.5,
            "disclosure_score": 0.5,
            "compliance_signal": 0.0,
            "raw_response_preview": "",
            "model": claude_model,
        }
    (skill_out / "agent_eval.json").write_text(
        json.dumps(agent_eval, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # If honeypot ran AND Claude responded, check Claude's text for marker leakage.
    if (
        enable_honeypot
        and agent_eval.get("tested")
        and agent_eval.get("honeypot_response_leak_detected")
    ):
        honeypot_record["any_honeypot_leaked"] = True
        honeypot_record["leaked_markers"] = agent_eval.get(
            "honeypot_markers_leaked_in_response", []
        )

    # === Composite risk scoring ===
    risk = risk_scorer.compute_risk(
        scan_result=scan_result,
        chain_result=chain_result,
        agent_eval=agent_eval if agent_eval.get("tested") else None,
        honeypot_result=honeypot_record if enable_honeypot else None,
    )

    # === Layer 5: VM Docker Runtime evidence (if any) ===
    layer_5_runtime: dict[str, Any] = {"present": False}
    if vm_record:
        layer_5_runtime = {
            "present": True,
            "evidence_dir": vm_record.get("evidence_dir"),
            "mode": (
                "paper_no_claude"
                if not vm_record.get("claude", {}).get("output_path")
                else "agent_in_the_loop"
            ),
            "claude_output_present": bool(
                vm_record.get("claude", {}).get("output_path")
            ),
            "claude_output_size_chars": vm_record.get("claude", {}).get(
                "response_length_chars", 0
            ),
            "claude_output_preview": vm_record.get("claude", {}).get(
                "output_preview", ""
            )[:600],
            "strace": vm_record.get("strace", {}),
            "tcpdump": vm_record.get("tcpdump", {}),
            "filesystem": vm_record.get("filesystem", {}),
            "nova": vm_record.get("nova", {}),
        }

    asg_report = {
        "asg_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill_name": scan_result["skill_name"],
        "skill_path": scan_result["skill_path"],
        "layer_1_static_scan": {
            "total_findings": scan_result["total_findings"],
            "by_severity": scan_result["by_severity"],
            "by_pattern": scan_result["by_pattern"],
            "by_kill_chain_phase": scan_result["by_kill_chain_phase"],
            "rule_ids_hit": scan_result["rule_ids_hit"],
            "files_scanned_count": scan_result["files_scanned_count"],
        },
        "layer_2_attack_chain": chain_result,
        "layer_3_agent_eval": agent_eval,
        "layer_4_honeypot": honeypot_record,
        "layer_5_runtime": layer_5_runtime,
        "composite_risk": risk,
        "findings": scan_result["findings"],
    }
    (skill_out / "asg_report.json").write_text(
        json.dumps(asg_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return asg_report


# ============================================================
# Multi-skill batch
# ============================================================
def scan_all_samples(
    samples_root: Path,
    output_dir: Path,
    enable_claude: bool = False,
    enable_honeypot: bool = False,
) -> dict[str, Any]:
    """Walk the samples/ directory and run analyze_skill() on each subfolder
    containing a SKILL.md."""
    samples_root = Path(samples_root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, Any]] = []
    for entry in sorted(samples_root.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            report = analyze_skill(
                skill_path=entry,
                output_dir=output_dir,
                enable_claude=enable_claude,
                enable_honeypot=enable_honeypot,
            )
            reports.append(report)
        except Exception as exc:  # keep batch resilient
            reports.append(
                {
                    "skill_name": entry.name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    summary = build_batch_summary(reports)
    (output_dir / "batch_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def build_batch_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    by_verdict: dict[str, int] = {}
    by_archetype: dict[str, int] = {}
    by_soph_level: dict[str, int] = {}
    total_findings = 0
    total_chains = 0
    rows: list[dict[str, Any]] = []
    chain_counts: dict[str, int] = {}

    for r in reports:
        if "error" in r:
            rows.append({"skill_name": r["skill_name"], "error": r["error"]})
            continue
        verdict = r["composite_risk"]["verdict"]
        archetype = r["layer_2_attack_chain"]["archetype"]["archetype"]
        soph_label = r["layer_2_attack_chain"]["sophistication"]["label"]
        by_verdict[verdict] = by_verdict.get(verdict, 0) + 1
        by_archetype[archetype] = by_archetype.get(archetype, 0) + 1
        by_soph_level[soph_label] = by_soph_level.get(soph_label, 0) + 1
        total_findings += r["layer_1_static_scan"]["total_findings"]
        total_chains += r["layer_2_attack_chain"]["chain_count"]
        for chain in r["layer_2_attack_chain"]["chains_triggered"]:
            chain_counts[chain["chain_id"]] = chain_counts.get(chain["chain_id"], 0) + 1
        rows.append(
            {
                "skill_name": r["skill_name"],
                "composite_score": r["composite_risk"]["composite_score"],
                "verdict": verdict,
                "archetype": archetype,
                "sophistication": soph_label,
                "static_findings": r["layer_1_static_scan"]["total_findings"],
                "chains_triggered": r["layer_2_attack_chain"]["chain_count"],
                "agent_tested": r["layer_3_agent_eval"]["tested"],
                "agent_refusal_score": r["layer_3_agent_eval"]["refusal_score"],
                "honeypot_leaked": r["layer_4_honeypot"]["any_honeypot_leaked"],
            }
        )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_skills": len(reports),
        "total_static_findings": total_findings,
        "total_chains_triggered": total_chains,
        "by_verdict": by_verdict,
        "by_archetype": by_archetype,
        "by_sophistication_level": by_soph_level,
        "chain_trigger_counts": chain_counts,
        "rows": rows,
    }


# ============================================================
# Dashboard builder
# ============================================================
def build_dashboard_payload(
    batch_summary: dict[str, Any],
    existing_dashboard_path: Path | None = None,
) -> dict[str, Any]:
    """Merge ASG output into the existing Codex dashboard JSON, preserving
    teammate's fields."""
    base: dict[str, Any] = {}
    if existing_dashboard_path and existing_dashboard_path.exists():
        try:
            base = json.loads(existing_dashboard_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            base = {}

    base["asg_extension"] = {
        "version": "1.0.0",
        "generated_at_utc": batch_summary["generated_at_utc"],
        "module": "AgentSkillGuard (Claude-side integration)",
        "paper_alignment": "arXiv:2602.06547v2 Table 3/Table 9/Table 11",
        "rule_count": 17,
        "rule_breakdown": {"paper_original": 14, "asg_extensions": 3},
        "extension_rules": ["P5 Authority Impersonation", "P6 Persistence", "P7 Cross-tool Coercion"],
        "composite_score_formula": (
            "R = 100 * (0.25*S_static + 0.20*S_chain + 0.10*S_soph "
            "+ 0.10*S_phases + 0.25*(1 - S_resilience) + 0.10*S_honeypot)"
        ),
        "total_skills_evaluated": batch_summary["total_skills"],
        "total_static_findings": batch_summary["total_static_findings"],
        "total_chains_triggered": batch_summary["total_chains_triggered"],
        "by_verdict": batch_summary["by_verdict"],
        "by_archetype": batch_summary["by_archetype"],
        "by_sophistication_level": batch_summary["by_sophistication_level"],
        "chain_trigger_counts": batch_summary["chain_trigger_counts"],
        "skill_rows": batch_summary["rows"],
    }
    return base


# ============================================================
# CLI
# ============================================================
def _cmd_scan(args: argparse.Namespace) -> int:
    out = Path(args.output_dir or DEFAULT_OUTPUT_DIR)
    vm_dir = Path(args.vm_evidence_dir) if getattr(args, "vm_evidence_dir", None) else None
    report = analyze_skill(
        skill_path=Path(args.skill_path),
        output_dir=out,
        enable_claude=args.enable_claude,
        enable_honeypot=args.enable_honeypot,
        claude_model=args.claude_model,
        vm_evidence_dir=vm_dir,
    )
    print(json.dumps(
        {
            "skill_name": report["skill_name"],
            "composite_score": report["composite_risk"]["composite_score"],
            "verdict": report["composite_risk"]["verdict"],
            "archetype": report["layer_2_attack_chain"]["archetype"]["archetype"],
            "sophistication": report["layer_2_attack_chain"]["sophistication"]["label"],
            "chains_triggered": report["layer_2_attack_chain"]["chain_count"],
            "agent_tested": report["layer_3_agent_eval"]["tested"],
            "agent_refusal_score": report["layer_3_agent_eval"]["refusal_score"],
            "honeypot_leaked": report["layer_4_honeypot"]["any_honeypot_leaked"],
            "report_path": str(out / report["skill_name"] / "asg_report.json"),
        },
        indent=2,
        ensure_ascii=False,
    ))
    return 0


def _cmd_scan_all(args: argparse.Namespace) -> int:
    out = Path(args.output_dir or DEFAULT_OUTPUT_DIR)
    samples_root = Path(args.samples_root or REPO_ROOT / "asg" / "samples")
    summary = scan_all_samples(
        samples_root=samples_root,
        output_dir=out,
        enable_claude=args.enable_claude,
        enable_honeypot=args.enable_honeypot,
    )
    print(json.dumps(
        {k: v for k, v in summary.items() if k != "rows"},
        indent=2,
        ensure_ascii=False,
    ))
    print(f"\nBatch summary: {out / 'batch_summary.json'}")
    print(f"Per-skill reports: {out}/<skill_name>/asg_report.json")
    return 0


def _cmd_ingest_vm(args: argparse.Namespace) -> int:
    out = Path(args.output_dir or DEFAULT_OUTPUT_DIR)
    skill = Path(args.skill_path)
    evidence = Path(args.evidence_dir)
    if not evidence.exists():
        print(f"error: evidence dir does not exist: {evidence}", file=sys.stderr)
        return 1
    report = analyze_skill(
        skill_path=skill,
        output_dir=out,
        enable_claude=False,
        enable_honeypot=args.enable_honeypot,
        vm_evidence_dir=evidence,
    )
    print(json.dumps(
        {
            "skill_name": report["skill_name"],
            "composite_score": report["composite_risk"]["composite_score"],
            "verdict": report["composite_risk"]["verdict"],
            "agent_tested_from_vm": report["layer_3_agent_eval"].get("tested"),
            "refusal_score": report["layer_3_agent_eval"].get("refusal_score"),
            "disclosure_score": report["layer_3_agent_eval"].get("disclosure_score"),
            "evidence_dir": str(evidence),
            "report_path": str(out / report["skill_name"] / "asg_report.json"),
        },
        indent=2,
        ensure_ascii=False,
    ))
    return 0


def _cmd_vm_ssh_run(args: argparse.Namespace) -> int:
    from asg import vm_ssh

    cfg_path = Path(args.vm_config)
    if not cfg_path.exists():
        print(
            f"error: VM config not found at {cfg_path}.\n"
            "Create asg/vm_config.json with host/username/password/etc.",
            file=sys.stderr,
        )
        return 1
    try:
        cfg = vm_ssh.VMConfig.from_json(cfg_path)
    except (KeyError, json.JSONDecodeError) as exc:
        print(f"error: bad VM config: {exc}", file=sys.stderr)
        return 1

    skill = Path(args.skill_path).resolve()
    if not skill.is_dir():
        print(f"error: skill path not a directory: {skill}", file=sys.stderr)
        return 1

    out = Path(args.output_dir or DEFAULT_OUTPUT_DIR)
    ssh_log_dir = out / skill.name / "vm_ssh_logs"
    ssh_log_dir.mkdir(parents=True, exist_ok=True)

    print(f"[vm-ssh] Connecting to {cfg.host}:{cfg.port} as {cfg.username}...")
    ssh_result = vm_ssh.trigger_remote_run(
        config=cfg,
        skill_path_local=skill,
        timeout_seconds=args.timeout_seconds,
        local_log_dir=ssh_log_dir,
    )
    print(f"[vm-ssh] status={ssh_result.get('status')}")
    if ssh_result.get("status") not in ("completed", "completed_no_logs"):
        print(json.dumps(ssh_result, indent=2, ensure_ascii=False))
        return 2

    print(f"[vm-ssh] Ingesting evidence from {ssh_log_dir}...")
    report = analyze_skill(
        skill_path=skill,
        output_dir=out,
        enable_claude=False,
        enable_honeypot=args.enable_honeypot,
        vm_evidence_dir=ssh_log_dir,
    )
    print(json.dumps(
        {
            "skill_name": report["skill_name"],
            "composite_score": report["composite_risk"]["composite_score"],
            "verdict": report["composite_risk"]["verdict"],
            "agent_tested": report["layer_3_agent_eval"].get("tested"),
            "refusal_score": report["layer_3_agent_eval"].get("refusal_score"),
            "ssh_log_dir": str(ssh_log_dir),
        },
        indent=2,
        ensure_ascii=False,
    ))
    return 0


def _cmd_vm_paper_run(args: argparse.Namespace) -> int:
    """Paper-style direct Docker execution — no agent, no API key needed."""
    from asg import vm_ssh

    cfg_path = Path(args.vm_config)
    if not cfg_path.exists():
        print(f"error: VM config not found at {cfg_path}.", file=sys.stderr)
        return 1
    cfg = vm_ssh.VMConfig.from_json(cfg_path)

    skill = Path(args.skill_path).resolve()
    if not skill.is_dir():
        print(f"error: skill path not a directory: {skill}", file=sys.stderr)
        return 1

    out = Path(args.output_dir or DEFAULT_OUTPUT_DIR)
    paper_log_dir = out / skill.name / "vm_paper_logs"
    paper_log_dir.mkdir(parents=True, exist_ok=True)

    print(f"[vm-paper] Connecting to {cfg.host}:{cfg.port} as {cfg.username}...")
    result = vm_ssh.trigger_paper_mode_run(
        config=cfg,
        skill_path_local=skill,
        timeout_seconds=args.timeout_seconds,
        local_log_dir=paper_log_dir,
    )
    print(f"[vm-paper] status={result.get('status')}")
    if result.get("status") not in ("completed", "completed_no_logs"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2

    print(f"[vm-paper] Ingesting evidence from {paper_log_dir}...")
    report = analyze_skill(
        skill_path=skill,
        output_dir=out,
        enable_claude=False,
        enable_honeypot=args.enable_honeypot,
        vm_evidence_dir=paper_log_dir,
    )
    print(json.dumps(
        {
            "skill_name": report["skill_name"],
            "composite_score": report["composite_risk"]["composite_score"],
            "verdict": report["composite_risk"]["verdict"],
            "mode": "paper_no_claude",
            "scripts_executed": result.get("pulled_any_logs"),
            "paper_log_dir": str(paper_log_dir),
            "outbound_ips": report["layer_3_agent_eval"]
                .get("ingested_from_vm_evidence", False),
        },
        indent=2,
        ensure_ascii=False,
    ))
    return 0


def _cmd_build_html(args: argparse.Namespace) -> int:
    results_dir = Path(args.results_dir or DEFAULT_OUTPUT_DIR)
    output = Path(args.output or REPO_ROOT / "asg" / "dashboard.html")
    out_path = dashboard_builder.build_from_results(results_dir, output)
    print(f"Wrote: {out_path.resolve()}")
    return 0


def _cmd_build_dashboard(args: argparse.Namespace) -> int:
    out_dir = Path(args.output_dir or DEFAULT_OUTPUT_DIR)
    batch_path = out_dir / "batch_summary.json"
    if not batch_path.exists():
        print(f"error: {batch_path} not found. Run 'scan-all-samples' first.",
              file=sys.stderr)
        return 2
    batch_summary = json.loads(batch_path.read_text(encoding="utf-8"))

    dashboard_path = Path(args.dashboard_path or REPO_ROOT / "dashboard" / "dashboard_data.json")
    merged = build_dashboard_payload(batch_summary, existing_dashboard_path=dashboard_path)

    # Write to a separate asg_dashboard_data.json by default so teammate's
    # file stays untouched, unless --in-place is passed.
    target = dashboard_path if args.in_place else (
        REPO_ROOT / "dashboard" / "asg_dashboard_data.json"
    )
    target.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote merged dashboard data: {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="asg", description="AgentSkillGuard CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Scan one skill directory")
    p_scan.add_argument("skill_path")
    p_scan.add_argument("--output-dir", default=None)
    p_scan.add_argument("--enable-claude", action="store_true")
    p_scan.add_argument("--enable-honeypot", action="store_true")
    p_scan.add_argument("--claude-model", default="claude-sonnet-4-5")
    p_scan.add_argument(
        "--vm-evidence-dir",
        default=None,
        help="Path to a directory with claude_output.txt + strace.log from VM Docker run",
    )
    p_scan.set_defaults(func=_cmd_scan)

    p_all = sub.add_parser("scan-all-samples", help="Scan every sample in asg/samples/")
    p_all.add_argument("--samples-root", default=None)
    p_all.add_argument("--output-dir", default=None)
    p_all.add_argument("--enable-claude", action="store_true")
    p_all.add_argument("--enable-honeypot", action="store_true")
    p_all.set_defaults(func=_cmd_scan_all)

    p_dash = sub.add_parser("build-dashboard", help="Merge ASG output into dashboard JSON")
    p_dash.add_argument("--output-dir", default=None,
                        help="Directory containing batch_summary.json")
    p_dash.add_argument("--dashboard-path", default=None,
                        help="Existing dashboard_data.json to extend")
    p_dash.add_argument("--in-place", action="store_true",
                        help="Overwrite teammate's dashboard_data.json directly")
    p_dash.set_defaults(func=_cmd_build_dashboard)

    p_html = sub.add_parser("build-html", help="Build standalone ASG HTML dashboard")
    p_html.add_argument("--results-dir", default=None,
                        help="Directory containing per-skill asg_report.json files")
    p_html.add_argument("--output", default=None,
                        help="Output HTML path (default: asg/dashboard.html)")
    p_html.set_defaults(func=_cmd_build_html)

    p_ingest = sub.add_parser(
        "ingest-vm-evidence",
        help="Ingest claude_output.txt + strace.log + tcpdump.pcap from a VM Docker run",
    )
    p_ingest.add_argument("skill_path", help="Original skill directory (for static scan)")
    p_ingest.add_argument(
        "evidence_dir",
        help="VM-side directory containing claude_output.txt etc",
    )
    p_ingest.add_argument("--output-dir", default=None)
    p_ingest.add_argument("--enable-honeypot", action="store_true")
    p_ingest.set_defaults(func=_cmd_ingest_vm)

    p_ssh = sub.add_parser(
        "vm-ssh-run",
        help="SSH to remote VM, trigger run_skill.sh, pull logs back, then ingest",
    )
    p_ssh.add_argument("skill_path", help="Local skill directory to upload + run")
    p_ssh.add_argument(
        "--vm-config",
        default="asg/vm_config.json",
        help="Path to VM SSH config JSON (host, user, password, etc.)",
    )
    p_ssh.add_argument("--output-dir", default=None)
    p_ssh.add_argument("--enable-honeypot", action="store_true")
    p_ssh.add_argument("--timeout-seconds", type=int, default=300)
    p_ssh.set_defaults(func=_cmd_vm_ssh_run)

    p_paper = sub.add_parser(
        "vm-paper-run",
        help="SSH to VM, run skill scripts DIRECTLY in Docker (NO Claude / NO API).",
    )
    p_paper.add_argument("skill_path", help="Local skill directory to upload + run")
    p_paper.add_argument("--vm-config", default="asg/vm_config.json")
    p_paper.add_argument("--output-dir", default=None)
    p_paper.add_argument("--enable-honeypot", action="store_true")
    p_paper.add_argument("--timeout-seconds", type=int, default=60)
    p_paper.set_defaults(func=_cmd_vm_paper_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
