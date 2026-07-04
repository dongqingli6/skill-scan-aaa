"""不重跑 Docker — 重 mine 静态 IOC（用新白名单）+ 重 judge。"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from malskillbench_runner import layer2_judge_with_extras, DATASET_ROOT
from asg import static_ioc_miner, canary_honeypot

WORK = REPO / "analysis_results" / "malskillbench"


def rejudge(name, r):
    # 重新 mine 静态 IOC（用新白名单）
    cat = r["category"]
    skill_path = DATASET_ROOT / cat / name
    if not skill_path.exists():
        # try alt path
        for p in DATASET_ROOT.rglob("SKILL.md"):
            if p.parent.name == name:
                skill_path = p.parent; break
    static_iocs = static_ioc_miner.mine_static_iocs(skill_path) if skill_path.exists() \
                  else r.get("static_iocs", {})
    static_summary = static_ioc_miner.format_for_layer2(static_iocs)
    leak_summary = canary_honeypot.format_leak_evidence(r.get("canary_leak_scan", {}))
    judge = layer2_judge_with_extras(
        r.get("skill_desc", ""), r.get("trigger_prompt", ""),
        r.get("iocs_observed", {}),
        r.get("agent_output_head", ""),
        static_summary=static_summary, leak_summary=leak_summary,
        leak_scan=r.get("canary_leak_scan", {}),
        static_risk_score=static_iocs.get("risk_score", 0),
    )
    return name, judge, static_iocs


def main():
    src = WORK / "malskillbench_results.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    print("=" * 70)
    print("MalSkillBench 重 judge v3（白名单 + 关系判定）")
    print("=" * 70)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(rejudge, n, r): n for n, r in data.items()}
        for f in as_completed(futs):
            n, judge, static_iocs = f.result()
            data[n]["judge"] = judge
            data[n]["static_iocs"] = static_iocs
            gt = data[n]["ground_truth"]["vector"]
            v = judge.get("verdict")
            if gt == "BENIGN":
                ok = "✓" if v == "SAFE" else "✗"
            else:
                ok = "✓" if v in ("MALICIOUS", "SUSPICIOUS") else "✗"
            risk = static_iocs.get("risk_score", 0)
            n_shell = static_iocs.get("summary", {}).get("n_shell_commands", 0)
            n_benign = static_iocs.get("summary", {}).get("n_benign_cli_uses", 0)
            print(f"  {ok} [{gt:6s}] {n[:38]:38s} v={v:11s} 静态={risk} shell={n_shell}(白名单跳过{n_benign})")

    src.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    n_total = len(data)
    n_correct = sum(
        1 for r in data.values()
        if (r["ground_truth"]["vector"] == "BENIGN" and r["judge"].get("verdict") == "SAFE")
        or (r["ground_truth"]["vector"] != "BENIGN" and r["judge"].get("verdict") in ("MALICIOUS", "SUSPICIOUS"))
    )
    print(f"\n准确率: {n_correct}/{n_total} = {n_correct/max(1,n_total)*100:.0f}%")


if __name__ == "__main__":
    main()
