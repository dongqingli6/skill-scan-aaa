---
name: pre-package-pipeline
description: >
  Single-command pre-flight pipeline before .skill packaging. Chains skill
  validation, security scanning, writing quality checks, and packaging into
  one gate. Use before creating .skill files, when "package skill" is
  requested, or to ensure quality before distribution. Triggers on "package
  skill", "pre-package", "pre-package-pipeline", "quality gate", or
  "prepare skill for distribution".
---

# Pre-Package Pipeline Skill

A comprehensive quality assurance pipeline that validates, scans, and packages skills into distributable `.skill` files. Designed to catch issues before distribution and ensure consistent skill quality.

## Pipeline Stages

### 1. Skill Validation
Verifies the skill directory structure and metadata integrity.

**Checks:**
- SKILL.md exists in skill root directory
- Valid YAML frontmatter with required fields (name, description)
- Directory structure complies with skill format
- All referenced scripts are syntactically valid
- No broken references or missing dependencies

**Gate Behavior:**
- Blocks packaging on ANY validation failure
- Cannot be skipped with `--force`
- Detailed error output pinpoints exact issues

### 2. Security Scan
Scans scripts and markdown for security vulnerabilities and risky patterns.

**Scans:**
- Shell script injection patterns (eval, system calls with unquoted vars)
- API key/token exposure in code or documentation
- Hardcoded credentials or secrets
- Unsafe file operations (chmod, rm patterns)
- SQL injection patterns
- XXE/XML vulnerabilities

**Gate Behavior:**
- **BLOCKS** on: critical and high severity findings
- **WARNS** on: medium and low severity findings
- Can be skipped with `--skip-security` flag
- `--force` allows packaging despite warnings (not blocks)

### 3. Writing Quality
Analyzes markdown files for AI-generated or low-quality writing patterns.

**Checks:**
- Detects generic AI writing patterns and filler language
- Flags overuse of hedging phrases and weak vocabulary
- Identifies repetitive structure and poor transitions
- Scores writing quality on 0-100 scale

**Gate Behavior:**
- **WARNS** on: score > 40
- **BLOCKS** on: score > 70
- Can be skipped with `--skip-slop` flag
- `--force` allows packaging despite warnings (not blocks)

### 4. Package
Creates a distributable `.skill` file (ZIP archive) with verified integrity.

**Actions:**
- Compresses skill directory to {skill-name}.skill
- Validates ZIP structure and file integrity
- Writes to specified output directory
- Only executes if gates 1-3 pass

**Output:**
- {skill-name}.skill archive in output directory
- File size and integrity report
- Archive contents list (with `--verbose`)

## Gate Criteria

| Stage | Block | Warn | Skip Flag | Bypass with --force |
|-------|-------|------|-----------|---------------------|
| Validation | Errors | — | None | No |
| Security | High/Critical | Medium/Low | `--skip-security` | Yes |
| Writing Quality | Score > 70 | Score > 40 | `--skip-slop` | Yes |
| Package | Compression errors | — | None | No |

## Configuration & Usage

### Basic Usage
```bash
python3 package_pipeline.py --skill-dir /path/to/skill --output /path/to/output
```

### Advanced Options
```bash
# Specify tool location for validators and scanners
python3 package_pipeline.py \
  --skill-dir /path/to/skill \
  --output /path/to/output \
  --tools-dir /path/to/tools

# Skip optional stages
python3 package_pipeline.py \
  --skill-dir /path/to/skill \
  --output /path/to/output \
  --skip-security \
  --skip-slop

# Force packaging despite warnings (but not errors)
python3 package_pipeline.py \
  --skill-dir /path/to/skill \
  --output /path/to/output \
  --force

# Generate detailed report
python3 package_pipeline.py \
  --skill-dir /path/to/skill \
  --output /path/to/output \
  --report /path/to/report.json \
  --verbose
```

### CLI Arguments
- `--skill-dir` (required): Path to skill directory to package
- `--output` (required): Output directory for .skill file
- `--tools-dir`: Directory containing validator/scanner scripts (auto-discovered if omitted)
- `--skip-security`: Skip security scanning stage
- `--skip-slop`: Skip writing quality check stage
- `--force`: Package despite warnings (warnings become non-blocking)
- `--report`: Write detailed JSON report to specified path
- `--verbose`: Print detailed output for each stage

## Integration with Existing Tools

The pipeline auto-discovers and chains these scripts if available in `tools-dir`:
- `skill_validator.py` — Skill structure validation
- `security_scan.py` — Security vulnerability detection
- `slop_scanner.py` — AI writing quality analysis

If scripts are not found, built-in validators run instead.

## Output Format

### Console Output
```
[STAGE 1/4] Skill Validation .............. PASS
[STAGE 2/4] Security Scan ................. PASS (0 critical, 0 high, 2 medium)
[STAGE 3/4] Writing Quality ............... WARN (score: 23/100)
[STAGE 4/4] Package ....................... DONE → my-skill.skill (15.2 KB)

Result: PASS with warnings
```

### JSON Report (with --report flag)
```json
{
  "skill_name": "my-skill",
  "timestamp": "2026-03-13T14:30:00Z",
  "stages": {
    "validation": {
      "status": "PASS",
      "errors": [],
      "warnings": []
    },
    "security": {
      "status": "PASS",
      "critical": 0,
      "high": 0,
      "medium": 2,
      "low": 0,
      "findings": []
    },
    "writing_quality": {
      "status": "WARN",
      "score": 23,
      "max_score": 100,
      "issues": []
    },
    "package": {
      "status": "DONE",
      "filename": "my-skill.skill",
      "size_kb": 15.2,
      "integrity": "VERIFIED"
    }
  },
  "overall_result": "PASS with warnings",
  "exit_code": 0
}
```

## Exit Codes
- `0`: Skill packaged successfully
- `1`: Blocked by gate (validation error or critical security/quality issues)
- `2`: Script error (invalid arguments, file not found, etc.)

## Use Cases

**Before creating .skill files:** Run pipeline to catch issues before distribution
**When "package skill" is requested:** Ensures skill meets quality standards
**Quality gates in CI/CD:** Automate quality checks in deployment pipelines
**Pre-distribution checks:** Verify security and quality before sharing skills

## Triggers

This skill activates on requests containing:
- "package skill"
- "pre-package"
- "pre-package-pipeline"
- "quality gate"
- "prepare skill for distribution"
