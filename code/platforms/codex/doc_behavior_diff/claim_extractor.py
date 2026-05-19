from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any


NETWORK_TERMS = ("network", "http", "https", "api", "curl", "wget", "fetch", "request", "download", "upload")
CREDENTIAL_TERMS = ("token", "secret", "api key", "apikey", "credential", "ssh", "github_token", "openai_api_key", "anthropic_api_key")
FILESYSTEM_TERMS = ("file", "directory", "read", "write", "save", "path", "filesystem", "workspace")
INSTALL_TERMS = ("install", "setup", "npm install", "pip install", "apt install", "dependency")
EXECUTION_TERMS = ("execute", "run", "command", "shell", "bash", "sh", "script", "eval", "exec")
DOCKER_TERMS = ("docker", "container", "docker.sock")
OFFLINE_TERMS = ("offline", "local only", "no network", "does not use network", "no internet")
PROMPT_INJECTION_TERMS = (
    "ignore previous",
    "ignore safety",
    "ignore system",
    "system prompt",
    "developer message",
    "reveal",
    "exfiltrate",
    "bypass",
)


def extract_claims_from_archive(archive_path: Path) -> dict[str, Any]:
    skill_text, skill_member = read_skill_md_from_archive(archive_path)
    return extract_claims_from_text(skill_text, archive_name=archive_path.name, skill_member=skill_member)


def read_skill_md_from_archive(archive_path: Path) -> tuple[str, str | None]:
    with zipfile.ZipFile(archive_path) as archive:
        candidates = [name for name in archive.namelist() if Path(name.replace("\\", "/")).name.lower() == "skill.md"]
        if not candidates:
            return "", None
        member = sorted(candidates, key=lambda item: (item.count("/"), item))[0]
        data = archive.read(member)
    return data.decode("utf-8", errors="replace"), member


def extract_claims_from_text(text: str, *, archive_name: str = "", skill_member: str | None = None) -> dict[str, Any]:
    lowered = text.lower()
    sections = _extract_sections(text)
    purpose = _first_nonempty_line(text)
    explicit_no_network = any(term in lowered for term in OFFLINE_TERMS)
    hidden_instruction_terms = _matched_terms(lowered, PROMPT_INJECTION_TERMS)

    return {
        "archive_name": archive_name,
        "skill_member": skill_member,
        "skill_md_present": bool(text),
        "skill_md_treated_as_untrusted": True,
        "purpose": purpose,
        "allowed_operations": _section_or_keyword_lines(sections, text, ("usage", "workflow", "steps", "instructions", "what")),
        "expected_inputs": _section_or_keyword_lines(sections, text, ("input", "inputs", "requires", "arguments")),
        "expected_outputs": _section_or_keyword_lines(sections, text, ("output", "outputs", "result", "returns")),
        "claimed_network_use": _claim_bucket(lowered, NETWORK_TERMS, explicit_no_network),
        "claimed_filesystem_use": _claim_bucket(lowered, FILESYSTEM_TERMS, False),
        "claimed_credential_use": _claim_bucket(lowered, CREDENTIAL_TERMS, False),
        "claimed_install_setup_use": _claim_bucket(lowered, INSTALL_TERMS, False),
        "claimed_execution_behavior": _claim_bucket(lowered, EXECUTION_TERMS, False),
        "claimed_docker_use": _claim_bucket(lowered, DOCKER_TERMS, False),
        "claims_local_offline": explicit_no_network,
        "hidden_instruction_indicators": hidden_instruction_terms,
        "raw_skill_md_excerpt": text[:2000],
    }


def _claim_bucket(lowered: str, terms: tuple[str, ...], explicit_negative: bool) -> dict[str, Any]:
    matches = _matched_terms(lowered, terms)
    status = "declared" if matches else "not_declared"
    if explicit_negative:
        status = "denied"
    return {"status": status, "matched_terms": matches}


def _matched_terms(lowered: str, terms: tuple[str, ...]) -> list[str]:
    return sorted({term for term in terms if term in lowered})


def _extract_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "preamble"
    sections[current] = []
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if match:
            current = re.sub(r"[^a-z0-9]+", "_", match.group(1).strip().lower()).strip("_")
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _section_or_keyword_lines(sections: dict[str, str], text: str, keys: tuple[str, ...]) -> list[str]:
    selected: list[str] = []
    for key, value in sections.items():
        if any(term in key for term in keys) and value:
            selected.extend(_compact_lines(value))
    if selected:
        return selected[:12]
    lowered_keys = tuple(term.lower() for term in keys)
    for line in text.splitlines():
        lowered = line.lower()
        if any(term in lowered for term in lowered_keys):
            selected.append(line.strip())
    return [line for line in selected if line][:12]


def _compact_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()][:12]


def _first_nonempty_line(text: str) -> str:
    description = re.search(r"(?im)^description:\s*(.+?)\s*$", text)
    if description:
        return description.group(1).strip().strip('"')[:240]
    for line in text.splitlines():
        stripped = line.strip(" #\t")
        if stripped and stripped != "---":
            return stripped[:240]
    return ""
