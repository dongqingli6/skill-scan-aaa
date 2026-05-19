#!/usr/bin/env python3
"""Unified static-only Agent Skill scanner CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

CODE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = CODE_ROOT.parent
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from core.report_writer import write_markdown_report
from core.safety_guard import (
    assert_no_real_codex_home,
    assert_no_real_home,
    assert_no_token_env,
    assert_static_only,
    deny_dynamic_execution_unless_explicit,
)
from core.schema_validation import validate_jsonl, validate_static, validate_summary
from platforms.codex.analyzer_adapter import analyze_codex_record_static_only
from platforms.codex.sandbox.run_plan import build_codex_run_plan
from platforms.codex.sandbox.sandbox_models import CodexRunQueueItem
from platforms.codex.sandbox.docker_smoke_plan import build_docker_safe_smoke_plan
from platforms.codex.sandbox.smoke_runner import prepare_codex_safe_smoke_test, run_codex_safe_smoke_test
from platforms.codex.sandbox.smoke_models import CodexSmokeTestConfig
from platforms.codex.static_scan import build_static_scan_result


DEFAULT_DYNAMIC_EVIDENCE_PATH = "analysis_results/codex_dynamic_security_report/dynamic_security_report.json"


def _resolve_repo_path(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    return candidate.resolve()


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_dynamic_evidence(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "included": False,
            "path": str(path),
            "warning": "dynamic evidence file was requested but does not exist",
        }
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "included": False,
            "path": str(path),
            "warning": f"dynamic evidence file is not valid JSON: {exc}",
        }
    if not isinstance(evidence, dict):
        return {
            "included": False,
            "path": str(path),
            "warning": "dynamic evidence file must contain a JSON object",
        }
    return {
        "included": True,
        "path": str(path),
        "summary": {
            "dynamic_execution_performed": evidence.get("dynamic_execution_performed"),
            "malicious_samples_executed": evidence.get("malicious_samples_executed"),
            "docker_network_mode": evidence.get("docker_network_mode"),
            "real_tokens_present": evidence.get("real_tokens_present"),
            "sample_mount": evidence.get("sample_mount"),
            "output_mount": evidence.get("output_mount"),
            "codex_bundle_mount": evidence.get("codex_bundle_mount"),
            "risk_summary": evidence.get("risk_summary", {}),
            "final_verdict": evidence.get("final_verdict", ""),
        },
    }


def _build_codex_queue(static_scan: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for skill in static_scan.get("skills", []):
        rows.append(
            {
                "platform": "codex",
                "mode": "static-only",
                "skill_name": skill.get("skill_name", ""),
                "source_path": skill.get("source_path", ""),
                "skill_md_path": skill.get("skill_md_path", ""),
                "agents_md_path": skill.get("agents_md_path"),
                "openai_yaml_path": skill.get("openai_yaml_path"),
                "scripts_paths": skill.get("scripts_paths", []),
                "risk_hint": skill.get("classification", "unknown"),
                "allow_dynamic_execution": False,
            }
        )
    return rows


def _summarize(audit_rows: List[Dict[str, Any]], total_findings: int) -> Dict[str, Any]:
    by_severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    by_classification: Dict[str, int] = {}
    for row in audit_rows:
        severity = row.get("severity", "LOW")
        if severity in by_severity:
            by_severity[severity] += 1
        classification = row.get("classification", "unknown")
        by_classification[classification] = by_classification.get(classification, 0) + 1
    return {
        "platform": "codex",
        "mode": "static-only",
        "total_skills": len(audit_rows),
        "total_findings": total_findings,
        "by_severity": by_severity,
        "by_classification": by_classification,
        "dynamic_execution_enabled": False,
    }


def run_codex_static(root: Path, output_dir: Path, dynamic_evidence_path: Path | None = None) -> Dict[str, Path]:
    static_scan = build_static_scan_result(root)

    static_path = output_dir / "static_scan_results.json"
    queue_path = output_dir / "queues" / "codex_analysis_queue.jsonl"
    audit_path = output_dir / "agent_audit_results.jsonl"
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "report.md"

    _write_json(static_path, static_scan)
    queue_rows = _build_codex_queue(static_scan)
    _write_jsonl(queue_path, queue_rows)

    audit_rows = [analyze_codex_record_static_only(row) for row in queue_rows]
    _write_jsonl(audit_path, audit_rows)

    summary = _summarize(audit_rows, static_scan.get("summary", {}).get("total_findings", 0))
    if dynamic_evidence_path:
        summary["dynamic_evidence"] = _load_dynamic_evidence(dynamic_evidence_path)
    _write_json(summary_path, summary)

    validate_static(static_path)
    validate_jsonl(queue_path)
    validate_jsonl(audit_path)
    validate_summary(summary_path)

    write_markdown_report(
        static_scan_path=static_path,
        audit_jsonl_path=audit_path,
        summary_path=summary_path,
        output_path=report_path,
        dynamic_evidence_path=dynamic_evidence_path,
    )

    return {
        "static_scan_results": static_path,
        "queue": queue_path,
        "agent_audit_results": audit_path,
        "summary": summary_path,
        "report": report_path,
    }


def run_codex_sandbox_plan_only(root: Path, output_dir: Path) -> Dict[str, Path]:
    """Generate sandbox plans for discovered Codex skills without execution."""
    static_scan = build_static_scan_result(root)
    static_path = output_dir / "static_scan_results.json"
    _write_json(static_path, static_scan)

    queue_path = output_dir / "codex_run_queue.jsonl"
    queue_rows = []
    for skill in static_scan.get("skills", []):
        skill_name = skill.get("skill_name") or Path(skill["source_path"]).name
        skill_output = output_dir / skill_name
        plan_result = build_codex_run_plan(
            skill_path=skill["source_path"],
            output_dir=skill_output,
            allow_dynamic_execution=False,
            allowed_root=root,
        )
        queue_rows.append(
            CodexRunQueueItem(
                platform="codex",
                skill_name=skill_name,
                skill_path=skill["source_path"],
                run_plan_path=plan_result["run_plan_path"],
                preflight_path=plan_result["preflight_path"],
                allow_dynamic_execution=False,
                network_enabled=False,
                fake_home_required=True,
                real_home_allowed=False,
                real_tokens_allowed=False,
            ).to_dict()
        )
    _write_jsonl(queue_path, queue_rows)

    summary_path = output_dir / "summary.json"
    summary = {
        "platform": "codex",
        "mode": "dynamic-plan-only",
        "total_skills": len(queue_rows),
        "total_findings": static_scan.get("summary", {}).get("total_findings", 0),
        "by_severity": static_scan.get("summary", {}).get("by_severity", {}),
        "by_classification": {},
        "dynamic_execution_requested": True,
        "dynamic_execution_performed": False,
        "sandbox_plan_generated": True,
    }
    _write_json(summary_path, summary)

    report_path = output_dir / "report.md"
    report_lines = [
        "# Codex Sandbox Plan-Only Report",
        "",
        "- Platform: `codex`",
        f"- Scan root: `{root}`",
        "- dynamic_execution_requested: `true`",
        "- dynamic_execution_performed: `false`",
        "- sandbox_plan_generated: `true`",
        f"- Planned skills: `{len(queue_rows)}`",
        "",
        "## Plans",
        "",
    ]
    for row in queue_rows:
        plan = json.loads(Path(row["run_plan_path"]).read_text(encoding="utf-8"))
        report_lines.extend(
            [
                f"### {row['skill_name']}",
                "",
                f"- Fake HOME path: `{plan.get('fake_home')}`",
                f"- Fake CODEX_HOME path: `{plan.get('fake_codex_home')}`",
                f"- Network enabled: `{plan.get('network_enabled')}`",
                "- Real HOME allowed: `false`",
                "- Real tokens allowed: `false`",
                "- dynamic_execution_performed: `false`",
                "",
            ]
        )
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "static_scan_results": static_path,
        "run_queue": queue_path,
        "summary": summary_path,
        "report": report_path,
    }


def run_codex_safe_smoke_plan(root: Path, output_dir: Path, allow_codex_exec: bool, safe_skill_only: bool) -> Dict[str, Path]:
    """Prepare safe_skill smoke test and fail closed unless manual gates are open."""
    prepared = prepare_codex_safe_smoke_test(
        skill_path=root,
        output_dir=output_dir,
        enabled=allow_codex_exec,
        allow_codex_exec=allow_codex_exec,
        safe_skill_only=safe_skill_only,
    )
    config: CodexSmokeTestConfig = prepared["config"]
    result = run_codex_safe_smoke_test(config)
    result_path = output_dir / "smoke_test_result.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = output_dir / "report.md"
    report_lines = [
        "# Codex Safe Smoke Test Report",
        "",
        "- safe_smoke_test_requested: `true`",
        f"- safe_smoke_test_performed: `{str(result.get('performed', False)).lower()}`",
        f"- safe_smoke_test_success: `{str(result.get('success', False)).lower()}`",
        f"- stdout_path: `{result.get('stdout_path', '')}`",
        f"- stderr_path: `{result.get('stderr_path', '')}`",
        "",
        "Current report中的 safe smoke test 不代表恶意样本动态验证。",
        "",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return {
        "smoke_test_plan": output_dir / "smoke_test_plan.json",
        "smoke_test_result": result_path,
        "report": report_path,
    }


def run_codex_docker_smoke_plan(root: Path, output_dir: Path) -> Dict[str, Path]:
    """Generate Docker safe smoke plan-only artifacts."""
    result = build_docker_safe_smoke_plan(skill_path=root, output_dir=output_dir)
    report_path = output_dir / "report.md"
    plan = result["plan"]
    preflight = result["preflight"]
    report_lines = [
        "# Codex Docker Safe Smoke Plan",
        "",
        f"- plan_only: `{plan.get('plan_only')}`",
        f"- docker_build_allowed: `{plan.get('docker_build_allowed')}`",
        f"- docker_run_allowed: `{plan.get('docker_run_allowed')}`",
        f"- codex_exec_allowed: `{plan.get('codex_exec_allowed')}`",
        f"- network_mode: `{plan.get('network_mode')}`",
        f"- sample_mount_mode: `{plan.get('sample_mount_mode')}`",
        f"- output_mount_mode: `{plan.get('output_mount_mode')}`",
        f"- fake_home_inside_container: `{plan.get('fake_home_inside_container')}`",
        f"- fake_codex_home_inside_container: `{plan.get('fake_codex_home_inside_container')}`",
        f"- command_preview: `{plan.get('command_preview')}`",
        f"- preflight_ok: `{preflight.get('ok')}`",
        f"- errors: `{preflight.get('errors')}`",
        f"- warnings: `{preflight.get('warnings')}`",
        "",
        "当前 Docker smoke plan 没有 build 镜像、没有启动容器、没有执行 Codex。",
        "",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return {
        "docker_smoke_plan": Path(result["plan_path"]),
        "docker_preflight": Path(result["preflight_path"]),
        "report": report_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified Agent Skill security scanner")
    parser.add_argument("--platform", choices=["codex", "claude_code", "both"], required=True)
    parser.add_argument("--root", required=True, help="Explicit scan root. HOME is never scanned by default.")
    parser.add_argument("--mode", choices=["static-only", "ai-audit-static", "dynamic"], required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--allow-dynamic-execution", action="store_true")
    parser.add_argument("--sandbox-plan-only", action="store_true")
    parser.add_argument("--safe-smoke-test", action="store_true")
    parser.add_argument("--allow-codex-exec", action="store_true")
    parser.add_argument("--safe-skill-only", action="store_true")
    parser.add_argument("--docker-smoke-plan", action="store_true")
    parser.add_argument("--docker-plan-only", action="store_true")
    parser.add_argument("--include-dynamic-evidence", action="store_true")
    parser.add_argument("--dynamic-evidence-path", default=DEFAULT_DYNAMIC_EVIDENCE_PATH)
    args = parser.parse_args()

    try:
        if args.mode == "dynamic" and not args.sandbox_plan_only and not args.safe_smoke_test and not args.docker_smoke_plan:
            deny_dynamic_execution_unless_explicit(args.mode, allow_dynamic_execution=False)
        elif args.mode != "dynamic":
            assert_static_only(args.mode)
        assert_no_token_env()
        root = _resolve_repo_path(args.root)
        assert_no_real_home(root)
        assert_no_real_codex_home(root)
        output_dir = _resolve_repo_path(args.output_dir or f"analysis_results/{args.platform}")
        output_dir.mkdir(parents=True, exist_ok=True)
        dynamic_evidence_path = (
            _resolve_repo_path(args.dynamic_evidence_path) if args.include_dynamic_evidence else None
        )

        if args.platform != "codex":
            print("Only platform=codex is implemented in this static-only CLI. Claude Code remains TODO.")
            return 1

        if args.mode == "dynamic" and args.docker_smoke_plan:
            if not args.docker_plan_only:
                print("--docker-smoke-plan requires --docker-plan-only. Refusing to build or run Docker.", file=sys.stderr)
                return 1
            paths = run_codex_docker_smoke_plan(root, output_dir)
        elif args.mode == "dynamic" and args.safe_smoke_test:
            paths = run_codex_safe_smoke_plan(
                root=root,
                output_dir=output_dir,
                allow_codex_exec=args.allow_codex_exec,
                safe_skill_only=args.safe_skill_only,
            )
        elif args.mode == "dynamic":
            paths = run_codex_sandbox_plan_only(root, output_dir)
        else:
            paths = run_codex_static(root, output_dir, dynamic_evidence_path=dynamic_evidence_path)
            if dynamic_evidence_path and not dynamic_evidence_path.exists():
                print(f"warning: dynamic evidence file does not exist: {dynamic_evidence_path}", file=sys.stderr)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("Codex static-only scan complete.")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
