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
    context: str = ""  # 命中行 ±N 行的上下文（带行号，命中行用 » 标记）


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
        severity="LOW",  # was MEDIUM; bare socket.connect is too generic, real signal needs nmap/portscan keywords (bumped in _classify_match)
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
        severity="HIGH",  # was CRITICAL; reading env vars alone is FP-prone, real harm needs E1 chain
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
        severity="MEDIUM",  # was HIGH; "must be followed"/"non-negotiable" wording alone is benign emphasis. Real prompt-injection (ignore/disregard/override) is bumped to HIGH in _classify_match.
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
        severity="MEDIUM",  # was HIGH; "first install" / "use another skill" is super common in install docs, real risk only when chained with E1/SC2
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


# Known-bad indicators: when these appear in a match, severity stays as-is.
# Without them, "example" patterns in .md docs (curl POST, requests.post)
# get downgraded to LOW to avoid false-positives on benign skill READMEs.
SINKHOLE_KEYWORDS = (
    "attacker.", "exfil", "c2.", ".onion", "webhook.site", "pastebin.com",
    "ngrok.io", "burpcollaborator", "interactsh", "requestbin",
)
# Rules that frequently produce noise inside markdown docs unless they hit
# a real sinkhole. Downgrade these in .md/.txt files when matched_text has
# no sinkhole keyword.
MARKDOWN_NOISE_RULE_IDS = {"E1", "SC1", "SC2", "PE2", "P7"}

# Real prompt-injection language. P1 base is MEDIUM (catches emphasis words
# like "non-negotiable" which legitimate skills also use). When the match
# contains a true override directive, bump to HIGH.
P1_OVERRIDE_KEYWORDS = ("ignore", "disregard", "override", "supersede")

# Reverse-shell signatures. SC1 base is HIGH (covers `os.system`, shell=True).
# When the match is a reverse-shell pattern, bump to CRITICAL.
SC1_REVSHELL_KEYWORDS = ("/bin/sh", "bash -i", "dup2", "nc -e ", " nc -e", "/bin/bash -i")

# Real port-scan / recon signals. E4 base is LOW (bare socket.connect is too
# generic). Bump to MEDIUM only when these keywords appear.
E4_SCAN_KEYWORDS = ("nmap", "netstat", "port_scan", "portscan", "port-scan")

# Unicode zero-width / bidi-override / non-printing characters used in
# steganographic prompt injection. P2 base is HIGH; bump these to CRITICAL.
P2_INVISIBLE_CHARS = (
    "​", "‌", "‍", "⁠", "﻿",
    "‪", "‫", "‬", "‭", "‮",  # bidi overrides
)


def _is_doc_context(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".txt"}


def _hit_real_sinkhole(matched_text: str) -> bool:
    low = matched_text.lower()
    return any(kw in low for kw in SINKHOLE_KEYWORDS)


def _build_context(lines: list[str], hit_line_no: int, radius: int = 3) -> str:
    """命中行周围 ±radius 行，带行号；命中行用 '»' 前缀标记，其余用 ' '。
    行号从 1 开始（hit_line_no 是 1-based）。"""
    start = max(1, hit_line_no - radius)
    end = min(len(lines), hit_line_no + radius)
    width = len(str(end))
    out: list[str] = []
    for n in range(start, end + 1):
        marker = "»" if n == hit_line_no else " "
        text = lines[n - 1].rstrip("\n")
        if len(text) > 200:
            text = text[:200] + " …"
        out.append(f"{marker} {str(n).rjust(width)} | {text}")
    return "\n".join(out)


def _classify_match(rule_id: str, base_severity: str, matched_text: str, doc_context: bool) -> str:
    """Decide the final severity of a single match based on rule-specific
    high-confidence / low-confidence indicators in the matched text.

    Bump-up cases (matched text indicates clear malicious intent):
      * E1 + sinkhole keyword     → CRITICAL  (attacker.example, .onion, ...)
      * SC1 + reverse-shell sig   → CRITICAL  (bin/sh -i, nc -e, dup2, ...)
      * E4 + scan keyword         → MEDIUM    (nmap, port_scan, ...)
      * P1 + override keyword     → HIGH      (ignore previous, disregard, ...)
      * P2 + invisible Unicode    → CRITICAL  (zero-width / bidi override)

    Bump-down cases (matched text in doc context with no high-confidence hint):
      * Any MARKDOWN_NOISE_RULE_IDS rule in .md/.txt with no sinkhole keyword
        → LOW
    """
    low = matched_text.lower()

    # ---- Per-rule bump-up rules ----
    if rule_id == "E1" and _hit_real_sinkhole(matched_text):
        return "CRITICAL"
    if rule_id == "SC1" and any(kw in low for kw in SC1_REVSHELL_KEYWORDS):
        return "CRITICAL"
    if rule_id == "E4" and any(kw in low for kw in E4_SCAN_KEYWORDS):
        return "MEDIUM"
    if rule_id == "P1" and any(kw in low for kw in P1_OVERRIDE_KEYWORDS):
        return "HIGH"
    if rule_id == "P2" and any(ch in matched_text for ch in P2_INVISIBLE_CHARS):
        return "CRITICAL"
    # P4: specific "mandatory_activation/protocol" sub-pattern is noisy emphasis,
    # not a coercion signal. Downgrade.
    if rule_id == "P4" and "mandatory" in low and ("activation" in low or "protocol" in low):
        return "LOW"

    # ---- Markdown-context downgrade ----
    if doc_context and rule_id in MARKDOWN_NOISE_RULE_IDS and not _hit_real_sinkhole(matched_text):
        return "LOW"

    return base_severity


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

    doc_context = _is_doc_context(path)
    lines = text.splitlines()
    for rule in rules:
        for pattern in rule.patterns:
            compiled = re.compile(pattern)
            for line_no, line in enumerate(lines, start=1):
                match = compiled.search(line)
                if not match:
                    continue
                matched = match.group(0)[:160]
                severity = _classify_match(rule.rule_id, rule.severity, matched, doc_context)
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        severity=severity,
                        kill_chain_phase=rule.kill_chain_phase,
                        file=rel,
                        line=line_no,
                        pattern=pattern,
                        matched_text=matched,
                        description=rule.description,
                        confidence=rule.confidence,
                        context=_build_context(lines, line_no, radius=3),
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
                "context": f.context,
            }
            for f in findings
        ],
    }
