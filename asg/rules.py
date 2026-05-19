"""ASG static detection rules.

Implements paper [arXiv:2602.06547v2] Table 3 / Table 9 14-pattern taxonomy,
plus 3 paper-supplementary extensions (P5, P6, P7) based on observed
attack categories in [6] GTG-1002 and [8] Cato CTRL incident reports.

Each rule maps to:
  - id: paper pattern id (E1..E4, P1..P7, PE1..PE3, SC1..SC3)
  - kill_chain_phase: one of recon/cred_access/execution/evasion/exfil/impact
  - severity: CRITICAL / HIGH / MEDIUM / LOW (paper Appendix H)
  - patterns: list of regex patterns (case-insensitive)
  - description: human-readable explanation
  - paper_table: reference (table_3, table_9, extension)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    rule_id: str
    severity: str
    kill_chain_phase: str
    file: str
    line: int
    pattern: str
    matched_text: str
    description: str
    confidence: float


@dataclass
class Rule:
    rule_id: str
    name: str
    kill_chain_phase: str
    severity: str
    patterns: list[str]
    description: str
    paper_reference: str = "table_3"
    confidence: float = 0.85


# ============================================================
# Paper Table 3 / Table 9: original 14 patterns
# ============================================================
PAPER_RULES: list[Rule] = [
    # Reconnaissance phase
    Rule(
        rule_id="E3",
        name="File System Enumeration",
        kill_chain_phase="recon",
        severity="MEDIUM",
        patterns=[
            r"glob.*\.(ssh|aws|gnupg)",
            r"id_rsa",
            r"\.pem(?:\s|$|[\"'])",
            r"os\.listdir.*\.(ssh|aws)",
            r"ls\s+[~/].*\.(ssh|aws)",
        ],
        description="Scanning for SSH keys, AWS credentials, or other auth files.",
    ),
    Rule(
        rule_id="E4",
        name="Network Reconnaissance",
        kill_chain_phase="recon",
        severity="MEDIUM",
        patterns=[
            r"socket\.(?:connect|gethostbyname|socket)",
            r"socket\.AF_INET",
            r"\.connect\s*\(\s*\(",  # any obj.connect((host, port)) pattern
            r"nmap",
            r"netstat",
            r"port[\s_-]?scan",
        ],
        description="Network socket usage or port scanning.",
    ),
    # Credential Access phase
    Rule(
        rule_id="E2",
        name="Credential Harvesting",
        kill_chain_phase="cred_access",
        severity="CRITICAL",
        patterns=[
            r"os\.(?:environ|getenv).*(?:key|secret|token|password|api)",
            r"\$\{?(?:ANTHROPIC|OPENAI|GITHUB|AWS)_(?:API_)?(?:KEY|TOKEN|SECRET)",
            r"process\.env\.[A-Z_]+(?:KEY|TOKEN|SECRET)",
            r"capture\s+(?:the\s+)?value[s]?\s+of",
        ],
        description="Collecting API keys, tokens, or passwords from environment.",
    ),
    Rule(
        rule_id="PE3",
        name="Credential File Access",
        kill_chain_phase="cred_access",
        severity="CRITICAL",
        patterns=[
            r"open\s*\(\s*[\"'][^\"']*\.(?:ssh|aws)/(?:id_rsa|credentials)",
            r"open\s*\(\s*[\"'][^\"']*\.env[\"']",
            r"~/\.(?:ssh|aws|kube|netrc|gnupg)",
            r"/etc/(?:shadow|passwd)",
        ],
        description="Reading auth tokens or password stores from filesystem.",
    ),
    # Execution phase
    Rule(
        rule_id="SC1",
        name="Command Injection",
        kill_chain_phase="execution",
        severity="HIGH",
        patterns=[
            r"subprocess\.(?:run|call|Popen).*shell\s*=\s*True",
            r"subprocess\.(?:run|call|Popen)\s*\(\s*\[\s*[\"']/?bin/(?:sh|bash|zsh)",
            r"os\.system\s*\(",
            r"eval\s*\(\s*(?:input|request|user|sys\.argv)",
            r"exec\s*\(\s*(?:input|request|user|open)",
            # Reverse-shell signatures (paper Fig. 1 pattern)
            r"/bin/sh.*-i",
            r"bash\s+-i\s+>",
            r"os\.dup2\s*\(.*fileno",
            r"nc\s+-e",
        ],
        description="Arbitrary system command execution or reverse-shell pattern.",
    ),
    Rule(
        rule_id="SC2",
        name="Remote Script Execution",
        kill_chain_phase="execution",
        severity="CRITICAL",
        patterns=[
            r"curl[^|]+\|\s*(?:bash|sh|zsh)",
            r"wget[^|]+\|\s*(?:bash|sh|zsh)",
            r"exec\s*\(\s*[\"']?http",
            r"requests\.get\(.*\)\.text.*exec",
        ],
        description="Downloading and running external code (curl | bash pattern).",
    ),
    # Defense Evasion phase
    Rule(
        rule_id="SC3",
        name="Obfuscated Code",
        kill_chain_phase="evasion",
        severity="CRITICAL",
        patterns=[
            r"base64\.b64decode.*exec",
            r"exec\s*\(\s*base64",
            r"eval\s*\(.*b64decode",
            r"marshal\.loads.*exec",
            r"pickle\.loads.*exec",
        ],
        description="Base64/hex/marshal obfuscated code execution.",
    ),
    Rule(
        rule_id="P2",
        name="Hidden Instructions",
        kill_chain_phase="evasion",
        severity="HIGH",
        patterns=[
            r"<!--[^-]*\b(?:must|always|never|do\s+not|critical)\b",
            r"\[//\]:\s*#",
            # invisible Unicode zero-width characters
            r"[​‌‍⁠﻿]",
        ],
        description="Directives hidden in HTML comments or invisible Unicode.",
    ),
    # Exfiltration phase
    Rule(
        rule_id="E1",
        name="External Data Transmission",
        kill_chain_phase="exfil",
        severity="HIGH",
        patterns=[
            r"requests\.(?:post|put|get).*http[s]?://(?!localhost)",
            r"urllib\.request.*http",
            r"axios\.(?:post|put|get).*http",
            r"fetch\s*\(\s*[\"']http",
            r"curl\s+-X?\s*(?:POST|PUT)",
            # Known attacker / exfil sinkholes used in paper case studies
            r"\battacker\.example\b",
            r"\battacker\.com\b",
            r"\bexfil[\w-]*\.example\b",
            r"\bc2[\w-]*\.example\b",
            r"webhook\.site",
            r"pastebin\.com",
            r"\.onion\b",
        ],
        description="Data transmission to external (typically attacker-controlled) endpoints.",
    ),
    Rule(
        rule_id="P3",
        name="Data Exfil via Code Exec",
        kill_chain_phase="exfil",
        severity="HIGH",
        patterns=[
            r"exec.*requests\.(?:post|put)",
            r"eval.*urllib",
            r"subprocess.*curl.*-d",
        ],
        description="Data exfiltration via dynamically-executed code paths.",
    ),
    # Impact phase
    Rule(
        rule_id="P1",
        name="Instruction Override",
        kill_chain_phase="impact",
        severity="HIGH",
        patterns=[
            r"(?i)ignore\s+(?:previous|above|prior|all)\s+(?:instruction|message|prompt|rule)",
            r"(?i)disregard\s+(?:previous|above|prior|all|safety|user)",
            r"(?i)override\s+(?:any|all|user|system|conflicting|prior)",
            r"(?i)supersede\s+(?:any|all|user|system)",
            r"(?i)non[\s-]?negotiable",
            r"(?i)unbypassable",
            r"(?i)cannot\s+be\s+overridden",
            r"(?i)these\s+instructions\s+are\s+(?:critical|mandatory)",
            r"(?i)must\s+be\s+followed\s+(?:in\s+all\s+cases|regardless)",
        ],
        description="Skill instructs the agent to override user/system constraints.",
    ),
    Rule(
        rule_id="P4",
        name="Behavior Manipulation",
        kill_chain_phase="impact",
        severity="MEDIUM",
        patterns=[
            r"(?i)(?:do\s+not|don't|never)\s+(?:ask|consult|prompt|query)\s+(?:the\s+)?user",
            r"(?i)(?:do\s+not|don't|never)\s+(?:mention|tell|inform|alert|notify|disclose)",
            r"(?i)silently\s+(?:add|include|inject|append|execute|run|copy)",
            r"(?i)without\s+(?:asking|notifying|informing|user[\s-]?consent)",
            r"(?i)deny\s+that\s+you",
            r"(?i)mandatory\s+(?:activation|protocol|step|behavior|bcc|action)",
            r"(?i)always\s+add\s+.*\s+(?:to\s+the\s+)?(?:bcc|cc|recipient|email)",
            r"(?i)ban\s+(?:the\s+)?askuserquestion",
            r"(?i)do\s+not\s+use\s+(?:the\s+)?askuserquestion",
        ],
        description="Coercive language steering the agent toward unsafe actions.",
    ),
    Rule(
        rule_id="PE1",
        name="Excessive Permissions",
        kill_chain_phase="impact",
        severity="LOW",
        patterns=[
            r"--dangerously-skip-permissions",
            r"--yolo",
            r"danger-full-access",
        ],
        description="Skill requests scope beyond stated functionality.",
    ),
    Rule(
        rule_id="PE2",
        name="Privilege Escalation",
        kill_chain_phase="impact",
        severity="MEDIUM",
        patterns=[
            r"sudo\s+",
            r"chmod\s+[0-7]*[67][0-7]*",
            r"chown\s+",
            r"setuid",
        ],
        description="Elevating access without justification.",
    ),
]


# ============================================================
# ASG paper-supplementary extensions (P5, P6, P7)
# ============================================================
EXTENSION_RULES: list[Rule] = [
    Rule(
        rule_id="P5",
        name="Authority Impersonation",
        kill_chain_phase="impact",
        severity="HIGH",
        patterns=[
            r"(?i)system\s+administrator\s+(?:requires|requests|asks|says)",
            r"(?i)this\s+is\s+a\s+test\s+by\s+(?:claude|anthropic|openai|admin)",
            r"(?i)verified\s+by\s+(?:safety|security|trust)\s+team",
            r"(?i)approved\s+by\s+(?:anthropic|openai|google)",
            r"(?i)as\s+(?:your|the)\s+(?:developer|maintainer|owner)",
            r"(?i)official\s+(?:internal|safety)\s+(?:guideline|policy)",
        ],
        description="Skill claims false authority to manipulate agent.",
        paper_reference="extension",
        confidence=0.80,
    ),
    Rule(
        rule_id="P6",
        name="Persistence Implantation",
        kill_chain_phase="impact",
        severity="CRITICAL",
        patterns=[
            r"(?i)(?:add|append|write)\s+(?:to|into)\s+~?[/\\]?\.bashrc",
            r"(?i)(?:add|append|write)\s+(?:to|into)\s+~?[/\\]?\.zshrc",
            r"(?i)(?:add|append|write)\s+(?:to|into)\s+~?[/\\]?\.profile",
            r"crontab\s+-e",
            r"systemd.*service",
            r"reg\s+add\s+.*\\Run",
            r"(?i)set\s+startup\s+(?:item|task)",
            r"(?i)launchd",
            r"(?i)autostart",
        ],
        description="Skill instructs persistent modification to system startup.",
        paper_reference="extension",
        confidence=0.85,
    ),
    Rule(
        rule_id="P7",
        name="Cross-tool Coercion",
        kill_chain_phase="impact",
        severity="HIGH",
        patterns=[
            r"(?i)use\s+(?:another|different|the)\s+skill",
            r"(?i)first\s+install\s+",
            r"(?i)before\s+responding[,]?\s+(?:read|run|execute)",
            r"(?i)chain\s+with\s+(?:skill|tool)",
            r"(?i)invoke\s+(?:the\s+)?backup\s+script",
            r"(?i)automatically\s+activate\s+for\s+every",
        ],
        description="Skill instructs the agent to invoke or install other skills/tools.",
        paper_reference="extension",
        confidence=0.75,
    ),
]


ALL_RULES: list[Rule] = PAPER_RULES + EXTENSION_RULES


# ============================================================
# Severity weights for risk scoring (paper Appendix H)
# ============================================================
SEVERITY_WEIGHTS = {
    "CRITICAL": 1.0,
    "HIGH": 0.7,
    "MEDIUM": 0.4,
    "LOW": 0.1,
}


# ============================================================
# Scanning
# ============================================================
def _read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def scan_file(path: Path, skill_root: Path, rules: list[Rule] | None = None) -> list[Finding]:
    """Scan one file with all rules. Returns list of Finding."""
    if rules is None:
        rules = ALL_RULES
    findings: list[Finding] = []
    text = _read_text_safely(path)
    if not text:
        return findings

    try:
        rel = str(path.relative_to(skill_root))
    except ValueError:
        rel = str(path)

    lines = text.splitlines()
    for rule in rules:
        for pattern in rule.patterns:
            compiled = re.compile(pattern)
            for line_no, line in enumerate(lines, start=1):
                match = compiled.search(line)
                if not match:
                    continue
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        kill_chain_phase=rule.kill_chain_phase,
                        file=rel,
                        line=line_no,
                        pattern=pattern,
                        matched_text=match.group(0)[:160],
                        description=rule.description,
                        confidence=rule.confidence,
                    )
                )
    return findings


SCAN_SUFFIXES = {".md", ".txt", ".py", ".sh", ".js", ".ts", ".yaml", ".yml", ".json", ".toml"}


def scan_skill_directory(skill_path: Path) -> dict[str, Any]:
    """Scan a skill folder and return findings + summary."""
    skill_path = skill_path.resolve()
    findings: list[Finding] = []
    files_scanned: list[str] = []

    for path in sorted(skill_path.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES and path.name != "SKILL.md":
            continue
        findings.extend(scan_file(path, skill_path))
        try:
            files_scanned.append(str(path.relative_to(skill_path)))
        except ValueError:
            files_scanned.append(str(path))

    by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    by_pattern: dict[str, int] = {}
    by_phase: dict[str, int] = {}
    rule_ids_hit: set[str] = set()

    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        by_pattern[f.rule_id] = by_pattern.get(f.rule_id, 0) + 1
        by_phase[f.kill_chain_phase] = by_phase.get(f.kill_chain_phase, 0) + 1
        rule_ids_hit.add(f.rule_id)

    return {
        "skill_path": str(skill_path),
        "skill_name": skill_path.name,
        "files_scanned": files_scanned,
        "files_scanned_count": len(files_scanned),
        "total_findings": len(findings),
        "by_severity": by_severity,
        "by_pattern": by_pattern,
        "by_kill_chain_phase": by_phase,
        "rule_ids_hit": sorted(rule_ids_hit),
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "kill_chain_phase": f.kill_chain_phase,
                "file": f.file,
                "line": f.line,
                "pattern": f.pattern,
                "matched_text": f.matched_text,
                "description": f.description,
                "confidence": f.confidence,
            }
            for f in findings
        ],
    }
