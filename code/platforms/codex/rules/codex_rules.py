"""Codex-specific static rules.

Rules operate on text and file paths only. They never execute sample code.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


Finding = Dict[str, Any]


RULES = [
    {
        "rule_id": "C-P1",
        "title": "SKILL.md instruction override",
        "severity": "HIGH",
        "patterns": [
            r"ignore (all )?(previous|prior|above|user|system) instructions",
            r"disregard (the )?(user|system|developer|safety)",
            r"do not (tell|mention|reveal|disclose)",
            r"never ask (for )?(permission|approval)",
        ],
        "explanation": "Skill instructions attempt to override user, system, or safety constraints.",
        "recommendation": "Remove override directives and require explicit user-visible behavior.",
    },
    {
        "rule_id": "C-P2",
        "title": "Hidden instructions",
        "severity": "HIGH",
        "patterns": [r"<!--[\s\S]*?(ignore|secret|hidden|do not mention)[\s\S]*?-->", r"[\u200b-\u200f\u202a-\u202e]"],
        "explanation": "Instructions appear hidden in markup or invisible Unicode.",
        "recommendation": "Reject concealed instructions and inspect rendered and raw Markdown.",
    },
    {
        "rule_id": "C-DESC1",
        "title": "Description abuses implicit activation",
        "severity": "MEDIUM",
        "patterns": [r"description:.*(always|whenever|for any task|all requests|every repository)", r"description:.*(automatically|silently)"],
        "explanation": "The description may coerce Codex into selecting the skill too broadly.",
        "recommendation": "Keep descriptions narrow, truthful, and task-specific.",
    },
    {
        "rule_id": "C-SC1",
        "title": "Remote execution in scripts",
        "severity": "CRITICAL",
        "patterns": [r"curl\s+.*\|\s*(sh|bash)", r"wget\s+.*\|\s*(sh|bash)", r"eval\s*\$\(", r"exec\s*\(.*https?://"],
        "explanation": "Script content includes remote fetch and execute patterns.",
        "recommendation": "Do not execute remote scripts; pin and verify local dependencies.",
    },
    {
        "rule_id": "C-E2",
        "title": "Credential or Codex state access",
        "severity": "CRITICAL",
        "patterns": [
            r"OPENAI_API_KEY",
            r"ANTHROPIC_API_KEY",
            r"GITHUB_TOKEN",
            r"CODEX_HOME",
            r"\.codex",
            r"\.ssh/(id_rsa|id_ed25519|config)",
            r"os\.environ",
        ],
        "explanation": "Code or instructions reference credentials or local Codex state.",
        "recommendation": "Do not read secrets or real user configuration from skills.",
    },
    {
        "rule_id": "C-E1",
        "title": "Data exfiltration channel",
        "severity": "HIGH",
        "patterns": [r"requests\.post", r"fetch\s*\(", r"\bcurl\b", r"\bwget\b", r"\bnc\b|\bnetcat\b", r"bash\s+-c\s+.*?/dev/tcp"],
        "explanation": "Skill content includes outbound data transfer primitives.",
        "recommendation": "Require explicit purpose, destination allowlists, and no secret-bearing payloads.",
    },
    {
        "rule_id": "C-RP1",
        "title": "Repo-scoped skill pollution",
        "severity": "MEDIUM",
        "patterns": [r"\.agents/skills"],
        "explanation": "Repository-scoped skills can silently influence Codex behavior in that repo.",
        "recommendation": "Review repo-scoped skills before enabling Codex in the workspace.",
    },
    {
        "rule_id": "C-AG1",
        "title": "Persistent AGENTS instruction pollution",
        "severity": "HIGH",
        "patterns": [r"AGENTS\.override\.md", r"AGENTS\.md", r"(always|never).*(approve|network|sandbox|permission)", r"hide.*(tool|command|output|behavior)"],
        "explanation": "Persistent project guidance may alter Codex behavior across tasks.",
        "recommendation": "Treat AGENTS guidance as untrusted and review override files carefully.",
    },
    {
        "rule_id": "C-PERM1",
        "title": "Sandbox, approval, or network escalation request",
        "severity": "HIGH",
        "patterns": [r"danger-full-access", r"--yolo", r"bypass.*(approval|sandbox)", r"enable network", r"ask-for-approval\s+never"],
        "explanation": "The skill requests weaker execution controls.",
        "recommendation": "Keep sandbox restrictive and require explicit human approval for escalation.",
    },
    {
        "rule_id": "C-MCP1",
        "title": "MCP, plugin, or external tool expansion",
        "severity": "MEDIUM",
        "patterns": [r"\bmcp\b", r"plugin", r"marketplace", r"external tool", r"server_url", r"bearer"],
        "explanation": "External tool integrations may expand the attack surface.",
        "recommendation": "Audit endpoints, credentials, and tool permissions before use.",
    },
    {
        "rule_id": "C-OAI1",
        "title": "Suspicious agents/openai.yaml configuration",
        "severity": "MEDIUM",
        "patterns": [r"agents/openai\.yaml", r"dependencies:", r"https?://", r"postinstall", r"command:"],
        "explanation": "OpenAI skill metadata references dependencies or external resources.",
        "recommendation": "Review metadata-driven resources and deny automatic execution.",
    },
]


def _finding(rule: dict, file_path: str, evidence: str) -> Finding:
    return {
        "rule_id": rule["rule_id"],
        "title": rule["title"],
        "severity": rule["severity"],
        "file": file_path,
        "evidence": evidence.strip()[:500],
        "explanation": rule["explanation"],
        "recommendation": rule["recommendation"],
    }


def scan_text(text: str, file_path: str) -> List[Finding]:
    """Scan a text blob with Codex-specific rules."""
    findings: List[Finding] = []
    for rule in RULES:
        for pattern in rule["patterns"]:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                findings.append(_finding(rule, file_path, match.group(0)))
                break
    return findings


def scan_text_for_codex_risks(text: str, file_path: str) -> List[Finding]:
    """Public wrapper for scanning arbitrary Codex-related text."""
    return scan_text(text, file_path)


def scan_script_for_codex_risks(text: str, file_path: str) -> List[Finding]:
    """Scan script text with Codex rules.

    The function only inspects text. It never imports, evaluates, or runs the
    script being scanned.
    """
    return scan_text(text, file_path)


def scan_file(path: str | Path) -> List[Finding]:
    """Scan a single file without executing it."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return []
    path_text = str(file_path)
    findings = scan_text(text, path_text)
    findings.extend(scan_text(path_text, path_text))
    return findings


