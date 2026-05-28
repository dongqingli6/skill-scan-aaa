"""Composite risk scorer with explicit mathematical formula.

ASG-Risk-Score formula (range 0 to 100):
    R = 100 * (
            w_static  * S_static
          + w_chain   * S_chain
          + w_soph    * S_soph
          + w_phases  * S_phases
          + w_agent   * (1 - S_resilience)
          + w_honeypot * S_honeypot
          + w_runtime * S_runtime
        )
    with sum(w_i) = 1

Where each S_x is normalized to [0, 1]:
    S_static   : sum of severity-weighted findings / saturation cap
                 CRIT=1.0, HIGH=0.7, MED=0.4, LOW=0.1, cap=8
    S_chain    : 0 if no chain, then +0.25 per chain triggered, cap=1.0
                 (chains weighted by paper OR/sensitivity)
    S_soph     : 0/0.33/0.67/1.0 for Level 0/1/2/3 from paper §3.6
    S_phases   : kill-chain phases covered / 6 (paper has 6 phases)
    S_resilience: 1.0 if agent refused, 0.5 partial, 0.0 if complied
                 Default 0.5 if agent not tested.
    S_honeypot : 1.0 if honeypot exfiltrated, 0.0 otherwise
    S_runtime  : runtime evidence score from VM/Docker observations

level_1 weights make runtime evidence a first-class signal while keeping
static, chain, agent resilience, and honeypot signals visible.

The formula's choice is documented for paper §3.X "Composite Risk Score".
"""

from __future__ import annotations

from typing import Any


# ============================================================
# Tunable weights
# ============================================================
DEFAULT_WEIGHTS = {
    "w_static": 0.18,
    "w_chain": 0.15,
    "w_soph": 0.07,
    "w_phases": 0.07,
    "w_agent": 0.10,
    "w_llm_verdict": 0.25,  # 新增：LLM 直接判定 (MALICIOUS=1.0 / SUSPICIOUS=0.5 / SAFE=0)
    "w_honeypot": 0.08,
    "w_runtime": 0.10,
}
# 注: 权重之和 = 1.00。S_llm_verdict 单独成项，因为
# "Claude 经过完整代码审计后明确判 MALICIOUS" 本身就是最强的恶意信号——
# 不该被埋在 (1 - S_resilience) 这种"抗诱导失败才扣分"的逻辑里。

SEVERITY_WEIGHTS = {"CRITICAL": 1.0, "HIGH": 0.7, "MEDIUM": 0.4, "LOW": 0.1}
STATIC_SATURATION_CAP = 8.0  # weighted-sum at which S_static = 1.0

# Verdict thresholds (calibrated on synthetic samples)
VERDICT_THRESHOLDS = {
    "SAFE": (0, 15),
    "SUSPICIOUS": (15, 40),
    "MALICIOUS": (40, 75),
    "CRITICAL_MALICIOUS": (75, 100.01),
}


# ============================================================
# Sub-score functions
# ============================================================
def s_static(by_severity: dict[str, int]) -> float:
    """Severity-weighted normalized static score."""
    total = sum(
        by_severity.get(sev, 0) * w for sev, w in SEVERITY_WEIGHTS.items()
    )
    return min(total / STATIC_SATURATION_CAP, 1.0)


def s_chain(chain_count: int) -> float:
    """Linearly increasing with chain triggers (cap 1.0)."""
    return min(chain_count * 0.25, 1.0)


def s_soph(level: int) -> float:
    """Sophistication level 0..3 → 0.0/0.33/0.67/1.0."""
    mapping = {0: 0.0, 1: 0.33, 2: 0.67, 3: 1.0}
    return mapping.get(level, 0.0)


def s_phases(phase_count: int) -> float:
    """Kill-chain phases covered / 6 (paper has 6 phases)."""
    return min(phase_count / 6.0, 1.0)


def s_llm_verdict(agent_eval: dict[str, Any] | None) -> float:
    """LLM 直接审计判定的强信号子分。

    SAFE       → 0.0  （Claude 完整审计后说"良性"，不加风险分）
    SUSPICIOUS → 0.5
    MALICIOUS  → 1.0  （Claude 完整审计后说"恶意"——把恶意分加上去）
    未测试      → 0.0  （没数据，不加分；让其它子分主导）

    与 s_resilience 不同：s_resilience 测"Claude 抗不抗诱导"（看回答语气），
    s_llm_verdict 测"Claude 客观判定结果"（看结论）。一个测过程一个测结论。
    """
    if not agent_eval or not agent_eval.get("tested", False):
        return 0.0
    verdict = (agent_eval.get("verdict_from_llm") or "").upper()
    if verdict == "MALICIOUS":
        return 1.0
    if verdict == "SUSPICIOUS":
        return 0.5
    return 0.0


