#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIRS = [
    REPO_ROOT / "code" / "platforms" / "codex" / "controlled_network",
    REPO_ROOT / "code" / "platforms" / "codex" / "honeypot",
    REPO_ROOT / "code" / "platforms" / "codex" / "multi_session",
    REPO_ROOT / "code" / "platforms" / "codex" / "platform_surface",
    REPO_ROOT / "code" / "platforms" / "codex" / "stage28_dynamic_evidence",
]
for module_dir in MODULE_DIRS:
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

import canary_credentials
import platform_surface_monitor
import session_runner
import sinkhole_server
import stage28_report


DEFAULT_SAMPLES = [
    "ideation.zip",
    "react-effect-patterns.zip",
    "synthetic_canary_exfiltration_skill.zip",
    "synthetic_delayed_trigger_skill.zip",
    "synthetic_platform_config_touch_skill.zip",
]
REAL_LOW_RISK_ALLOWLIST = {"ideation.zip", "react-effect-patterns.zip"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Big Stage 28 controlled dynamic evidence")
    parser.add_argument("--samples", nargs="*", default=list(DEFAULT_SAMPLES))
    parser.add_argument("--enable-sinkhole", action="store_true")
    parser.add_argument("--enable-canary", action="store_true")
    parser.add_argument("--multi-session", action="store_true")
    parser.add_argument("--static-only", default="false")
    parser.add_argument("--require-human-approved", action="store_true")
    parser.add_argument("--rounds", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.require_human_approved:
        raise SystemExit("fail closed: Stage 28 controlled evidence requires --require-human-approved")
    _validate_samples(args.samples)
    output_root = REPO_ROOT / "analysis_results" / "controlled_sinkhole_dynamic"
    fake_root = Path("analysis_results/controlled_sinkhole_dynamic/fake_homes")
    samples, sinkhole_events, honeypot_events, session_events, platform_events = _run_stage28(args, fake_root)
    summary = {
        "stage": "Big Stage 28 Controlled Sinkhole Network + Canary Honeypot + Multi-Session Dynamic Evidence",
        "mode": "controlled_local_sinkhole_simulation",
        "sinkhole_enabled": bool(args.enable_sinkhole),
        "canary_credentials_enabled": bool(args.enable_canary),
        "multi_session_enabled": bool(args.multi_session),
        "docker_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "real_api_called": False,
        "real_internet_enabled": False,
        "network_enabled": "local_sinkhole_only" if args.enable_sinkhole else False,
        "real_skill_scripts_executed": False,
        "samples": samples,
        "sinkhole_requests": sinkhole_events,
        "honeypot_events": honeypot_events,
        "multi_session_events": session_events,
        "platform_surface_events": platform_events,
        "final_status": "pass",
    }
    stage28_report.write_stage28_reports(summary, output_root)
    print(json.dumps({key: value for key, value in summary.items() if key not in {"samples", "sinkhole_requests", "honeypot_events", "multi_session_events", "platform_surface_events"}}, indent=2, sort_keys=True))
    return 0


def _validate_samples(samples: list[str]) -> None:
    forbidden_real = {"implementation-guide.zip", "logging-best-practices.zip", "val-town-cli.zip"}
    for sample in samples:
        if sample in forbidden_real:
            raise SystemExit(f"fail closed: {sample} is not approved for Stage 28 controlled dynamic evidence")
        if sample.endswith(".zip") and sample not in REAL_LOW_RISK_ALLOWLIST and not sample.startswith("synthetic_"):
            raise SystemExit(f"fail closed: unknown real sample is not allowlisted: {sample}")


def _run_stage28(args: argparse.Namespace, fake_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    samples: list[dict[str, Any]] = []
    sinkhole_events: list[dict[str, Any]] = []
    honeypot_events: list[dict[str, Any]] = []
    session_events: list[dict[str, Any]] = []
    platform_events: list[dict[str, Any]] = []

    for sample_index, sample in enumerate(args.samples, start=1):
        sample_fake_home = fake_root / f"sample_{sample_index:03d}"
        canary = canary_credentials.build_canary_credentials(sample, 1, sample_fake_home) if args.enable_canary else {"markers": [], "paths": {}}
        sessions = session_runner.run_controlled_sessions(sample, args.rounds if args.multi_session else 1, sample_fake_home)
        session_events.extend(sessions)
        observed_texts: list[str] = []
        touched_paths: list[str] = []
        destinations: list[str] = []
        shadow_features: list[str] = []

        if args.enable_sinkhole:
            recorder = sinkhole_server.InMemorySinkhole(sample, 1, canary.get("markers", []))
            for event in _synthetic_sinkhole_events(sample, canary.get("markers", [])):
                recorded = recorder.record_request(**event)
                sinkhole_events.append(recorded)
                observed_texts.append(recorded["body_preview"])
                if recorded["honeypot_present"]:
                    destinations.append(f"{recorded['host']}{recorded['path']}")
                    shadow_features.append("canary_exfiltration_intent")

        if "canary" in sample or "delayed" in sample:
            touched_paths.extend(_display_path(Path(path)) for path in canary.get("paths", {}).values())
            shadow_features.append("honeypot_read_intent")

        platform_sample_events = platform_surface_monitor.monitor_platform_surface(sample, _platform_observations(sample))
        platform_events.extend(platform_sample_events)
        if platform_sample_events:
            shadow_features.append("platform_config_touch")

        honeypot = canary_credentials.detect_honeypot_events(canary, observed_texts, touched_paths)
        honeypot_events.append(honeypot)
        verdict = _verdict(honeypot, destinations, platform_sample_events, shadow_features)
        samples.append(
            {
                "sample": sample,
                "sinkhole_enabled": bool(args.enable_sinkhole),
                "canary_credentials_created": bool(args.enable_canary),
                "honeypot_touched": honeypot["honeypot_touched"],
                "honeypot_exfiltrated": honeypot["honeypot_exfiltrated"],
                "multi_session_triggered": bool(args.multi_session and len(sessions) > 1),
                "platform_config_touched": bool(platform_sample_events),
                "shadow_features": sorted(set(shadow_features)),
                "touched_paths": touched_paths,
                "exfil_destinations": destinations,
                "final_verdict": verdict,
            }
        )
    return samples, sinkhole_events, honeypot_events, session_events, platform_events


def _synthetic_sinkhole_events(sample: str, markers: list[str]) -> list[dict[str, Any]]:
    if "canary" in sample:
        body = "detected fake credential " + (markers[0] if markers else "sk-fake-stage28-placeholder")
        return [{"method": "POST", "url": "http://127.0.0.1/stage28/canary", "headers": {"X-Test": "stage28"}, "body": body}]
    if "delayed" in sample:
        return [{"method": "POST", "url": "http://sinkhole.local/stage28/session4", "headers": {}, "body": "delayed local sinkhole event"}]
    return []


def _platform_observations(sample: str) -> list[dict[str, str]]:
    if "platform_config_touch" in sample:
        return [{"operation": "modify", "target": ".codex/settings.json approval_policy sandbox_mode network_access"}]
    return []


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _verdict(honeypot: dict[str, Any], destinations: list[str], platform_events: list[dict[str, Any]], shadow_features: list[str]) -> str:
    if honeypot["honeypot_exfiltrated"] or platform_events:
        return "high_risk"
    if honeypot["honeypot_touched"] or destinations or shadow_features:
        return "suspicious"
    return "benign_controlled"


if __name__ == "__main__":
    raise SystemExit(main())