def scan_paths(paths: Iterable[str | Path]) -> List[Finding]:
    """Scan multiple paths and return JSON-compatible findings."""
    results: List[Finding] = []
    for path in paths:
        file_path = Path(path)
        if file_path.is_file():
            results.extend(scan_file(file_path))
    return results


def scan_codex_skill(skill_record_or_path: Any) -> List[Finding]:
    """Scan a SkillRecord-like object, dict, or path for Codex risks."""
    paths: List[str | Path] = []

    if isinstance(skill_record_or_path, (str, Path)):
        root = Path(skill_record_or_path)
        if root.is_file():
            paths.append(root)
        elif root.is_dir():
            for candidate in [
                root / "SKILL.md",
                root / "AGENTS.md",
                root / "AGENTS.override.md",
                root / "agents" / "openai.yaml",
            ]:
                if candidate.exists():
                    paths.append(candidate)
            for subdir in ("scripts", "references", "assets"):
                paths.extend(path for path in (root / subdir).rglob("*") if path.is_file()) if (root / subdir).exists() else None
        return scan_paths(paths)

    if hasattr(skill_record_or_path, "to_dict"):
        data = skill_record_or_path.to_dict()
    elif isinstance(skill_record_or_path, dict):
        data = skill_record_or_path
    else:
        return []

    for key in ("skill_md_path", "agents_md_path", "openai_yaml_path"):
        if data.get(key):
            paths.append(data[key])
    for key in ("scripts_paths", "references_paths", "assets_paths"):
        paths.extend(data.get(key) or [])

    return scan_paths(paths)


def classify_findings(findings: List[Finding]) -> Dict[str, Any]:
    """Classify Codex static findings into a compact risk summary."""
    if not findings:
        return {"classification": "safe", "severity": "LOW", "confidence": 0.0}

    rule_ids = {finding.get("rule_id", "") for finding in findings}
    severity_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    highest = max((finding.get("severity", "LOW") for finding in findings), key=lambda value: severity_rank.get(value, 0))

    classification = "suspicious"
    confidence = 0.55

    if {"C-E2", "C-E1"}.issubset(rule_ids):
        highest = "CRITICAL"
        classification = "malicious"
        confidence = 0.9
    elif "C-SC1" in rule_ids:
        classification = "malicious"
        confidence = 0.85
    elif "C-P1" in rule_ids or "C-AG1" in rule_ids or "C-PERM1" in rule_ids:
        if severity_rank.get(highest, 0) < severity_rank["HIGH"]:
            highest = "HIGH"
        classification = "malicious"
        confidence = 0.8
    elif highest == "CRITICAL":
        classification = "malicious"
        confidence = 0.8
    elif highest == "HIGH":
        classification = "suspicious"
        confidence = 0.7
    elif highest == "MEDIUM":
        classification = "suspicious"
        confidence = 0.6

    return {"classification": classification, "severity": highest, "confidence": confidence}
