"""强制跑 3 个含恶意 .py 的样本走 OpenCode + DS Docker，
打出真 strace IOC 证据（外联 IP、敏感读、agent 报告）。
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from malskillbench_runner import DATASET_ROOT
from unified_runner import stage2b_opencode_ds
from inject_stage2b_runtime import inject as inject_s2b

SAMPLES = [
    ("Branch Orchestration__CI_B6", "反向 Shell (B6) — 应连 81.46.246.181:4444"),
    ("3d-games__CI_B2", "凭据窃取 (B2) — 应读 .ssh/id_rsa"),
    ("Cloud Penetration Testing__CI_B8", "权限提升 (B8) — 应跑 setuid/sudo"),
]


def stage_to_adhoc(name: str) -> str:
    src = DATASET_ROOT / "malware" / name
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", name)[:60]
    dst = DATASET_ROOT / "adhoc" / safe
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    return safe


def one(name, label):
    print(f"\n{'='*70}")
    print(f"=== {name} ===")
    print(f"=== {label} ===")
    print(f"{'='*70}")
    safe = stage_to_adhoc(name)
    t0 = time.time()
    r = stage2b_opencode_ds(safe)
    dur = time.time() - t0
    print(f"\n[OpenCode + DS Docker 真跑了 {dur:.0f}s]")
    print(f"[容器内执行: {r.get('exec_dur_s',0)}s]")
    print(f"\nverdict: {r.get('verdict')} conf={r.get('confidence',0):.2f}")
    print(f"reason: {r.get('reason','')[:200]}")
    print()
    iocs = r.get("iocs_observed", {}) or {}
    print(f"=== 容器内真 IOC ===")
    print(f"  外联 IP 数: {iocs.get('real_outbound_count', 0)}")
    print(f"  外联 IPs: {iocs.get('real_outbound_ips', [])[:5]}")
    print(f"  真敏感读: {iocs.get('sensitive_reads_count', 0)} 条")
    print(f"  敏感路径: {iocs.get('sensitive_file_reads', [])[:5]}")
    print(f"  良性初始化已过滤: {iocs.get('benign_init_reads_filtered', [])[:3]}")
    print()
    canary = r.get("canary_leak_scan", {}) or {}
    if canary.get("any_leaked"):
        print(f"=== ⚠ canary 蜜罐铁证 ===")
        print(f"  泄露 token: {canary.get('leaked_token_kinds', [])}")
        print(f"  泄露通道: {canary.get('leak_channels', [])}")
    print()
    agent = r.get("agent_output_head", "")
    if agent:
        print(f"=== Agent 真输出（前 600 字）===")
        print(agent[:600])
    print()
    # 注入到 asg_report
    # 先把 unified_scans/result.json 写出来
    ufile = REPO / "analysis_results" / "unified_scans" / safe / "result.json"
    ufile.parent.mkdir(parents=True, exist_ok=True)
    # 加载或新建
    if ufile.exists():
        ur = json.load(open(ufile, encoding="utf-8"))
        ur.setdefault("stages", {})["stage2b_opencode_ds"] = r
    else:
        ur = {"stages": {"stage2b_opencode_ds": r}, "skill_name": safe}
    ufile.write_text(json.dumps(ur, indent=2, ensure_ascii=False), encoding="utf-8")
    # 先跑 asg_cli scan 生成 asg_report.json，再注入 Stage 2B
    import subprocess, os
    env = {**os.environ}
    cfg = REPO / "asg" / "vm_config.json"
    if cfg.exists():
        try:
            c = json.loads(cfg.read_text(encoding="utf-8"))
            k = c.get("remote_anthropic_api_key", "")
            if k and "REPLACE" not in k:
                env["ANTHROPIC_API_KEY"] = k
                b = c.get("remote_anthropic_base_url")
                if b: env["ANTHROPIC_BASE_URL"] = b
        except json.JSONDecodeError:
            pass
    skill_path = DATASET_ROOT / "adhoc" / safe
    if not (REPO / "analysis_results" / "asg" / safe / "asg_report.json").exists():
        subprocess.run([sys.executable, "-m", "asg.asg_cli", "scan", str(skill_path),
                        "--enable-honeypot", "--enable-ssd"],
                       cwd=str(REPO), capture_output=True, text=True, timeout=180, env=env)
    inject_s2b(safe)
    print(f"→ /report/{safe} 可看完整证据")
    return safe, r


def main():
    print(f"挑 3 个含恶意 .py 的样本强制跑 OpenCode + DS Docker")
    for name, label in SAMPLES:
        print(f"  · {name} — {label}")
    print()
    t0 = time.time()
    results = []
    # 串行跑，确保不抢 VM
    for name, label in SAMPLES:
        safe, r = one(name, label)
        results.append((safe, r))
    dur = time.time() - t0
    print()
    print("=" * 70)
    print(f"全部跑完 {dur:.0f}s")
    print()
    print("=== 汇总（用于报告）===")
    for safe, r in results:
        iocs = r.get("iocs_observed", {}) or {}
        print(f"  · {safe}: verdict={r.get('verdict')} 外联={iocs.get('real_outbound_count',0)} 敏感读={iocs.get('sensitive_reads_count',0)}")
    out = REPO / "analysis_results" / "force_stage2b_3" / "results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {safe: r for safe, r in results}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
