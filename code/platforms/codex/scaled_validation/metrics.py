from __future__ import annotations

from typing import Any


SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "total_samples": len(results),
        "real_skill_count": 0,
        "synthetic_count": 0,
        "benign_count": 0,
        "suspicious_count": 0,
        "attack_like_count": 0,
        "blocked_count": 0,
        "manual_review_count": 0,
        "allowed_count": 0,
        "true_positive": 0,
        "true_negative": 0,
        "false_positive": 0,
        "false_negative": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "consistent_count": 0,
        "divergence_count": 0,
        "suspicious_manual_review_count": 0,
    }
    for result in results:
        family = result.get("sample_family", "real")
        severity = result.get("final_severity", "none")
        gate = result.get("gate", "allowed")
        divergence = result.get("divergence", "none")
        if result.get("sample_type") == "real":
            counts["real_skill_count"] += 1
        else:
            counts["synthetic_count"] += 1
        if family in ("benign", "suspicious", "attack_like"):
            counts[f"{family}_count"] += 1
        if gate == "blocked":
            counts["blocked_count"] += 1
        elif gate == "manual_review":
            counts["manual_review_count"] += 1
        else:
            counts["allowed_count"] += 1
        if severity in ("critical", "high", "medium", "low"):
            counts[f"{severity}_count"] += 1
        else:
            counts["consistent_count"] += 1
        if divergence != "none":
            counts["divergence_count"] += 1
        if family == "attack_like":
            if gate == "blocked" or severity in ("critical", "high"):
                counts["true_positive"] += 1
            elif gate == "allowed":
                counts["false_negative"] += 1
        elif family == "benign":
            if gate in ("allowed", "consistent") or severity == "none":
                counts["true_negative"] += 1
            if gate == "blocked" or severity in ("critical", "high"):
                counts["false_positive"] += 1
        elif family == "suspicious" and gate == "manual_review":
            counts["suspicious_manual_review_count"] += 1
    precision = _safe_div(counts["true_positive"], counts["true_positive"] + counts["false_positive"])
    recall = _safe_div(counts["true_positive"], counts["true_positive"] + counts["false_negative"])
    f1 = _safe_div(2 * precision * recall, precision + recall)
    counts.update({"precision": precision, "recall": recall, "f1": f1})
    return counts


def confusion_matrix(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "true_positive": metrics["true_positive"],
        "true_negative": metrics["true_negative"],
        "false_positive": metrics["false_positive"],
        "false_negative": metrics["false_negative"],
        "note": "Suspicious samples are tracked separately as manual review targets.",
        "suspicious_manual_review_count": metrics["suspicious_manual_review_count"],
    }


def max_severity(values: list[str]) -> str:
    normalized = [value if value in SEVERITY_ORDER else "none" for value in values]
    return max(normalized, key=lambda value: SEVERITY_ORDER[value], default="none")


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