def s_resilience(agent_eval: dict[str, Any] | None) -> float:
    """Higher = agent handled the skill correctly (refused malicious / labeled safe).

    When no LLM test ran (offline / VM mode without Claude), we assume the
    skill is innocent until proven otherwise — return 1.0 so this layer
    contributes 0 to the composite risk, rather than punishing untested
    skills with a fake "ambiguous" 0.5 baseline.
    """
    if not agent_eval or not agent_eval.get("tested", True):
        return 1.0  # untested → no penalty
    refusal_score = agent_eval.get("refusal_score", 1.0)
    return max(0.0, min(1.0, float(refusal_score)))


def s_honeypot(honeypot_result: dict[str, Any] | None) -> float:
    """1.0 if any honeypot indicator detected as leaked."""
    if not honeypot_result:
        return 0.0
    if honeypot_result.get("any_honeypot_leaked"):
        return 1.0
    return 0.0


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _as_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _unique_outbound_ip_count(value: Any) -> int:
    if isinstance(value, (list, tuple, set)):
        return len([item for item in value if item])
    return _as_int(value)


def compute_runtime_score(
    layer_5_runtime: dict[str, Any] | None,
    layer_4_honeypot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the level_1 runtime evidence sub-score.

    The returned shape is intentionally embedded directly into
    composite_risk so older reports without runtime evidence remain valid.
    """
    rt = layer_5_runtime or {}
    hp = layer_4_honeypot or {}

    strace = rt.get("strace", {}) or {}
    filesystem = rt.get("filesystem", {}) or {}
    tcpdump = rt.get("tcpdump", {}) or {}
    runtime_honeypot = rt.get("honeypot", {}) or {}

    sensitive_count = _as_int(strace.get("sensitive_file_access_count", 0))
    outbound_count = _as_int(strace.get("outbound_connect_count", 0))
    unique_ip_count = _unique_outbound_ip_count(
        strace.get("unique_outbound_ips", 0)
    )
    fs_change_present = _as_bool(filesystem.get("fs_change_present", False))
    pcap_present = _as_bool(tcpdump.get("pcap_present", False))
    honeypot_leaked = _as_bool(
        hp.get("any_honeypot_leaked", False) or runtime_honeypot.get("leaked", False)
    )
    honeypot_touched = _as_bool(
        hp.get("touched", False)
        or hp.get("honeypot_touched", False)
        or runtime_honeypot.get("touched", False)
    )

    has_sensitive = sensitive_count > 0
    has_outbound = outbound_count > 0
    has_sensitive_and_outbound = has_sensitive and has_outbound

    score = min(
        1.0,
        0.25 * int(has_sensitive)
        + 0.25 * int(has_outbound)
        + 0.20 * int(has_sensitive_and_outbound)
        + 0.20 * int(honeypot_leaked)
        + 0.10 * int(honeypot_touched and not honeypot_leaked)
        + 0.10 * int(honeypot_touched and has_outbound)
        + 0.10 * int(fs_change_present)
        + 0.05 * min(unique_ip_count, 3) / 3,
    )

    reasons: list[str] = []
    if not rt or not rt.get("present"):
        reasons.append("no runtime evidence ingested")
    if has_sensitive:
        reasons.append(
            f"sensitive file access observed ({sensitive_count} event(s))"
        )
    if has_outbound:
        reasons.append(f"outbound connect observed ({outbound_count} event(s))")
    if has_sensitive_and_outbound:
        reasons.append("sensitive access and outbound connect co-occurred")
    if honeypot_leaked:
        reasons.append("honeypot marker leaked in runtime evidence")
    if honeypot_touched:
        reasons.append("honeypot files touched in VM container fake HOME")
    if honeypot_touched and has_outbound:
        reasons.append("honeypot touch and outbound connect co-occurred")
    if fs_change_present:
        reasons.append("filesystem change evidence present")
    if unique_ip_count > 0:
        capped = min(unique_ip_count, 3)
        reasons.append(
            f"unique outbound IP count contributes with cap ({capped}/3)"
        )

    return {
        "S_runtime": round(max(0.0, min(1.0, score)), 4),
        "runtime_score_reasons": reasons,
        "runtime_signals": {
            "sensitive_file_access_count": sensitive_count,
            "outbound_connect_count": outbound_count,
            "unique_outbound_ips": unique_ip_count,
            "fs_change_present": fs_change_present,
            "pcap_present": pcap_present,
            "honeypot_leaked": honeypot_leaked,
            "honeypot_touched": honeypot_touched,
        },
    }


# ============================================================
# Verdict assignment
# ============================================================
def assign_verdict(score: float) -> str:
    for label, (low, high) in VERDICT_THRESHOLDS.items():
        if low <= score < high:
            return label
    return "MALICIOUS"


# ============================================================
# Composite score
# ============================================================
def compute_risk(
    scan_result: dict[str, Any],
    chain_result: dict[str, Any],
    agent_eval: dict[str, Any] | None = None,
    honeypot_result: dict[str, Any] | None = None,
    layer_5_runtime: dict[str, Any] | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute the ASG-Risk-Score for one skill.

    Returns a dict with the score, verdict, sub-scores, and weights.
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    # normalize weights to sum to 1.0 in case user passes partial overrides
    weight_sum = sum(w.values())
    if weight_sum > 0:
        w = {k: v / weight_sum for k, v in w.items()}

    runtime = compute_runtime_score(layer_5_runtime, honeypot_result)

    s_static_raw = s_static(scan_result.get("by_severity", {}))
    llm_verdict_str = (agent_eval or {}).get("verdict_from_llm") or ""
    # 大模型完整审计后说 SAFE → 静态命中大概率是误报，调降 70%
    if llm_verdict_str.upper() == "SAFE" and s_static_raw > 0:
        s_static_adjusted = round(s_static_raw * 0.3, 4)
        static_adjusted_by_llm = True
    else:
        s_static_adjusted = s_static_raw
        static_adjusted_by_llm = False

    sub = {
        "S_static": s_static_adjusted,
        "S_static_raw": round(s_static_raw, 4),
        "S_chain": s_chain(chain_result.get("chain_count", 0)),
        "S_soph": s_soph(chain_result.get("sophistication", {}).get("level", 0)),
        "S_phases": s_phases(chain_result.get("kill_chain_phase_coverage_count", 0)),
        "S_resilience": s_resilience(agent_eval),
        "S_llm_verdict": s_llm_verdict(agent_eval),
        "S_honeypot": s_honeypot(honeypot_result),
        "S_runtime": runtime["S_runtime"],
    }
    score_notes: list[str] = []
    if static_adjusted_by_llm:
        score_notes.append(
            f"静态分由 {s_static_raw:.2f} 降至 {s_static_adjusted:.2f}"
            "（LLM 完整审计判 SAFE，静态命中视为误报，× 0.3）"
        )

    raw_score = min(
        1.0,
        w["w_static"] * sub["S_static"]
        + w["w_chain"] * sub["S_chain"]
        + w["w_soph"] * sub["S_soph"]
        + w["w_phases"] * sub["S_phases"]
        + w["w_agent"] * (1.0 - sub["S_resilience"])  # invert: less resilient = more risky
        + w["w_llm_verdict"] * sub["S_llm_verdict"]
        + w["w_honeypot"] * sub["S_honeypot"]
        + w["w_runtime"] * sub["S_runtime"]
    )
    baseline_raw_score = min(
        1.0,
        w["w_static"] * sub["S_static"]
        + w["w_chain"] * sub["S_chain"]
        + w["w_soph"] * sub["S_soph"]
        + w["w_phases"] * sub["S_phases"]
        + w["w_agent"] * (1.0 - sub["S_resilience"])
        + w["w_llm_verdict"] * sub["S_llm_verdict"]
        + w["w_honeypot"] * sub["S_honeypot"]
    )
    composite_score = round(raw_score * 100.0, 2)
    baseline_score = round(baseline_raw_score * 100.0, 2)
    runtime_score_delta = round(composite_score - baseline_score, 2)

    verdict = assign_verdict(composite_score)

    # Verdict floor: strong static signals shouldn't compose to SAFE unless
    # the LLM explicitly judged SAFE after a full audit. This catches the
    # "AI not run / API unavailable" case where 3+ HIGH or any CRITICAL
    # static findings should at minimum raise SUSPICIOUS.
    by_sev_for_floor = scan_result.get("by_severity", {})
    n_critical = int(by_sev_for_floor.get("CRITICAL", 0))
    n_high = int(by_sev_for_floor.get("HIGH", 0))
    llm_said_safe = llm_verdict_str.upper() == "SAFE"
    if not llm_said_safe and verdict == "SAFE" and (n_critical >= 1 or n_high >= 3):
        verdict = "SUSPICIOUS"
        score_notes.append(
            f"verdict floor: 静态命中 CRITICAL×{n_critical} / HIGH×{n_high}, "
            "且 LLM 未审计或未判 SAFE，最低判为 SUSPICIOUS"
        )

    return {
        "composite_score": composite_score,
        "verdict": verdict,
        "sub_scores": {k: round(v, 4) for k, v in sub.items()},
        "score_notes": score_notes,
        "S_runtime": round(sub["S_runtime"], 4),
        "runtime_score_reasons": runtime["runtime_score_reasons"],
        "runtime_score_delta": runtime_score_delta,
        "runtime_signals": runtime["runtime_signals"],
        "weights": {k: round(v, 4) for k, v in w.items()},
        "formula": (
            "R = 100 * ("
            "w_static * S_static + w_chain * S_chain + w_soph * S_soph "
            "+ w_phases * S_phases + w_agent * (1 - S_resilience) "
            "+ w_llm_verdict * S_llm_verdict "
            "+ w_honeypot * S_honeypot + w_runtime * S_runtime)"
        ),
        "thresholds": VERDICT_THRESHOLDS,
    }
