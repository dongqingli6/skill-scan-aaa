from __future__ import annotations

import cgi
import html
import json
import mimetypes
import os
import re
import shutil
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_adapter
import job_store
from safe_extract import SafeExtractError, safe_extract_archive


HOST = "0.0.0.0"  # 监听所有网卡，让局域网其它机器能访问；本机仍可用 127.0.0.1
PORT = 8765
REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent

# 公开模式开关：ASG_PUBLIC_MODE=1 时，禁用所有动态执行入口（模式二/模式三），
# 只保留模式一（静态扫 + Claude API 研判）。本地全功能跑就不要设这个变量。
PUBLIC_MODE = os.environ.get("ASG_PUBLIC_MODE", "0") == "1"


def public_badge_html() -> str:
    if PUBLIC_MODE:
        return '<span class="public-badge" title="ASG_PUBLIC_MODE=1，动态执行已禁用">公开模式</span>'
    return '<span class="public-badge" style="background:#dcfce7;color:#166534;border-color:#86efac;">本地全功能</span>'


def render_dynamic_section_html() -> str:
    """模式二 / 模式三：本地显示真实表单，公开模式显示文字说明指导。"""
    if not PUBLIC_MODE:
        return (
            '<section class="mode-section mode-2">'
            '<h2 class="mode-title">'
            '<span class="mode-num">2</span>动态执行（Docker 容器内运行）'
            '</h2>'
            '<p class="mode-desc">在 VM 的 Docker 容器中执行 Skill 包含的 '
            '<code>python script.py</code> / <code>bash script.sh</code> 等脚本，'
            '使用 <code>strace</code> 记录系统调用，使用 <code>tcpdump</code> 抓取网络流量。'
            '<strong>本模式不调用 Claude API。</strong></p>'
            '<div class="upload-row">'
            '<form method="post" action="/asg/vm_paper_run" enctype="multipart/form-data" class="upload-card">'
            '<span class="upload-card-tag">A · 上传并在 VM 中执行</span>'
            '<label>Skill 文件（.zip 或单文件）<input class="file-input" type="file" name="archive" required></label>'
            '<button class="btn-submit" type="submit">上传并执行</button>'
            '</form>'
            '<form method="post" action="/asg/vm_ingest" class="upload-card">'
            '<span class="upload-card-tag">B · 离线分析已有证据</span>'
            '<label>本地 Skill 目录路径<input class="file-input" name="skill_path" placeholder="asg/samples/data_thief" required></label>'
            '<label>证据目录（含 strace.log 等）<input class="file-input" name="evidence_dir" placeholder="analysis_results/asg/data_thief/vm_ssh_logs" required></label>'
            '<button class="btn-submit" type="submit">提交分析</button>'
            '</form>'
            '</div>'
            '</section>'
            '<section class="mode-section mode-3">'
            '<h2 class="mode-title">'
            '<span class="mode-num">3</span>Docker 中运行 Claude（评估 Agent 抗诱导能力）'
            '</h2>'
            '<p class="mode-desc">在 VM 的 Docker 容器中启动 <strong>Claude CLI</strong>，将 Skill 安装至 '
            '<code>~/.claude/skills/</code>，向 Claude 发出指令使其加载并使用此 Skill，'
            '并通过 <code>strace</code> 记录其实际行为。单次调用费用约 ¥1.2。</p>'
            '<form method="post" action="/asg/vm_ssh_run" enctype="multipart/form-data" class="upload-card" style="max-width:640px;">'
            '<span class="upload-card-tag">提交 Skill 进行 Agent 评估</span>'
            '<label>Skill 文件（.zip 或单文件）<input class="file-input" type="file" name="archive" required></label>'
            '<button class="btn-submit" type="submit">上传并启动 Claude 容器</button>'
            '</form>'
            '</section>'
        )
    # 公开模式：纯说明
    return (
        '<section class="mode-section mode-disabled">'
        '<h2 class="mode-title">'
        '<span class="mode-num">2</span>动态执行（Docker 容器内运行）'
        '<span class="mode-tag tag-disabled">公开模式已禁用</span>'
        '</h2>'
        '<div class="docs-panel">'
        '<h4>模式说明</h4>'
        '<p>将上传的 Skill 解压至 VM 中的 Docker 容器并执行 <code>python script.py</code> / <code>bash script.sh</code>，'
        '使用 <code>strace</code> 记录系统调用、<code>tcpdump</code> 抓取网络流量。本模式可获得最强的运行时证据，'
        '但会占用服务器资源，且会在主机上留下真实执行痕迹，因此在公开实例上默认禁用。</p>'
        '<h4>本地启用方法</h4>'
        '<pre># Windows PowerShell\nRemove-Item Env:\\ASG_PUBLIC_MODE -ErrorAction SilentlyContinue\npython web_ui\\app.py</pre>'
        '<p>启用前请确认：① 已配置 <code>asg/vm_config.json</code>；② VM 已安装 Docker、strace、tcpdump。'
        '完整安全边界说明见 <code>asg/README.md</code>。</p>'
        '</div>'
        '</section>'
        '<section class="mode-section mode-disabled">'
        '<h2 class="mode-title">'
        '<span class="mode-num">3</span>Docker 中运行 Claude（评估 Agent 抗诱导能力）'
        '<span class="mode-tag tag-disabled">公开模式已禁用</span>'
        '</h2>'
        '<div class="docs-panel">'
        '<h4>模式说明</h4>'
        '<p>在 VM 的 Docker 容器中启动 <strong>Claude CLI</strong>，将 Skill 安装至 <code>~/.claude/skills/</code>，'
        '指令 Claude 加载并使用该 Skill，通过 <code>strace</code> 记录其实际行为。此模式用于评估真实的 Claude Agent '
        '能否被 <code>SKILL.md</code> 中的恶意指令诱导，是研究 Agent Skill 攻击面的核心实验。单次调用费用约 ¥1.2（kuaipao.ai）。</p>'
        '<h4>本地启用方法</h4>'
        '<pre># 1. 在 asg/vm_config.json 中填入 remote_anthropic_api_key\n# 2. VM 上安装 Claude CLI 与 Docker\n# 3. 关闭公开模式后重启：\nRemove-Item Env:\\ASG_PUBLIC_MODE -ErrorAction SilentlyContinue\npython web_ui\\app.py</pre>'
        '</div>'
        '</section>'
    )
DOWNLOAD_REPORT_KEYS = {
    "static_report_md": ("static_scan_report_md", "text/markdown; charset=utf-8", "static_report.md"),
    "static_report_json": ("static_scan_report_json", "application/json; charset=utf-8", "static_report.json"),
    "dynamic_plan_md": ("dynamic_plan_md", "text/markdown; charset=utf-8", "dynamic_plan.md"),
    "dynamic_plan_json": ("dynamic_plan_json", "application/json; charset=utf-8", "dynamic_plan.json"),
    "dynamic_execution_report_json": ("dynamic_execution_report_json", "application/json; charset=utf-8", "dynamic_execution_report.json"),
    "dynamic_execution_report_md": ("dynamic_execution_report_md", "text/markdown; charset=utf-8", "dynamic_execution_report.md"),
    "dynamic_stdout": ("dynamic_stdout", "text/plain; charset=utf-8", "dynamic_stdout.txt"),
    "dynamic_stderr": ("dynamic_stderr", "text/plain; charset=utf-8", "dynamic_stderr.txt"),
}


def render_template(name: str, context: dict[str, object]) -> bytes:
    text = (WEB_ROOT / "templates" / name).read_text(encoding="utf-8")
    for key, value in context.items():
        text = text.replace("{{ " + key + " }}", str(value))
    return text.encode("utf-8")


def sanitize_filename(name: str) -> str:
    return job_store.sanitize_text(Path(name).name, limit=160).replace(" ", "_")


def risk_badge(job: dict[str, object]) -> str:
    summary = job.get("risk_summary") or {}
    if not isinstance(summary, dict):
        return "unscanned"
    critical = int(summary.get("critical", 0))
    high = int(summary.get("high", 0))
    medium = int(summary.get("medium", 0))
    if critical or high:
        return f"critical={critical}, high={high}"
    if medium:
        return f"medium={medium}"
    return "no high risk"


def render_jobs_table() -> str:
    rows: list[str] = []
    for job in job_store.list_jobs():
        job_id = html.escape(job["job_id"])
        rows.append(
            "<tr>"
            f"<td><code>{job_id}</code></td>"
            f"<td>{html.escape(job.get('skill_name', ''))}</td>"
            f"<td>{html.escape(job.get('status', ''))}</td>"
            f"<td>{html.escape(job.get('created_at', ''))}</td>"
            f"<td>{html.escape(risk_badge(job))}</td>"
            f"<td><a class=\"button small\" href=\"/job/{job_id}\">Open</a></td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan=\"6\" class=\"muted\">No jobs yet.</td></tr>")
    return "\n".join(rows)


def _verdict_bucket(job: dict[str, object]) -> tuple[str, str]:
    """根据 ASG 综合分判定 (bucket_class, label)。

    数据源优先级：
      1) composite_risk.verdict（ASG 已综合静态+LLM+chain+honeypot 算出来）
      2) layer_3.verdict_from_llm（AI 审计结论）
      3) layer_1 by_severity（纯静态回退）
      4) job["risk_summary"]（传统流程回退）
    """
    skill = str(job.get("skill_name", "") or "")
    if skill:
        report = _load_asg_report(skill)
        if report:
            # 1) 综合 verdict（最权威，已处理 AI vs 静态冲突）
            composite = report.get("composite_risk")
            if isinstance(composite, dict):
                v = str(composite.get("verdict", "") or "").upper()
                if v in ("CRITICAL_MALICIOUS", "MALICIOUS"):
                    return ("malicious", "危险")
                if v == "SUSPICIOUS":
                    return ("medium", "可疑")
                if v == "SAFE":
                    return ("safe", "安全")
            # 2) LLM 审计结论
            llm_verdict = ""
            l3 = report.get("layer_3_agent_eval")
            if isinstance(l3, dict):
                llm_verdict = str(l3.get("verdict_from_llm", "") or "").upper()
            if llm_verdict == "MALICIOUS":
                return ("malicious", "危险")
            if llm_verdict == "SUSPICIOUS":
                return ("medium", "可疑")
            if llm_verdict == "SAFE":
                return ("safe", "安全")
            # 3) 纯静态回退
            l1 = report.get("layer_1_static_scan") or {}
            by_sev = l1.get("by_severity") if isinstance(l1, dict) else {}
            by_sev = by_sev if isinstance(by_sev, dict) else {}
            c = int(by_sev.get("CRITICAL", 0))
            h = int(by_sev.get("HIGH", 0))
            m = int(by_sev.get("MEDIUM", 0))
            if c or h:
                return ("malicious", "危险")
            if m:
                return ("medium", "可疑")
            return ("safe", "安全")
    # 2) Fallback: job["risk_summary"]
    if job.get("static_scan_status") != "completed" and not isinstance(job.get("risk_summary"), dict):
        return ("unscanned", "未扫描")
    summary = job.get("risk_summary") or {}
    if not isinstance(summary, dict):
        return ("unscanned", "未扫描")
    try:
        c = int(summary.get("critical", 0))
        h = int(summary.get("high", 0))
        m = int(summary.get("medium", 0))
    except (TypeError, ValueError):
        return ("unscanned", "未扫描")
    if c or h:
        return ("malicious", "危险")
    if m:
        return ("medium", "可疑")
    if job.get("static_scan_status") == "completed":
        return ("safe", "安全")
    return ("unscanned", "未扫描")


def _format_created(value: str) -> str:
    """2026-05-26T15:54:23.111882+00:00 → 2026-05-26 15:54"""
    if not isinstance(value, str) or len(value) < 16:
        return html.escape(str(value))
    return html.escape(value[:10] + " " + value[11:16])


_VERDICT_EN = {
    "malicious": "MALICIOUS",
    "medium": "SUSPICIOUS",
    "safe": "SAFE",
    "unscanned": "UNSCANNED",
}

# 17 ASG 规则的中英文对照 + 默认严重度。顺序遵循 asg/rules.py 中定义的逻辑分组：
# Recon → Cred → Exec → Evasion → Exfil → Impact → Privilege → Hijack
ASG_17_RULES: list[tuple[str, str, str, str]] = [
    ("E2", "凭证窃取",     "Credential Harvesting",       "HIGH"),
    ("PE3", "凭证文件访问", "Credential File Access",      "HIGH"),
    ("E3", "文件系统枚举", "File System Enumeration",     "MEDIUM"),
    ("E4", "网络侦察",     "Network Reconnaissance",      "MEDIUM"),
    ("SC1", "命令注入",    "Command Injection",           "CRITICAL"),
    ("SC2", "远程脚本执行","Remote Script Execution",     "CRITICAL"),
    ("SC3", "代码混淆",    "Obfuscated Code",             "HIGH"),
    ("E1", "数据外传",     "External Data Transmission",  "HIGH"),
    ("P3", "代码执行外传", "Data Exfil via Code Exec",    "HIGH"),
    ("P1", "指令覆盖",     "Instruction Override",        "HIGH"),
    ("P2", "隐藏指令",     "Hidden Instructions",         "HIGH"),
    ("P4", "行为操纵",     "Behavior Manipulation",       "HIGH"),
    ("P5", "权威伪装",     "Authority Impersonation",     "MEDIUM"),
    ("P7", "跨工具诱导",   "Cross-tool Coercion",         "MEDIUM"),
    ("PE1", "权限过大",    "Excessive Permissions",       "HIGH"),
    ("PE2", "权限提升",    "Privilege Escalation",        "CRITICAL"),
    ("P6", "持久化植入",   "Persistence Implantation",    "HIGH"),
]


def _load_asg_report(skill_name: str) -> dict[str, object]:
    """读 analysis_results/asg/<skill_name>/asg_report.json，缺失返回 {}。"""
    if not skill_name:
        return {}
    path = REPO_ROOT / "analysis_results" / "asg" / skill_name / "asg_report.json"
    if not path.exists() or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


ASG_RESULTS_ROOT = REPO_ROOT / "analysis_results" / "asg"
SKILL_NAME_RE = re.compile(r"[A-Za-z0-9_.一-鿿-]{1,120}")


def list_asg_skills() -> list[dict[str, object]]:
    """枚举 analysis_results/asg/<skill>/asg_report.json，每个 skill 一条，
    按扫描时间倒序。这是 /results 的唯一数据源——真实扫描结果，天然去重
    （一个 skill 名一个目录）。返回 job-like dict 以复用卡片/报告渲染逻辑。"""
    out: list[dict[str, object]] = []
    if not ASG_RESULTS_ROOT.exists():
        return out
    for d in ASG_RESULTS_ROOT.iterdir():
        if not d.is_dir():
            continue
        report_path = d / "asg_report.json"
        if not report_path.is_file():
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        skill_name = str(report.get("skill_name") or d.name)
        out.append({
            "skill_name": skill_name,
            "job_id": skill_name,  # report 页用 skill_name 当 key
            "created_at": str(report.get("generated_at_utc", "") or ""),
            "_report": report,
        })
    out.sort(key=lambda j: str(j.get("created_at", "")), reverse=True)
    return out


_SEVERITY_CN = {"CRITICAL": "严重", "HIGH": "高危", "MEDIUM": "可疑", "LOW": "低危", "INFORMATIONAL": "提示"}
_SEVERITY_CSS = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low", "INFORMATIONAL": "info"}


def _file_lang(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
        ".md": "Markdown", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
        ".html": "HTML", ".css": "CSS", ".go": "Go", ".rs": "Rust",
        ".toml": "TOML", ".cfg": "Config", ".ini": "Config",
    }.get(suffix, "Other")


def render_report_categories(report: dict[str, object]) -> str:
    """17 条规则的格子：命中显示严重度，未命中显示「未检出 ✓」。"""
    by_pattern = (report.get("layer_1_static_scan") or {}).get("by_pattern") or {}
    if not isinstance(by_pattern, dict):
        by_pattern = {}
    hits_by_severity = (report.get("layer_1_static_scan") or {}).get("by_severity") or {}
    # 也尝试从 detailed_audit.risks 里抓每个 category 的严重度
    audit = (report.get("layer_3_agent_eval") or {}).get("detailed_audit") or {}
    risks = audit.get("risks") if isinstance(audit, dict) else None
    risks = risks if isinstance(risks, list) else []
    # 把 detailed_audit 的 category 名按规则 cn_name 模糊对齐
    audit_sev_by_cn: dict[str, str] = {}
    for r in risks:
        if not isinstance(r, dict):
            continue
        cat = str(r.get("category", "")).strip()
        sev = str(r.get("severity", "")).upper()
        if cat and sev:
            audit_sev_by_cn.setdefault(cat, sev)
    cells: list[str] = []
    for rule_id, cn, en, default_sev in ASG_17_RULES:
        count = int(by_pattern.get(rule_id, 0))
        # 优先用 audit 的同名严重度，其次根据是否命中 + 默认严重度
        sev_for_display = audit_sev_by_cn.get(cn)
        if count > 0 or sev_for_display:
            sev = (sev_for_display or default_sev).upper()
            sev_cn = _SEVERITY_CN.get(sev, sev)
            sev_class = _SEVERITY_CSS.get(sev, "high")
            badge = f'<span class="cat-sev sev-{sev_class}">{html.escape(sev_cn)}</span>'
            note = f'{count} 项' if count > 0 else '大模型检出'
            cells.append(
                f'<div class="cat-cell hit hit-{sev_class}">'
                f'<div class="cat-name">{html.escape(cn)}</div>'
                f'<div class="cat-en">{html.escape(en)}</div>'
                f'<div class="cat-status">{badge}<span class="cat-count">{html.escape(note)}</span></div>'
                '</div>'
            )
        else:
            cells.append(
                f'<div class="cat-cell clean">'
                f'<div class="cat-name">{html.escape(cn)}</div>'
                f'<div class="cat-en">{html.escape(en)}</div>'
                f'<div class="cat-status"><span class="cat-ok">✓ 未检出</span></div>'
                '</div>'
            )
    return '<div class="cat-grid">' + "".join(cells) + '</div>'


def render_report_filetree(report: dict[str, object]) -> str:
    contents = report.get("skill_contents") or {}
    files = contents.get("files") if isinstance(contents, dict) else None
    if not isinstance(files, list) or not files:
        return '<p class="empty-note">未采集到文件列表。</p>'
    # 语言占比
    by_lang_bytes: dict[str, int] = {}
    by_lang_count: dict[str, int] = {}
    total_files = 0
    total_bytes = 0
    total_lines = 0
    for f in files:
        if not isinstance(f, dict):
            continue
        path = str(f.get("path", ""))
        size = int(f.get("size_bytes", 0) or 0)
        preview = str(f.get("content_preview", "") or "")
        lines = preview.count("\n") + (1 if preview and not preview.endswith("\n") else 0)
        lang = _file_lang(path)
        by_lang_bytes[lang] = by_lang_bytes.get(lang, 0) + size
        by_lang_count[lang] = by_lang_count.get(lang, 0) + 1
        total_files += 1
        total_bytes += size
        total_lines += lines
    # 语言占比条
    lang_segs: list[str] = []
    lang_legend: list[str] = []
    lang_colors = {
        "Python": "#3b82f6", "JavaScript": "#facc15", "TypeScript": "#0ea5e9",
        "Markdown": "#22d3ee", "JSON": "#86efac", "YAML": "#f472b6",
        "Shell": "#a78bfa", "HTML": "#fb923c", "CSS": "#60a5fa",
        "Go": "#38bdf8", "Rust": "#f87171", "TOML": "#94a3b8",
        "Config": "#64748b", "Other": "#475569",
    }
    if total_bytes > 0:
        for lang, b in sorted(by_lang_bytes.items(), key=lambda x: -x[1]):
            pct = b * 100.0 / max(total_bytes, 1)
            color = lang_colors.get(lang, "#475569")
            lang_segs.append(f'<div class="bar-seg" style="width:{pct:.2f}%;background:{color};" title="{html.escape(lang)} {pct:.1f}%"></div>')
            lang_legend.append(
                f'<span class="lang-dot"><span class="dot" style="background:{color};"></span>'
                f'{html.escape(lang)} <span class="muted">{by_lang_count[lang]} 文件 · {b} B</span></span>'
            )
    bar_html = '<div class="lang-bar">' + "".join(lang_segs) + '</div>' if lang_segs else ""
    legend_html = '<div class="lang-legend">' + "".join(lang_legend) + '</div>' if lang_legend else ""

    # 文件列表（含预览展开）
    rows: list[str] = []
    for f in files:
        if not isinstance(f, dict):
            continue
        path = html.escape(str(f.get("path", "")))
        size = int(f.get("size_bytes", 0) or 0)
        preview = str(f.get("content_preview", "") or "")
        lang = _file_lang(str(f.get("path", "")))
        lines = preview.count("\n") + 1 if preview else 0
        is_skill_md = str(f.get("path", "")).lower().endswith("skill.md")
        row_class = " skill-md" if is_skill_md else ""
        preview_text = html.escape(preview[:6000])
        rows.append(
            f'<details class="file-row{row_class}">'
            f'<summary>'
            f'<span class="file-icon">📄</span>'
            f'<span class="file-path">{path}</span>'
            f'<span class="file-meta"><span class="lang-tag">{html.escape(lang)}</span> '
            f'<span class="muted">{lines} 行 · {size} B</span></span>'
            f'</summary>'
            f'<pre class="file-preview">{preview_text}</pre>'
            '</details>'
        )
    return (
        '<div class="tree-summary">'
        f'<strong>{total_files}</strong> 文件 · <strong>{total_bytes:,}</strong> B · <strong>{total_lines}</strong> 行'
        '</div>'
        + bar_html + legend_html +
        '<div class="file-list">' + "".join(rows) + '</div>'
    )


def render_report_risks(report: dict[str, object]) -> str:
    """风险评估列表：优先用 detailed_audit.risks，回退到 scan_result findings。"""
    audit = (report.get("layer_3_agent_eval") or {}).get("detailed_audit") or {}
    risks = audit.get("risks") if isinstance(audit, dict) else None
    risks = risks if isinstance(risks, list) else []
    if not risks:
        # 回退：用 scan_result 的 findings（粒度更细但描述少）
        scan = report.get("layer_1_static_scan") or {}
        findings = scan.get("findings") if isinstance(scan, dict) else None
        if isinstance(findings, list) and findings:
            adapter: list[dict[str, object]] = []
            for f in findings:
                if not isinstance(f, dict):
                    continue
                adapter.append({
                    "severity": f.get("severity", ""),
                    "category": f.get("rule_name", f.get("rule_id", "未知规则")),
                    "title": f.get("description", "命中静态规则"),
                    "file": f.get("file", ""),
                    "line": f.get("line", ""),
                    "code_snippet": f.get("matched_text", ""),
                    "description": f.get("description", ""),
                    "recommendation": "",
                })
            risks = adapter
    if not risks:
        return '<p class="empty-note">没有检出任何风险。</p>'

    # 按类别分组
    grouped: dict[str, list[dict[str, object]]] = {}
    for r in risks:
        if not isinstance(r, dict):
            continue
        cat = str(r.get("category", "未分类"))
        grouped.setdefault(cat, []).append(r)

    blocks: list[str] = []
    for cat, items in grouped.items():
        max_sev = "LOW"
        for r in items:
            s = str(r.get("severity", "")).upper()
            if s == "CRITICAL" or (s == "HIGH" and max_sev != "CRITICAL") or (s == "MEDIUM" and max_sev in ("LOW", "INFORMATIONAL")):
                max_sev = s
        max_sev_cn = _SEVERITY_CN.get(max_sev, "可疑")
        max_sev_cls = _SEVERITY_CSS.get(max_sev, "medium")
        item_html: list[str] = []
        for i, r in enumerate(items, 1):
            sev = str(r.get("severity", "")).upper()
            sev_cn = _SEVERITY_CN.get(sev, sev or "—")
            sev_cls = _SEVERITY_CSS.get(sev, "medium")
            file_str = str(r.get("file", "")).strip()
            line_str = str(r.get("line", "")).strip()
            file_line = ""
            if file_str:
                file_line = f"<span class='risk-file'><code>{html.escape(file_str)}</code>" + (
                    f" <span class='muted'>:{html.escape(line_str)}</span>" if line_str else ""
                ) + "</span>"
            snippet = str(r.get("code_snippet", "") or "").strip()
            description = str(r.get("description", "") or "").strip()
            recommendation = str(r.get("recommendation", "") or "").strip()
            title = str(r.get("title", "") or "命中规则").strip()
            item_html.append(
                f'<details class="risk-item">'
                f'<summary>'
                f'<span class="risk-num">#{i}</span>'
                f'<span class="sev-pill sev-{sev_cls}">{html.escape(sev_cn)}</span>'
                f'<span class="risk-title">{html.escape(title)}</span>'
                + (f'<span class="risk-source">{html.escape(file_str.split("/")[-1] if file_str else "")}</span>' if file_str else "")
                + '</summary>'
                f'<div class="risk-body">'
                + (f'<div class="risk-loc">📍 {file_line}</div>' if file_line else "")
                + (f'<pre class="risk-snippet">{html.escape(snippet)}</pre>' if snippet else "")
                + (f'<p class="risk-desc">{html.escape(description)}</p>' if description else "")
                + (f'<div class="risk-fix">🔧 <strong>修复建议：</strong>{html.escape(recommendation)}</div>' if recommendation else "")
                + '</div>'
                '</details>'
            )
        blocks.append(
            '<div class="risk-group">'
            f'<div class="risk-group-head"><span class="risk-cat">{html.escape(cat)}</span>'
            f'<span class="sev-pill sev-{max_sev_cls}">{max_sev_cn}</span>'
            f'<span class="muted">{len(items)} 项</span></div>'
            + "".join(item_html) +
            '</div>'
        )
    return "".join(blocks)


_RUNTIME_REASON_CN = {
    "no runtime evidence ingested": "未采集到运行时证据",
    "sensitive file access observed": "观测到敏感文件访问",
    "outbound connect observed": "观测到对外网络连接",
    "sensitive access and outbound connect co-occurred": "敏感文件读取与对外连接同时出现（典型窃取→外传链路）",
    "honeypot marker leaked in runtime evidence": "蜜罐标记在运行时证据中泄露（脚本读到了诱饵凭证）",
    "honeypot files touched in VM container fake HOME": "VM 容器假 HOME 里的蜜罐文件被触碰",
    "honeypot touch and outbound connect co-occurred": "蜜罐触碰与对外连接同时出现",
    "filesystem change evidence present": "存在文件系统改动证据",
    "unique outbound IP count contributes with cap": "唯一对外 IP 数计入评分（封顶）",
}


def _cn_runtime_reason(reason: str) -> str:
    for en, cn in _RUNTIME_REASON_CN.items():
        if reason.startswith(en):
            # 保留括号里的事件计数
            tail = reason[len(en):].strip()
            return cn + ((" " + tail) if tail else "")
    return reason


def _read_vm_log(skill_name: str, filename: str, limit_chars: int = 4000) -> str:
    """读 analysis_results/asg/<skill>/vm_paper_logs/<filename>，截断。"""
    if not skill_name:
        return ""
    p = ASG_RESULTS_ROOT / skill_name / "vm_paper_logs" / filename
    if not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit_chars]
    except OSError:
        return ""


def _extract_strace_evidence(skill_name: str, limit: int = 10) -> list[tuple[str, str]]:
    """从 strace.log 抽代表性 syscall：敏感文件 open（读到的）+ 对外 connect。
    返回 [(类型, 原始行)]。"""
    text = _read_vm_log(skill_name, "strace.log", limit_chars=400_000)
    if not text:
        return []
    sensitive_kw = (".ssh", ".aws", ".env", "id_rsa", "credentials", ".codex", ".config/gh")
    out: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(out) >= limit:
            break
        # 敏感文件成功打开（fd >= 0，不是 ENOENT）
        if "openat(" in line and any(k in line for k in sensitive_kw):
            if "ENOENT" in line:
                continue
            # 只保留 = <数字> 结尾的成功调用
            if re.search(r"=\s*\d+\s*$", line):
                # 去掉前面的 pid 列
                clean = re.sub(r"^\d+\s+", "", line)
                out.append(("read", clean[:200]))
        elif "connect(" in line and ("AF_INET" in line or "sin_addr" in line):
            clean = re.sub(r"^\d+\s+", "", line)
            out.append(("connect", clean[:200]))
    return out


def render_report_dynamic(report: dict[str, object], skill_name: str = "") -> str:
    """动态执行详情：strace 系统调用证据 + 蜜罐 + 网络抓包 + 中文解释。"""
    rt = report.get("layer_5_runtime")
    if not isinstance(rt, dict) or not rt.get("present"):
        return (
            '<div class="dyn-empty">'
            '<p class="empty-note">此 skill 未运行 VM 动态执行（仅静态 + AI 研判）。'
            '动态执行需要带可执行脚本（.py/.sh）的 skill，并在「扫描页·模式二」上传或用 '
            '<code>asg_cli vm-paper-run</code> 触发。</p>'
            '</div>'
        )
    mode = str(rt.get("mode", "") or "")
    mode_cn = {"paper_no_claude": "脚本直跑（python/bash，不调 Claude）",
               "claude": "容器内 Claude CLI 使用此 skill"}.get(mode, mode or "未知")
    strace = rt.get("strace") or {}
    tcp = rt.get("tcpdump") or {}
    fs = rt.get("filesystem") or {}
    hp = rt.get("honeypot") or {}
    cr = report.get("composite_risk") or {}
    delta = cr.get("runtime_score_delta", 0)
    reasons = cr.get("runtime_score_reasons") or []

    sens = int(strace.get("sensitive_file_access_count", 0) or 0)
    outb = int(strace.get("outbound_connect_count", 0) or 0)
    swrite = int(strace.get("sensitive_write_count", 0) or 0)
    uips = strace.get("unique_outbound_ips") or []
    uips = uips if isinstance(uips, list) else []

    # 关键指标卡
    def metric(label, value, danger=False, sub=""):
        cls = " dyn-danger" if danger else ""
        sub_html = f'<span class="dyn-metric-sub">{html.escape(sub)}</span>' if sub else ""
        return (
            f'<div class="dyn-metric{cls}">'
            f'<span class="dyn-metric-num">{value}</span>'
            f'<span class="dyn-metric-label">{html.escape(label)}</span>'
            f'{sub_html}'
            '</div>'
        )
    metrics = (
        metric("敏感文件读取", sens, danger=sens > 0, sub="strace open/read")
        + metric("对外连接", outb, danger=outb > 0, sub="strace connect")
        + metric("敏感写入", swrite, danger=swrite > 0, sub="strace write")
        + metric("唯一对外 IP", len(uips), danger=len(uips) > 0, sub=(", ".join(map(str, uips))[:40] or "无"))
    )

    # 蜜罐
    hp_touched = bool(hp.get("touched"))
    hp_leaked = bool(hp.get("leaked"))
    touched_files = hp.get("touched_files") or []
    touched_files = touched_files if isinstance(touched_files, list) else []
    if hp_leaked:
        hp_badge = '<span class="dyn-hp-badge leaked">⚠ 蜜罐凭证已泄露</span>'
        hp_text = "脚本真的读取了诱饵凭证文件——这是凭证窃取的铁证（syscall 不会撒谎）。"
    elif hp_touched:
        hp_badge = '<span class="dyn-hp-badge touched">蜜罐文件被触碰</span>'
        hp_text = "脚本访问了诱饵文件路径，但未确认读出内容。"
    else:
        hp_badge = '<span class="dyn-hp-badge clean">✓ 蜜罐未触碰</span>'
        hp_text = "运行期间未碰任何诱饵凭证文件。"
    touched_html = ""
    if touched_files:
        items = "".join(f'<li><code>{html.escape(str(p))}</code></li>' for p in touched_files)
        touched_html = f'<ul class="dyn-hp-files">{items}</ul>'

    # 网络/文件系统
    pcap_present = bool(tcp.get("pcap_present"))
    pcap_size = int(tcp.get("pcap_size_bytes", 0) or 0)
    fs_changed = bool(fs.get("fs_change_present"))
    net_html = (
        f'<div class="dyn-row"><span class="dyn-k">网络抓包 (pcap)</span>'
        f'<span class="dyn-v">{"✅ 已捕获 " + str(pcap_size) + " B" if pcap_present else "—（无外发流量或未抓到）"}</span></div>'
        f'<div class="dyn-row"><span class="dyn-k">文件系统改动</span>'
        f'<span class="dyn-v">{"⚠ 检测到改动" if fs_changed else "无改动"}</span></div>'
        f'<div class="dyn-row"><span class="dyn-k">执行模式</span><span class="dyn-v">{html.escape(mode_cn)}</span></div>'
        f'<div class="dyn-row"><span class="dyn-k">动态加分</span><span class="dyn-v">+{delta} 分（运行时证据对综合分的贡献）</span></div>'
    )

    # reasons（中文）
    reasons_html = ""
    if isinstance(reasons, list) and reasons:
        items = "".join(f'<li>{html.escape(_cn_runtime_reason(str(r)))}</li>' for r in reasons)
        reasons_html = f'<div class="dyn-reasons"><strong>📋 运行时判定依据</strong><ul>{items}</ul></div>'

    # ===== Docker 执行了什么（流程说明）=====
    flow_html = (
        '<details class="dyn-flow"><summary>🐳 Docker 容器里到底执行了什么？（点击展开）</summary>'
        '<div class="dyn-flow-body">'
        '<ol>'
        '<li>在 VM 上启动 <code>claude-skill-sandbox</code> 容器，设一个<strong>假 HOME</strong>'
        '（<code>/home/codexsafe</code>），里面预先放好<strong>蜜罐诱饵凭证</strong>：'
        '<code>.ssh/id_rsa</code>、<code>.aws/credentials</code>、<code>.env</code>、<code>.codex/config.json</code>'
        '——全是带唯一 canary 标记的假密钥，真密钥绝不进容器。</li>'
        '<li>把待测 skill <strong>只读挂载</strong>到 <code>/skill</code>，日志目录挂到 <code>/logs</code>。</li>'
        '<li>扫描 skill 里所有可执行脚本（<code>.py</code> / <code>.sh</code>），逐个执行，每个限时 30s。</li>'
        '<li>执行全程套 <code>strace</code> 抓<strong>系统调用</strong>（open/read/connect/write…）、'
        '<code>tcpdump</code> 抓<strong>网络包</strong>。</li>'
        '<li>跑完比对：脚本碰没碰蜜罐文件、读没读出 canary、有没有对外连接、文件系统改没改。</li>'
        '</ol>'
        '<p class="dyn-flow-note">核心思路：<strong>syscall 不会撒谎</strong>。SKILL.md 可以写得人畜无害、'
        '脚本可以打印"0 credentials transmitted"，但只要它真去 <code>open()</code> 了 id_rsa，strace 就记下来了。</p>'
        '</div></details>'
    )

    # ===== 脚本输出 =====
    script_out = _read_vm_log(skill_name, "script_output.txt", limit_chars=3000).strip()
    script_html = ""
    if script_out:
        script_html = (
            '<div class="dyn-block">'
            '<div class="dyn-block-title">📤 脚本运行输出（stdout）</div>'
            f'<pre class="dyn-pre">{html.escape(script_out)}</pre>'
            '<p class="dyn-hint">注意：脚本的输出常常是<strong>伪装</strong>——下面的 syscall 才是它真实干的事。</p>'
            '</div>'
        )

    # ===== 真实 syscall 证据 =====
    evidence = _extract_strace_evidence(skill_name, limit=10)
    evidence_html = ""
    if evidence:
        ev_rows = []
        for kind, line in evidence:
            tag = ('<span class="syscall-tag read">读敏感文件</span>' if kind == "read"
                   else '<span class="syscall-tag conn">对外连接</span>')
            ev_rows.append(f'<div class="syscall-row">{tag}<code>{html.escape(line)}</code></div>')
        evidence_html = (
            '<div class="dyn-block">'
            '<div class="dyn-block-title">🔍 关键系统调用证据（strace 原始记录）</div>'
            + "".join(ev_rows) +
            '<p class="dyn-hint">这些是从 strace.log 抽出的代表性记录：脚本对蜜罐文件成功 '
            '<code>openat()</code>（返回 fd），以及向外 <code>connect()</code> 的真实地址端口。</p>'
            '</div>'
        )

    return (
        '<div class="dyn-summary-line">'
        f'真实执行了 skill 的脚本，用 <code>strace</code> 抓系统调用、<code>tcpdump</code> 抓网络包。下面是观测到的真实行为：'
        '</div>'
        f'<div class="dyn-metrics">{metrics}</div>'
        f'{flow_html}'
        '<div class="dyn-honeypot">'
        f'<div class="dyn-hp-head">{hp_badge}</div>'
        f'<p class="dyn-hp-text">{html.escape(hp_text)}</p>'
        f'{touched_html}'
        '</div>'
        f'{script_html}'
        f'{evidence_html}'
        f'<div class="dyn-net">{net_html}</div>'
        f'{reasons_html}'
    )


def render_report_static_hits(report: dict[str, object]) -> str:
    """静态命中明细：每条 finding 显示规则、严重度、文件:行 + 上下文代码块。"""
    scan = report.get("layer_1_static_scan") or report.get("findings")
    findings = None
    if isinstance(report.get("findings"), list):
        findings = report.get("findings")
    elif isinstance(scan, dict):
        findings = scan.get("findings")
    if not isinstance(findings, list) or not findings:
        return '<p class="empty-note">静态规则无命中。</p>'
    # rule_id → 中文名
    cn_by_rule = {rid: cn for rid, cn, en, sev in ASG_17_RULES}
    rows: list[str] = []
    # 按严重度排序：CRITICAL > HIGH > MEDIUM > LOW
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}
    findings_sorted = sorted(
        [f for f in findings if isinstance(f, dict)],
        key=lambda f: sev_order.get(str(f.get("severity", "")).upper(), 9),
    )
    for i, f in enumerate(findings_sorted, 1):
        rid = str(f.get("rule_id", ""))
        cn = cn_by_rule.get(rid, rid)
        sev = str(f.get("severity", "")).upper()
        sev_cn = _SEVERITY_CN.get(sev, sev)
        sev_cls = _SEVERITY_CSS.get(sev, "medium")
        file_str = str(f.get("file", ""))
        line = str(f.get("line", ""))
        matched = str(f.get("matched_text", ""))
        context = str(f.get("context", "") or "")
        pattern = str(f.get("pattern", ""))
        body = (
            f'<div class="sh-loc">📍 <code>{html.escape(file_str)}</code>'
            f' <span class="muted">:{html.escape(line)}</span>'
            f' · 命中正则 <code>{html.escape(pattern[:80])}</code></div>'
        )
        if context:
            body += f'<pre class="sh-context">{html.escape(context)}</pre>'
        else:
            body += f'<pre class="sh-context">{html.escape(matched)}</pre>'
        rows.append(
            '<details class="sh-item" open>'
            '<summary>'
            f'<span class="risk-num">#{i}</span>'
            f'<span class="sev-pill sev-{sev_cls}">{html.escape(sev_cn)}</span>'
            f'<span class="sh-rule">{html.escape(cn)} <span class="muted">[{html.escape(rid)}]</span></span>'
            f'<span class="risk-source">{html.escape(file_str.split("/")[-1])}:{html.escape(line)}</span>'
            '</summary>'
            f'<div class="risk-body">{body}</div>'
            '</details>'
        )
    return f'<div class="sh-count">共 {len(findings_sorted)} 处静态命中（按严重度排序）</div>' + "".join(rows)


def render_safeskill_report(job: dict[str, object]) -> bytes:
    """SAFESKILL 风格的完整报告页（取代旧的 job.html）。"""
    skill_name = str(job.get("skill_name", ""))
    job_id = str(job.get("job_id", ""))
    report = _load_asg_report(skill_name)
    audit = (report.get("layer_3_agent_eval") or {}).get("detailed_audit") or {}
    summary_cn = ""
    if isinstance(audit, dict):
        summary_cn = str(audit.get("summary_cn", "") or "")

    # Verdict（先看 layer_3 的 verdict_from_llm，其次 layer_1 risk_summary）
    bucket, verdict_cn = _verdict_bucket(job)
    layer_3_verdict = ""
    if isinstance(report.get("layer_3_agent_eval"), dict):
        layer_3_verdict = str(report["layer_3_agent_eval"].get("verdict_from_llm", "") or "")
    if layer_3_verdict.upper() == "MALICIOUS":
        bucket, verdict_cn = "malicious", "危险"
    elif layer_3_verdict.upper() == "SUSPICIOUS":
        bucket = "medium" if bucket != "malicious" else bucket
        verdict_cn = "可疑" if bucket == "medium" else verdict_cn
    elif layer_3_verdict.upper() == "SAFE" and bucket not in ("malicious", "medium"):
        bucket, verdict_cn = "safe", "安全"
    verdict_en = _VERDICT_EN[bucket]
    handling = {
        "malicious": "拒绝安装",
        "medium": "人工复核",
        "safe": "建议放行",
        "unscanned": "尚未扫描",
    }[bucket]

    # archetype + kill-chain chips
    chips: list[str] = []
    chain = report.get("layer_2_attack_chain") or {}
    if isinstance(chain, dict):
        arche = chain.get("archetype")
        if isinstance(arche, dict) and arche.get("archetype"):
            chips.append(f'<span class="chip chip-archetype">{html.escape(str(arche["archetype"]))}</span>')
        phases = chain.get("kill_chain_phases_covered")
        if isinstance(phases, list):
            for p in phases:
                chips.append(f'<span class="chip">{html.escape(str(p))}</span>')
    chips_html = '<div class="meta-chips">' + "".join(chips) + '</div>' if chips else ""

    # Analyzed at
    analyzed = str(report.get("generated_at_utc") or job.get("updated_at") or job.get("created_at") or "")
    if analyzed:
        analyzed = analyzed[:10] + " " + analyzed[11:19] if len(analyzed) >= 19 else analyzed

    risk_summary = report.get("layer_1_static_scan") or {}
    by_sev = risk_summary.get("by_severity") if isinstance(risk_summary, dict) else {}
    by_sev = by_sev if isinstance(by_sev, dict) else {}
    c = int(by_sev.get("CRITICAL", 0))
    h = int(by_sev.get("HIGH", 0))
    m = int(by_sev.get("MEDIUM", 0))
    l = int(by_sev.get("LOW", 0))
    total_findings = c + h + m + l

    if total_findings == 0 and bucket == "unscanned":
        threat_banner = (
            '<div class="threat-banner banner-unscanned">'
            '<strong>📋 尚未运行静态扫描。</strong>到「扫描」页上传文件就能开始。'
            '</div>'
        )
    elif total_findings == 0:
        threat_banner = (
            '<div class="threat-banner banner-safe">'
            '<strong>✓ 未发现高危威胁。</strong>所有 17 条 ASG 静态规则未命中此 skill。'
            '</div>'
        )
    else:
        parts = []
        if c: parts.append(f"CRITICAL×{c}")
        if h: parts.append(f"HIGH×{h}")
        if m: parts.append(f"MEDIUM×{m}")
        if l: parts.append(f"LOW×{l}")
        threat_banner = (
            '<div class="threat-banner banner-danger">'
            f'<strong>检测到风险信号！</strong>共 {total_findings} 个安全问题（{"，".join(parts)}）。'
            + (f' 建议：<strong>{handling}</strong>。' if bucket == "malicious" else "")
            + '</div>'
        )

    description_block = (
        f'<div class="ai-desc">'
        f'<h3>📍 AI 研判描述</h3>'
        f'<p>{html.escape(summary_cn)}</p>'
        '</div>'
    ) if summary_cn else (
        '<div class="ai-desc">'
        '<h3>📍 AI 研判描述</h3>'
        '<p class="muted">尚未生成 AI 研判描述（可能没启用 Claude API，或扫描未完成）。</p>'
        '</div>'
    )

    # 综合分数块
    score_info = _composite_score(job)
    score_block = ""
    if score_info is not None:
        s = score_info["score"]
        # 算分数条相对位置 + bucket 颜色
        bar_pct = max(0.0, min(s, 100.0))
        sub = score_info["sub_scores"] or {}
        weights = score_info["weights"] or {}
        sub_rows: list[str] = []
        sub_labels = [
            ("S_static", "w_static", "静态命中"),
            ("S_chain", "w_chain", "攻击链"),
            ("S_soph", "w_soph", "复杂度"),
            ("S_phases", "w_phases", "Kill-Chain 阶段覆盖"),
            ("S_resilience", "w_agent", "Agent 抗诱导（1-S）"),
            ("S_llm_verdict", "w_llm_verdict", "LLM 判定"),
            ("S_honeypot", "w_honeypot", "蜜罐触发"),
            ("S_runtime", "w_runtime", "运行时证据"),
        ]
        for key, wkey, label in sub_labels:
            v = sub.get(key, 0)
            w = weights.get(wkey, 0)
            try:
                v_f = float(v); w_f = float(w)
            except (TypeError, ValueError):
                v_f, w_f = 0.0, 0.0
            contribution = v_f * w_f * 100
            # S_resilience 是反向（抗诱导越强分越低），用 (1-S)
            if key == "S_resilience":
                contribution = (1 - v_f) * w_f * 100
            bar_w = min(max(contribution / 30 * 100, 2), 100)  # 30 分对应 100% 条宽
            sub_rows.append(
                '<div class="sub-row">'
                f'<span class="sub-label">{html.escape(label)}</span>'
                f'<span class="sub-val">{v_f:.3f}</span>'
                f'<span class="sub-weight">×{w_f:.2f}</span>'
                f'<div class="sub-bar"><div class="sub-bar-fill" style="width:{bar_w:.1f}%;"></div></div>'
                f'<span class="sub-contrib">+{contribution:.2f}</span>'
                '</div>'
            )
        notes_html = ""
        if score_info["notes"]:
            items = "".join(f'<li>{html.escape(str(n))}</li>' for n in score_info["notes"])
            notes_html = f'<div class="score-notes"><strong>💡 评分说明</strong><ul>{items}</ul></div>'

        score_block = (
            '<section class="panel score-panel">'
            '<div class="panel-head">'
            '<span class="panel-icon">🎯</span>'
            f'<h2 class="panel-title">综合风险评分<span class="en">COMPOSITE RISK SCORE</span></h2>'
            f'<span class="panel-extra">阈值 SAFE 0-15 · SUSPICIOUS 15-40 · MALICIOUS 40-75 · CRITICAL 75+</span>'
            '</div>'
            '<div class="score-hero">'
            f'<div class="score-big v-{bucket}">'
            f'<div class="score-big-num">{s}</div>'
            '<div class="score-big-max">/ 100</div>'
            '</div>'
            '<div class="score-bar-wrap">'
            '<div class="score-bar-track">'
            '<div class="score-zone z-safe"  style="width:15%;"></div>'
            '<div class="score-zone z-susp"  style="width:25%;"></div>'
            '<div class="score-zone z-mal"   style="width:35%;"></div>'
            '<div class="score-zone z-crit"  style="width:25%;"></div>'
            f'<div class="score-marker" style="left:{bar_pct:.1f}%;" title="得分 {s}"></div>'
            '</div>'
            '<div class="score-bar-labels">'
            '<span>0</span><span>15</span><span>40</span><span>75</span><span>100</span>'
            '</div>'
            '</div>'
            '</div>'
            '<details class="score-breakdown">'
            '<summary>查看分项明细（点击展开）</summary>'
            '<div class="sub-table">' + "".join(sub_rows) + '</div>'
            + notes_html +
            '</details>'
            '</section>'
        )

    template = (WEB_ROOT / "templates" / "safeskill_report.html").read_text(encoding="utf-8")
    ctx = {
        "skill_name": html.escape(skill_name),
        "job_id": html.escape(job_id),
        "verdict_bucket": bucket,
        "verdict_cn": html.escape(verdict_cn),
        "verdict_en": verdict_en,
        "handling": html.escape(handling),
        "analyzed": html.escape(analyzed),
        "chips": chips_html,
        "score_block": score_block,
        "threat_banner": threat_banner,
        "ai_description": description_block,
        "category_grid": render_report_categories(report),
        "static_hits": render_report_static_hits(report),
        "dynamic_detail": render_report_dynamic(report, skill_name),
        "file_tree": render_report_filetree(report),
        "risks": render_report_risks(report),
        "public_badge": public_badge_html(),
        "total_findings_label": f"{total_findings} 项风险" if total_findings else "0 风险",
    }
    for key, value in ctx.items():
        template = template.replace("{{ " + key + " }}", str(value))
    return template.encode("utf-8")


def _read_skill_description(job: dict[str, object], max_len: int = 130) -> str:
    """优先级：AI研判 summary_cn → notes → SKILL.md description。"""
    skill = str(job.get("skill_name", "") or "")
    if skill:
        report = _load_asg_report(skill)
        l3 = report.get("layer_3_agent_eval") if isinstance(report, dict) else None
        audit = l3.get("detailed_audit") if isinstance(l3, dict) else None
        if isinstance(audit, dict):
            summary = str(audit.get("summary_cn", "") or "").strip()
            if summary:
                return summary[:max_len]
    notes = job.get("note") or job.get("notes")
    if isinstance(notes, str) and notes.strip() and notes.strip() != "uploaded for local_api_check":
        # 过滤掉系统自动生成的占位 note
        cleaned = notes.strip()
        if not cleaned.startswith("uploaded "):
            return cleaned[:max_len]
    skill_path = job.get("extracted_skill_path")
    if not isinstance(skill_path, str) or not skill_path:
        return ""
    root = Path(skill_path)
    if not root.exists():
        return ""
    candidates = [root / "SKILL.md"]
    try:
        for child in root.iterdir():
            if child.is_dir() and (child / "SKILL.md").exists():
                candidates.append(child / "SKILL.md")
    except OSError:
        pass
    for md in candidates:
        if not md.exists() or not md.is_file():
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.search(r"^description\s*:\s*(.+?)$", text, re.MULTILINE)
        if m:
            desc = m.group(1).strip().strip("'\"").strip()
            if desc:
                return desc[:max_len]
    return ""


def _composite_score(job: dict[str, object]) -> dict[str, object] | None:
    """读 composite_risk 子结构。没有就返回 None。"""
    skill = str(job.get("skill_name", "") or "")
    if not skill:
        return None
    report = _load_asg_report(skill)
    cr = report.get("composite_risk") if isinstance(report, dict) else None
    if not isinstance(cr, dict):
        return None
    try:
        score = float(cr.get("composite_score", 0))
    except (TypeError, ValueError):
        score = 0.0
    return {
        "score": round(score, 1),
        "verdict": str(cr.get("verdict", "") or "").upper(),
        "sub_scores": cr.get("sub_scores") if isinstance(cr.get("sub_scores"), dict) else {},
        "notes": cr.get("score_notes") if isinstance(cr.get("score_notes"), list) else [],
        "thresholds": cr.get("thresholds") if isinstance(cr.get("thresholds"), dict) else {},
        "weights": cr.get("weights") if isinstance(cr.get("weights"), dict) else {},
    }


def _risk_counts(job: dict[str, object]) -> dict[str, int]:
    """优先用 ASG report.layer_1_static_scan.by_severity (大写键)，
    回退到 job["risk_summary"] (小写键)。"""
    skill = str(job.get("skill_name", "") or "")
    if skill:
        report = _load_asg_report(skill)
        l1 = report.get("layer_1_static_scan") if isinstance(report, dict) else None
        by_sev = l1.get("by_severity") if isinstance(l1, dict) else None
        if isinstance(by_sev, dict):
            out: dict[str, int] = {}
            for lvl_upper, lvl_lower in (("CRITICAL", "critical"), ("HIGH", "high"),
                                          ("MEDIUM", "medium"), ("LOW", "low"),
                                          ("INFORMATIONAL", "informational")):
                try:
                    out[lvl_lower] = int(by_sev.get(lvl_upper, 0))
                except (TypeError, ValueError):
                    out[lvl_lower] = 0
            return out
    summary = job.get("risk_summary") or {}
    if not isinstance(summary, dict):
        return {}
    out: dict[str, int] = {}
    for lvl in ("critical", "high", "medium", "low", "informational"):
        try:
            out[lvl] = int(summary.get(lvl, 0))
        except (TypeError, ValueError):
            out[lvl] = 0
    return out


def dedupe_jobs_by_skill(jobs: list[dict[str, object]]) -> list[dict[str, object]]:
    """同一 skill_name 只保留最新一次扫描（list_jobs 已按时间倒序）。"""
    seen: dict[str, dict[str, object]] = {}
    for job in jobs:
        name = str(job.get("skill_name", "") or job.get("job_id", ""))
        if name not in seen:
            seen[name] = job
    return list(seen.values())


def paginate(items: list, page: int, per_page: int = 12) -> tuple[list, int, int]:
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    return items[start:start + per_page], page, total_pages


def render_pagination(page: int, total_pages: int, base: str = "/results") -> str:
    if total_pages <= 1:
        return ""
    links: list[str] = []
    prev_disabled = ' aria-disabled="true"' if page <= 1 else ""
    next_disabled = ' aria-disabled="true"' if page >= total_pages else ""
    prev_href = f'{base}?page={page-1}' if page > 1 else "#"
    next_href = f'{base}?page={page+1}' if page < total_pages else "#"
    links.append(f'<a class="page-link prev{prev_disabled and " disabled"}" href="{prev_href}">‹ 上一页</a>')
    window = []
    for p in range(1, total_pages + 1):
        if p == 1 or p == total_pages or abs(p - page) <= 2:
            window.append(p)
    last = 0
    for p in window:
        if last and p - last > 1:
            links.append('<span class="page-ellipsis">…</span>')
        active = " active" if p == page else ""
        links.append(f'<a class="page-link{active}" href="{base}?page={p}">{p}</a>')
        last = p
    links.append(f'<a class="page-link next{next_disabled and " disabled"}" href="{next_href}">下一页 ›</a>')
    return '<nav class="pagination">' + "".join(links) + '</nav>'


def render_jobs_cards(jobs: list[dict[str, object]] | None = None) -> str:
    if jobs is None:
        jobs = list(job_store.list_jobs())
    if not jobs:
        return (
            '<div class="empty-state">'
            '<h3>还没有扫描任务</h3>'
            '<p>到 <a href="/">扫描页</a> 上传一个 skill 文件就能开始。</p>'
            '</div>'
        )
    cn_labels = {"critical": "严重", "high": "高危", "medium": "可疑", "low": "低危", "informational": "提示"}
    cards: list[str] = []
    for job in jobs:
        job_id_raw = str(job["job_id"])
        job_id = html.escape(job_id_raw)
        skill_name_raw = str(job.get("skill_name", "") or "")
        report_href = "/report/" + quote(skill_name_raw, safe="")
        skill = html.escape(skill_name_raw or "(no name)")
        created = _format_created(job.get("created_at", "") or "")
        bucket, _ = _verdict_bucket(job)
        verdict_en = _VERDICT_EN[bucket]
        verdict_cn = {"malicious": "危险", "medium": "可疑", "safe": "安全", "unscanned": "未扫描"}[bucket]
        description = _read_skill_description(job)
        if not description:
            if bucket == "unscanned":
                description = "尚未运行静态扫描；点开后可在结果页里启动 Run Static Scan。"
            else:
                description = "这个 skill 暂无描述。点卡片查看完整报告。"
        description_html = html.escape(description)

        counts = _risk_counts(job)
        # 构造风险一句话摘要 + 彩色 tag
        tags: list[str] = []
        for lvl in ("critical", "high", "medium", "low", "informational"):
            n = counts.get(lvl, 0)
            if n > 0:
                tags.append(
                    f'<span class="risk-tag tag-{lvl}">{cn_labels[lvl]} {n}</span>'
                )
        if bucket == "malicious":
            headline = f'<span class="risk-headline danger">●&nbsp;检出 {counts.get("critical",0)+counts.get("high",0)} 个高危威胁</span>'
        elif bucket == "medium":
            headline = f'<span class="risk-headline warn">●&nbsp;{counts.get("medium",0)} 个可疑点需复核</span>'
        elif bucket == "safe":
            headline = '<span class="risk-headline ok">✓&nbsp;未发现高危威胁</span>'
        else:
            headline = '<span class="risk-headline muted">—&nbsp;尚未扫描</span>'
        tags_html = ('<div class="risk-tags">' + "".join(tags) + '</div>') if tags else ""

        score_info = _composite_score(job)
        score_html = ""
        if score_info is not None:
            s = score_info["score"]
            score_html = (
                f'<div class="score-row">'
                f'<span class="score-label">综合风险分</span>'
                f'<span class="score-num score-{bucket}">{s}</span>'
                f'<span class="score-max">/ 100</span>'
                '</div>'
            )
        cards.append(
            f'<a class="job-card risk-{bucket}" href="{report_href}">'
            '<div class="job-header">'
            '<div style="flex:1;min-width:0;">'
            f'<h3 class="job-title">{skill}</h3>'
            f'<div class="job-id">{job_id}</div>'
            '</div>'
            f'<div class="verdict-pill v-{bucket}">'
            '<span class="dot"></span>'
            f'<span class="v-cn">{verdict_cn}</span>'
            '<span class="v-sep">·</span>'
            f'<span class="v-en">{verdict_en}</span>'
            '</div>'
            '</div>'
            + score_html +
            f'<p class="job-desc">{description_html}</p>'
            '<div class="risk-block">'
            + headline + tags_html +
            '</div>'
            '<div class="job-meta">'
            f'<span class="timestamp">📅 {created}</span>'
            '<span class="cta">查看报告 →</span>'
            '</div>'
            '</a>'
        )
    return "\n".join(cards)


def render_risk_cards(job: dict[str, object]) -> str:
    summary = job.get("risk_summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    labels = ["critical", "high", "medium", "low", "informational"]
    cards = []
    for label in labels:
        cards.append(
            f"<div class=\"risk-card risk-{label}\">"
            f"<span>{label.upper()}</span><strong>{int(summary.get(label, 0))}</strong>"
            "</div>"
        )
    return "\n".join(cards)


def render_file_tree(job: dict[str, object], limit: int = 100) -> str:
    root_value = job.get("extracted_skill_path")
    if not root_value:
        return "<p class=\"muted\">No uploaded skill has been extracted yet.</p>"
    root = Path(str(root_value))
    try:
        root_real = root.resolve()
        job_root = job_store.job_dir(str(job["job_id"])).resolve()
        root_real.relative_to(job_root)
    except (OSError, ValueError):
        return "<p class=\"muted\">File tree unavailable: extracted path rejected.</p>"
    if not root_real.exists() or not root_real.is_dir():
        return "<p class=\"muted\">Extracted skill directory is missing.</p>"

    rows: list[str] = []
    truncated = False
    count = 0
    for path in sorted(root_real.rglob("*")):
        if path.is_dir():
            continue
        if path.is_symlink():
            continue
        try:
            relative = path.relative_to(root_real)
        except ValueError:
            continue
        rows.append(f"<li><code>{html.escape(str(relative))}</code></li>")
        count += 1
        if count >= limit:
            truncated = True
            break
    if not rows:
        return "<p class=\"muted\">No files found.</p>"
    suffix = "<li class=\"muted\">truncated after 100 paths</li>" if truncated else ""
    return "<ul class=\"file-tree\">" + "".join(rows) + suffix + "</ul>"


def render_dynamic_gate(job: dict[str, object]) -> str:
    gate = job.get("dynamic_eligibility") or {}
    if not isinstance(gate, dict):
        gate = {}
    blockers = gate.get("blockers") or []
    controls = gate.get("required_controls") or []
    if not isinstance(blockers, list):
        blockers = []
    if not isinstance(controls, list):
        controls = []
    blocker_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in blockers) or "<li>none</li>"
    controls_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in controls) or "<li>generate a dynamic plan first</li>"
    allowed = gate.get("allowed") is True
    confirmed = job.get("dynamic_user_confirmed") is True
    if allowed and not confirmed:
        gate_notice = '<p class="notice">Eligible, waiting for human confirmation.</p>'
    elif allowed and confirmed:
        gate_notice = '<p class="notice">Eligible and confirmed for safe no-network benign inspection.</p>'
    elif blockers:
        gate_notice = '<p class="notice warning">Dynamic execution is blocked by the gate.</p>'
    else:
        gate_notice = '<p class="muted">Generate a dynamic plan to evaluate the gate.</p>'
    high_critical_blocked = any(
        "HIGH / CRITICAL static findings block dynamic execution" in str(item)
        or "critical static findings" in str(item)
        or "high static findings" in str(item)
        for item in blockers
    )
    block_summary = ""
    if high_critical_blocked:
        block_summary = (
            "<div class=\"gate-denied-card\">"
            "<strong>Dynamic Gate: denied</strong>"
            "<p>Reason: HIGH or CRITICAL static findings block dynamic execution.</p>"
            "<ul>"
            "<li>User confirmation cannot override static HIGH / CRITICAL findings.</li>"
            "<li>Run Safe Dynamic Execution remains disabled in the UI and fail closed in the backend.</li>"
            "<li>No container was started.</li>"
            "<li>No uploaded scripts were executed.</li>"
            "</ul>"
            "</div>"
        )
    return (
        "<dl class=\"meta\">"
        f"<dt>Eligibility</dt><dd>{html.escape(str(gate.get('eligibility_status', 'not_evaluated')))}</dd>"
        f"<dt>Reason</dt><dd>{html.escape(str(gate.get('reason', 'dynamic plan not generated')))}</dd>"
        f"<dt>User confirmed</dt><dd>{html.escape(str(job.get('dynamic_user_confirmed', False)).lower())}</dd>"
        f"<dt>Mode</dt><dd>{html.escape(str(job.get('dynamic_scan_status', 'not_started')))}</dd>"
        "</dl>"
        + gate_notice + block_summary +
        "<h3>Blockers</h3><ul class=\"blockers\">" + blocker_html + "</ul>"
        "<h3>Required controls</h3><ul class=\"controls\">" + controls_html + "</ul>"
    )


def render_dynamic_action_controls(job: dict[str, object]) -> str:
    allowed = ((job.get("dynamic_eligibility") or {}).get("allowed") is True)
    confirmed = job.get("dynamic_user_confirmed") is True
    static_done = job.get("static_scan_status") == "completed"
    plan_ready = job.get("dynamic_plan_status") == "ready"
    confirm_disabled = not (allowed and static_done and plan_ready)
    run_disabled = not (allowed and confirmed and static_done and plan_ready)
    confirm_disabled_attr = " disabled" if confirm_disabled else ""
    run_disabled_attr = " disabled" if run_disabled else ""
    if not allowed:
        hint = '<p class="muted">Safe dynamic execution is disabled until the gate is allowed.</p>'
    elif not confirmed:
        hint = '<p class="muted">Eligible, waiting for human confirmation.</p>'
    else:
        hint = '<p class="muted">Confirmed. Safe dynamic execution remains protected by backend gate checks.</p>'
    return (
        "<form method=\"post\" action=\"/job/{{ job_id }}/confirm_dynamic\" class=\"inline-form\">"
        "<input name=\"confirmation_text\" value=\"I confirm safe no-network benign inspection only\" maxlength=\"200\">"
        f"<button type=\"submit\"{confirm_disabled_attr}>Confirm Safe Dynamic Execution</button>"
        "</form>"
        "<form method=\"post\" action=\"/job/{{ job_id }}/run_safe_dynamic\">"
        f"<button type=\"submit\"{run_disabled_attr}>Run Safe Dynamic Execution</button>"
        "</form>"
        + hint
    )


def final_verdict(job: dict[str, object]) -> str:
    summary = job.get("risk_summary") or {}
    if not isinstance(summary, dict):
        return "Not scanned"
    if int(summary.get("critical", 0)) or int(summary.get("high", 0)):
        return "Blocked by HIGH/CRITICAL static risk"
    if job.get("static_scan_status") == "completed":
        return "No HIGH/CRITICAL prototype findings"
    return "Pending static scan"


def load_static_report(job: dict[str, object]) -> dict[str, object]:
    rel_path = (job.get("report_paths") or {}).get("static_scan_report_json")
    if not isinstance(rel_path, str):
        return {}
    try:
        path = (REPO_ROOT / rel_path).resolve()
        path.relative_to(job_store.job_dir(str(job["job_id"])).resolve())
    except (OSError, ValueError):
        return {}
    if not path.exists() or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def render_warnings(job: dict[str, object]) -> str:
    warnings = job.get("static_scanner_warnings") or []
    if not isinstance(warnings, list) or not warnings:
        return ""
    items = "".join(f"<li>{html.escape(str(item))}</li>" for item in warnings)
    return "<ul class=\"warnings\">" + items + "</ul>"


def render_findings_table(static_report: dict[str, object]) -> str:
    findings = static_report.get("findings") or []
    if not isinstance(findings, list) or not findings:
        return "<p class=\"muted\">No static findings.</p>"
    rows = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(finding.get('severity', '')))}</td>"
            f"<td><code>{html.escape(str(finding.get('file', '')))}</code></td>"
            f"<td>{html.escape(str(finding.get('line', '')))}</td>"
            f"<td><code>{html.escape(str(finding.get('rule', finding.get('keyword', ''))))}</code></td>"
            f"<td>{html.escape(str(finding.get('reason', '')))}</td>"
            f"<td>{html.escape(str(finding.get('suppressed', False)).lower())}</td>"
            f"<td>{html.escape(str(finding.get('confidence', '')))}</td>"
            "</tr>"
        )
    return (
        "<div class=\"table-wrap\"><table><thead><tr>"
        "<th>Severity</th><th>File</th><th>Line</th><th>Rule</th>"
        "<th>Reason</th><th>Suppressed</th><th>Confidence</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def scanner_notice(job: dict[str, object]) -> str:
    if job.get("static_scanner_fallback_used"):
        return (
            "<div class=\"notice warning\">Real scanner was unavailable or incompatible; "
            "prototype fallback adapter was used.</div>"
        )
    return ""


def render_job_page(job: dict[str, object], message: str = "") -> bytes:
    dashboard_path = REPO_ROOT / "dashboard" / "index.html"
    context = {
        "title": html.escape(str(job["job_id"])),
        "job_id": html.escape(str(job["job_id"])),
        "skill_name": html.escape(str(job.get("skill_name", ""))),
        "status": html.escape(str(job.get("status", ""))),
        "created_at": html.escape(str(job.get("created_at", ""))),
        "updated_at": html.escape(str(job.get("updated_at", ""))),
        "static_scan_status": html.escape(str(job.get("static_scan_status", ""))),
        "dynamic_scan_status": html.escape(str(job.get("dynamic_scan_status", ""))),
        "static_scanner_mode": html.escape(str(job.get("static_scanner_mode", "not_started"))),
        "static_scanner_fallback_used": html.escape(str(job.get("static_scanner_fallback_used", False)).lower()),
        "static_scanner_warnings": render_warnings(job),
        "risk_summary": html.escape(json.dumps(job.get("risk_summary", {}), sort_keys=True)),
        "risk_cards": render_risk_cards(job),
        "file_tree": render_file_tree(job),
        "dynamic_gate": render_dynamic_gate(job),
        "dynamic_action_controls": render_dynamic_action_controls(job).replace("{{ job_id }}", html.escape(str(job["job_id"]))),
        "message": f"<div class=\"notice\">{html.escape(message)}</div>" if message else "",
        "errors": render_errors(job),
        "dashboard_link": "/dashboard/index.html" if dashboard_path.exists() else "#",
    }
    return render_template("job.html", context)


def render_errors(job: dict[str, object]) -> str:
    errors = job.get("errors") or []
    if not isinstance(errors, list) or not errors:
        return ""
    items = []
    for error in errors:
        if isinstance(error, dict):
            items.append(f"<li>{html.escape(str(error.get('message', error)))}</li>")
        else:
            items.append(f"<li>{html.escape(str(error))}</li>")
    return "<section><h2>Errors</h2><ul class=\"errors\">" + "".join(items) + "</ul></section>"


def render_report(job: dict[str, object]) -> bytes:
    reports = backend_adapter.collect_reports(job)
    static_report = load_static_report(job)
    sections: list[str] = []
    for name, text in reports.items():
        sections.append(f"<h2>{html.escape(name)}</h2><pre>{html.escape(text)}</pre>")
    if not sections:
        sections.append("<p class=\"muted\">No reports have been generated for this job yet.</p>")
    context = {
        "job_id": html.escape(str(job["job_id"])),
        "skill_name": html.escape(str(job.get("skill_name", ""))),
        "static_scan_status": html.escape(str(job.get("static_scan_status", ""))),
        "dynamic_scan_status": html.escape(str(job.get("dynamic_scan_status", ""))),
        "static_scanner_mode": html.escape(str(job.get("static_scanner_mode", static_report.get("scanner_mode", "not_started")))),
        "static_scanner_fallback_used": html.escape(str(job.get("static_scanner_fallback_used", False)).lower()),
        "files_scanned": html.escape(str(static_report.get("files_scanned", static_report.get("file_count", 0)))),
        "findings_count": html.escape(str(len(static_report.get("findings", []) or []))),
        "static_scanner_warnings": render_warnings(job),
        "scanner_notice": scanner_notice(job),
        "findings_table": render_findings_table(static_report),
        "dynamic_execution_summary": render_dynamic_execution_summary(job),
        "dynamic_stdout_preview": render_text_preview(job, "dynamic_stdout"),
        "dynamic_stderr_preview": render_text_preview(job, "dynamic_stderr"),
        "risk_cards": render_risk_cards(job),
        "final_verdict": html.escape(final_verdict(job)),
        "safety_boundary": render_safety_boundary(job),
        "reports": "\n".join(sections),
        "summary": html.escape(json.dumps(backend_adapter.summarize_job(job), indent=2, sort_keys=True)),
    }
    return render_template("report.html", context)


def render_safety_boundary(job: dict[str, object]) -> str:
    boundaries = job.get("safety_boundaries") or {}
    if isinstance(boundaries, dict):
        items = [f"{key}: {str(value).lower()}" for key, value in sorted(boundaries.items())]
    elif isinstance(boundaries, list):
        items = [str(item) for item in boundaries]
    else:
        items = []
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def render_dynamic_execution_summary(job: dict[str, object]) -> str:
    report = job.get("dynamic_execution_report") or {}
    if not isinstance(report, dict) or not report:
        return "<p class=\"muted\">No safe dynamic execution report yet.</p>"
    fields = [
        "execution_attempted",
        "execution_performed",
        "container_started",
        "container_removed",
        "network_mode",
        "sample_mount_mode",
        "output_mount_mode",
        "fake_home_used",
        "fake_codex_home_used",
        "docker_sock_mounted",
        "privileged",
        "network_host",
        "hardening_policy_version",
        "no_new_privileges",
        "cap_drop_all",
        "read_only_rootfs",
        "pids_limit",
        "memory_limit",
        "cpu_limit",
        "timeout_seconds",
        "docker_network_none",
        "docker_network_host_forbidden",
        "docker_sock_forbidden",
        "privileged_forbidden",
        "real_home_forbidden",
        "real_codex_home_forbidden",
        "real_token_forbidden",
        "real_tokens_present",
        "runtime_image",
        "image_allowlisted",
        "image_present_locally",
        "image_pull_prevented",
        "docker_pull_executed",
        "image_inspect_performed",
        "image_inspect_exit_code",
        "host_sensitive_env_detected",
        "host_sensitive_env_names_redacted",
        "sanitized_subprocess_env_used",
        "sanitized_subprocess_env_keys",
        "real_tokens_passed_to_container",
        "uploaded_script_execution_forbidden",
        "install_command_forbidden",
        "docker_pull_forbidden",
        "local_image_preflight_required",
        "sanitized_env_required",
        "runtime_audit_complete",
        "uploaded_scripts_executed",
        "codex_executed",
        "strace_executed",
        "final_verdict",
    ]
    rows = "".join(
        f"<dt>{html.escape(field)}</dt><dd>{html.escape(str(report.get(field, '')))}</dd>"
        for field in fields
    )
    return "<dl class=\"meta\">" + rows + "</dl>"


def render_text_preview(job: dict[str, object], report_key: str) -> str:
    rel_path = (job.get("report_paths") or {}).get(report_key)
    if not isinstance(rel_path, str):
        return "<p class=\"muted\">Not generated.</p>"
    try:
        path = (REPO_ROOT / rel_path).resolve()
        path.relative_to(job_store.job_dir(str(job["job_id"])).resolve())
    except (OSError, ValueError):
        return "<p class=\"muted\">Preview path rejected.</p>"
    if not path.exists() or not path.is_file():
        return "<p class=\"muted\">Not generated.</p>"
    text = path.read_text(encoding="utf-8", errors="replace")[:2000]
    return f"<pre>{html.escape(text)}</pre>"


def ensure_valid_job_id(job_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", job_id):
        raise ValueError("invalid job id")


class PortalHandler(BaseHTTPRequestHandler):
    server_version = "CodexSkillPortal/0.1"

    def send_error(self, code, message=None, explain=None):
        # HTTP reason phrase must be Latin-1. Strip non-ASCII for the status
        # line, but keep the original (Chinese OK) text in the response body.
        ascii_reason = None
        if isinstance(message, str):
            try:
                message.encode("latin-1")
                ascii_reason = message
            except UnicodeEncodeError:
                ascii_reason = message.encode("ascii", "replace").decode("ascii")
                if explain is None:
                    explain = message
        super().send_error(code, ascii_reason, explain)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.send_html(render_template("scan.html", {
                "public_badge": public_badge_html(),
                "dynamic_section": render_dynamic_section_html(),
            }))
            return
        if path == "/results" or path == "/results/":
            query = parse_qs(parsed.query or "")
            try:
                page = int(query.get("page", ["1"])[0])
            except (ValueError, TypeError):
                page = 1
            # 数据源 = analysis_results/asg/（真实扫描结果，一个 skill 一目录天然去重）
            skills = list_asg_skills()
            page_jobs, page, total_pages = paginate(skills, page, per_page=12)
            self.send_html(render_template("results.html", {
                "public_badge": public_badge_html(),
                "jobs_cards": render_jobs_cards(page_jobs),
                "jobs_count": len(skills),
                "pagination": render_pagination(page, total_pages),
                "page_info": f"第 {page} / {total_pages} 页 · 共 {len(skills)} 个已扫描 skill",
            }))
            return
        if path.startswith("/static/"):
            self.send_static(WEB_ROOT / path.lstrip("/"))
            return
        # SAFESKILL 报告页：直接从 analysis_results/asg/<skill> 渲染
        if path.startswith("/report/"):
            skill_name = unquote(path[len("/report/"):]).strip("/")
            if not skill_name or not SKILL_NAME_RE.fullmatch(skill_name):
                self.send_error(400, "invalid skill name")
                return
            report = _load_asg_report(skill_name)
            if not report:
                self.send_error(404, "no scan report for this skill")
                return
            job_like = {
                "skill_name": skill_name,
                "job_id": skill_name,
                "created_at": str(report.get("generated_at_utc", "") or ""),
            }
            self.send_html(render_safeskill_report(job_like))
            return
        if path == "/dashboard/index.html":
            self.send_static(REPO_ROOT / "dashboard" / "index.html")
            return
        if path == "/dashboard/style.css":
            self.send_static(REPO_ROOT / "dashboard" / "style.css")
            return
        # ===== ASG (AgentSkillGuard) routes =====
        if path == "/asg" or path == "/asg/" or path == "/asg/dashboard":
            asg_html = REPO_ROOT / "asg" / "dashboard.html"
            if not asg_html.exists():
                self._asg_render_empty()
                return
            self.send_static(asg_html)
            return
        if path == "/asg/json":
            batch = REPO_ROOT / "analysis_results" / "asg" / "batch_summary.json"
            if batch.exists():
                self.send_static(batch)
            else:
                self.send_error(404, "ASG batch_summary.json not generated yet; click Rebuild")
            return
        # Serve per-skill detail HTML pages (e.g. /skills/credential_exfil_skill.html).
        # Files live in asg/skills/<name>.html, written by dashboard_builder.
        if path.startswith("/skills/") and path.endswith(".html"):
            fname = path[len("/skills/"):]
            # Block path traversal — only allow plain filenames
            if "/" in fname or ".." in fname:
                self.send_error(400, "invalid skill name")
                return
            detail = REPO_ROOT / "asg" / "skills" / fname
            if detail.exists():
                self.send_static(detail)
            else:
                # Trigger a rebuild of just this one skill so users can recover from 404
                skill_name = fname[:-len(".html")]
                try:
                    import subprocess
                    subprocess.run(
                        [sys.executable, "-m", "asg.asg_cli", "build-html",
                         "--skill", skill_name],
                        cwd=str(REPO_ROOT), check=True, capture_output=True,
                        text=True, timeout=30,
                    )
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass
                if detail.exists():
                    self.send_static(detail)
                else:
                    self.send_error(
                        404,
                        f"详情页 {fname} 不存在；可能该 skill 报告还没生成。"
                        "回到 /asg 看主面板，或运行 'python -m asg.asg_cli build-html' 重建全部详情页。",
                    )
            return
        if path.startswith("/job/"):
            self.handle_job_get(path)
            return
        self.send_error(404, "not found")

    # 公开模式下被禁用的 POST 端点（动态执行 + 删除）。模式一上传扫描不在此列。
    _PUBLIC_BLOCKED_EXACT = {
        "/asg/vm_ingest",
        "/asg/vm_ssh_run",
        "/asg/vm_paper_run",
    }
    _PUBLIC_BLOCKED_SUFFIX = (
        "/run_safe_dynamic",
        "/run_dynamic_plan",
        "/confirm_dynamic",
        "/delete",
    )

    def _is_blocked_in_public_mode(self, path: str) -> bool:
        if not PUBLIC_MODE:
            return False
        if path in self._PUBLIC_BLOCKED_EXACT:
            return True
        if path.startswith("/job/") and any(path.endswith(s) for s in self._PUBLIC_BLOCKED_SUFFIX):
            return True
        return False

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if self._is_blocked_in_public_mode(path):
            self.send_error(
                403,
                "Public mode: dynamic execution and destructive actions are disabled. "
                "See the docs panel on the scan page for how to enable mode 2/3 locally.",
            )
            return
        if path == "/upload":
            self.handle_upload()
            return
        if path.startswith("/job/") and path.endswith("/run_static"):
            job_id = path.split("/")[2]
            ensure_valid_job_id(job_id)
            job = job_store.load_job(job_id)
            job = backend_adapter.run_static_scan(job)
            self.send_html(render_job_page(job, "Static scan finished."))
            return
        if path.startswith("/job/") and path.endswith("/run_dynamic_plan"):
            job_id = path.split("/")[2]
            ensure_valid_job_id(job_id)
            job = job_store.load_job(job_id)
            job = backend_adapter.run_dynamic_scan_plan(job)
            self.send_html(render_job_page(job, "Dynamic plan gate evaluated."))
            return
        if path.startswith("/job/") and path.endswith("/confirm_dynamic"):
            job_id = path.split("/")[2]
            ensure_valid_job_id(job_id)
            job = job_store.load_job(job_id)
            form = self.read_urlencoded_form()
            job = backend_adapter.confirm_dynamic_execution(job, form.get("confirmation_text", ""))
            self.send_html(render_job_page(job, "Safe dynamic execution confirmation recorded."))
            return
        if path.startswith("/job/") and path.endswith("/run_safe_dynamic"):
            job_id = path.split("/")[2]
            ensure_valid_job_id(job_id)
            job = job_store.load_job(job_id)
            job = backend_adapter.run_safe_dynamic_scan(job)
            self.send_html(render_job_page(job, "Safe dynamic execution gate evaluated."))
            return
        if path.startswith("/job/") and path.endswith("/delete"):
            job_id = path.split("/")[2]
            ensure_valid_job_id(job_id)
            self.delete_job(job_id)
            return
        # ===== ASG routes =====
        if path == "/asg/rebuild":
            self._asg_rebuild()
            return
        if path == "/asg/vm_ingest":
            form = self.read_urlencoded_form()
            self._asg_vm_ingest(
                form.get("skill_path", ""),
                form.get("evidence_dir", ""),
            )
            return
        if path == "/asg/vm_ssh_run":
            self._asg_vm_ssh_run()
            return
        if path == "/asg/vm_paper_run":
            self._asg_vm_paper_run()
            return
        if path == "/asg/local_api_check":
            self._asg_local_api_check()
            return
        if path == "/asg/upload_scan":
            self._asg_upload_scan()
            return
        if path.startswith("/job/") and path.endswith("/asg_scan"):
            job_id = path.split("/")[2]
            ensure_valid_job_id(job_id)
            self._asg_scan_job(job_id)
            return
        self.send_error(404, "not found")

    # ============================================================
    # ASG helpers (delegate to asg.asg_cli)
    # ============================================================
    def _asg_render_empty(self) -> None:
        body = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>ASG dashboard not built</title>"
            "<style>body{font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:32px;}"
            "form{margin-top:16px;}button{background:#38bdf8;color:#0f172a;border:none;"
            "padding:12px 24px;border-radius:6px;cursor:pointer;font-size:16px;font-weight:600;}"
            "a{color:#38bdf8;}</style></head><body>"
            "<h1>ASG Dashboard not yet built</h1>"
            "<p>Click the button below to run the full ASG scan-all-samples pipeline."
            " This generates static + chain + risk scoring for all 7 synthetic samples"
            " in <code>asg/samples/</code>.</p>"
            "<form method='post' action='/asg/rebuild'><button type='submit'>"
            "&#x1f6e1;  Build ASG dashboard now</button></form>"
            "<p style='margin-top:24px;'><a href='/'>&larr; Back to Codex portal</a></p>"
            "</body></html>"
        )
        self.send_html(body.encode("utf-8"))

    def _asg_rebuild(self) -> None:
        import subprocess
        try:
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "scan-all-samples", "--enable-honeypot"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=120,
            )
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "build-html"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=60,
            )
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "build-dashboard"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=60,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"ASG rebuild failed: {exc.stderr or exc}")
            return
        except subprocess.TimeoutExpired:
            self.send_error(504, "ASG rebuild timed out")
            return
        self.redirect("/results")

    def _asg_vm_ingest(self, skill_path: str, evidence_dir: str) -> None:
        import subprocess
        if not skill_path or not evidence_dir:
            self.send_error(400, "skill_path and evidence_dir required")
            return
        try:
            result = subprocess.run(
                [sys.executable, "-m", "asg.asg_cli",
                 "ingest-vm-evidence", skill_path, evidence_dir, "--enable-honeypot"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=60,
            )
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "build-html",
                 "--skill", Path(skill_path).name],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=30,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"VM ingest failed: {exc.stderr or exc}")
            return
        self.redirect("/results")

    def _asg_vm_ssh_run(self, skill_path: str = "") -> None:
        """模式三：上传 zip → VM 容器里跑 Claude CLI 使用此 skill。"""
        import subprocess
        if skill_path:
            target_path = skill_path
            target_name = Path(skill_path).name
        else:
            res = self._recv_skill_zip_to_path(purpose="vm_ssh_run")
            if not res:
                return
            target_path, target_name = str(res[0]), res[1]
        cfg_path = REPO_ROOT / "asg" / "vm_config.json"
        if not cfg_path.exists():
            self.send_error(400,
                "asg/vm_config.json 不存在，需要 VM host/username/password。")
            return
        try:
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli",
                 "vm-ssh-run", target_path, "--enable-honeypot"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=600,
            )
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "build-html",
                 "--skill", target_name],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=30,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"模式三（Claude in Docker）失败: {exc.stderr or exc}")
            return
        self.redirect("/results")

    def _asg_vm_paper_run(self, skill_path: str = "") -> None:
        """模式二-A：上传 zip → VM Docker 直接 python/bash 跑脚本（不调 API）。"""
        import subprocess
        if skill_path:
            target_path = skill_path
            target_name = Path(skill_path).name
        else:
            res = self._recv_skill_zip_to_path(purpose="vm_paper_run")
            if not res:
                return
            target_path, target_name = str(res[0]), res[1]
        cfg_path = REPO_ROOT / "asg" / "vm_config.json"
        if not cfg_path.exists():
            self.send_error(400,
                "asg/vm_config.json 不存在，需要 VM host/username/password。")
            return
        try:
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli",
                 "vm-paper-run", target_path, "--enable-honeypot",
                 "--timeout-seconds", "30"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=300,
            )
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "build-html",
                 "--skill", target_name],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=30,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"模式二（VM Docker 执行）失败: {exc.stderr or exc}")
            return
        except subprocess.TimeoutExpired:
            self.send_error(504, "模式二超时")
            return
        self.redirect("/results")

    def _recv_skill_zip_to_path(self, form: "cgi.FieldStorage | None" = None,
                                 field_name: str = "archive",
                                 purpose: str = "upload"):
        """接收一个 multipart 文件上传（zip / tar.gz / 单文件），解压到 job dir，
        返回 (skill_root_path: Path, skill_name: str) 或 None（已 send_error）。
        如果传 form 进来就复用，否则现读 multipart stream。"""
        import time
        if form is None:
            ct = self.headers.get("Content-Type", "")
            if not ct.startswith("multipart/form-data"):
                self.send_error(400, "需要 multipart 表单上传")
                return None
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers,
                environ={"REQUEST_METHOD": "POST"},
            )
        upload = form[field_name] if field_name in form else None
        if upload is None or not getattr(upload, "filename", ""):
            self.send_error(400, f"缺少上传字段: {field_name}")
            return None
        archive_stem = Path(sanitize_filename(upload.filename)).stem or "uploaded"
        ts = time.strftime("%Y%m%d_%H%M%S")
        skill_name = f"{archive_stem}_{ts}"
        job = job_store.create_job(skill_name, f"uploaded for {purpose}")
        try:
            filename = sanitize_filename(upload.filename)
            lower = filename.lower()
            is_archive = (lower.endswith(".zip") or lower.endswith(".tar.gz")
                          or lower.endswith(".tgz"))
            job_dir = job_store.job_dir(job["job_id"])
            archive_dir = job_dir / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / filename
            with archive_path.open("wb") as out:
                shutil.copyfileobj(upload.file, out, length=1024 * 1024)
            extracted = job_dir / "uploaded_skill"
            if is_archive:
                result = safe_extract_archive(archive_path, extracted)
                raw_path = Path(result.extracted_path)
            else:
                extracted.mkdir(parents=True, exist_ok=True)
                shutil.copy2(archive_path, extracted / filename)
                raw_path = extracted
        except SafeExtractError as exc:
            self.send_error(400, f"上传被拒（安全解压失败）: {exc}")
            return None
        skill_root = None
        if (raw_path / "SKILL.md").exists():
            skill_root = raw_path
        else:
            for child in (raw_path.iterdir() if raw_path.is_dir() else []):
                if child.is_dir() and (child / "SKILL.md").exists():
                    skill_root = child
                    break
        if skill_root is None:
            if is_archive:
                self.send_error(400, "上传的压缩包里没找到 SKILL.md")
                return None
            skill_root = raw_path
            stub = (f"---\nname: {skill_name}\n"
                    f"description: Auto-generated SKILL.md stub for single-file "
                    f"upload ({filename}).\n---\n\n"
                    f"# {skill_name}\n\nUploaded file: `{filename}`.\n")
            (skill_root / "SKILL.md").write_text(stub, encoding="utf-8")
        unique_root = skill_root.parent / skill_name
        if unique_root.exists():
            unique_root = skill_root.parent / f"{skill_name}_{job['job_id'][:8]}"
        skill_root.rename(unique_root)
        return (unique_root, skill_name)

    def _load_anthropic_env(self) -> dict[str, str]:
        """读 vm_config.json 把 Claude API key/base 注入 subprocess env。"""
        cfg_path = REPO_ROOT / "asg" / "vm_config.json"
        api_env: dict[str, str] = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                key = cfg.get("remote_anthropic_api_key", "")
                if key and "REPLACE" not in key:
                    api_env["ANTHROPIC_API_KEY"] = key
                    base = cfg.get("remote_anthropic_base_url")
                    if base:
                        api_env["ANTHROPIC_BASE_URL"] = base
            except json.JSONDecodeError:
                pass
        return api_env

    def _asg_local_api_check(self, skill_path: str = "") -> None:
        """模式一-B：上传 Skill zip → 解压 → 静态 + Claude API 研判（不执行）。
        skill_path 参数保留兼容（如果非空就直接用本地路径，否则走 multipart 上传）。
        """
        import subprocess
        if skill_path:
            scan_target = skill_path
        else:
            res = self._recv_skill_zip_to_path(purpose="local_api_check")
            if not res:
                return
            scan_target = str(res[0])
        api_env = self._load_anthropic_env()
        if not api_env:
            self.send_error(400,
                "asg/vm_config.json 里 remote_anthropic_api_key 缺失或仍是占位符。"
                "请先填入真实 kuaipao.ai key。")
            return
        env = {**os.environ, **api_env}
        try:
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "scan",
                 scan_target, "--enable-claude", "--enable-honeypot"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
                timeout=180, env=env,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"模式一扫描失败: {exc.stderr or exc}")
            return
        except subprocess.TimeoutExpired:
            self.send_error(504, "模式一扫描超时 (>180s)")
            return
        self.redirect("/results")

    def _asg_upload_scan(self) -> None:
        """Upload .zip → safe extract → static + chain + honeypot + Claude API check.

        The skill is NEVER executed by this path. It is only:
          1. Statically scanned (regex rules + attack chain detection)
          2. Sent as SKILL.md text to Claude via kuaipao.ai for judgment

        Anyone on the network can safely upload here. Dynamic execution (Mode
        B / C) stays operator-only and is not exposed to upload flow.
        """
        import subprocess
        import time
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error(400, "multipart form required")
            return
        form = cgi.FieldStorage(
            fp=self.rfile, headers=self.headers,
            environ={"REQUEST_METHOD": "POST"},
        )
        upload = form["archive"] if "archive" in form else None
        if upload is None or not getattr(upload, "filename", ""):
            self.send_error(400, "archive upload required")
            return
        archive_stem = Path(sanitize_filename(upload.filename)).stem or "uploaded"
        ts = time.strftime("%Y%m%d_%H%M%S")
        skill_name = f"{archive_stem}_{ts}"
        job = job_store.create_job(skill_name, "uploaded via ASG upload-scan (no exec)")
        try:
            filename = sanitize_filename(upload.filename)
            lower = filename.lower()
            is_archive = (lower.endswith(".zip") or lower.endswith(".tar.gz")
                          or lower.endswith(".tgz"))
            job_dir = job_store.job_dir(job["job_id"])
            archive_dir = job_dir / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / filename
            with archive_path.open("wb") as output:
                shutil.copyfileobj(upload.file, output, length=1024 * 1024)
            extracted_path = job_dir / "uploaded_skill"
            if is_archive:
                result = safe_extract_archive(archive_path, extracted_path)
                raw_path = Path(result.extracted_path)
            else:
                # Single-file upload: wrap into a skill dir as-is.
                extracted_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(archive_path, extracted_path / filename)
                raw_path = extracted_path
        except SafeExtractError as exc:
            self.send_error(400, f"upload rejected by safe extraction: {exc}")
            return
        # Find directory containing SKILL.md (could be raw_path or a child).
        # For single-file uploads with no SKILL.md, synthesize a minimal stub
        # so claude_runner has something to send.
        skill_root = None
        if (raw_path / "SKILL.md").exists():
            skill_root = raw_path
        else:
            for child in raw_path.iterdir() if raw_path.is_dir() else []:
                if child.is_dir() and (child / "SKILL.md").exists():
                    skill_root = child
                    break
        if skill_root is None:
            if is_archive:
                self.send_error(
                    400,
                    "uploaded archive has no SKILL.md (looked in extracted root "
                    "and first-level subdirs)",
                )
                return
            # Single-file upload without SKILL.md → synthesize one
            skill_root = raw_path
            stub = (
                f"---\nname: {skill_name}\n"
                f"description: Auto-generated SKILL.md stub for single-file upload "
                f"({filename}). The uploaded file is shown below for static + agent "
                f"review.\n---\n\n"
                f"# {skill_name}\n\n"
                f"Uploaded file: `{filename}` (no original SKILL.md provided).\n"
            )
            (skill_root / "SKILL.md").write_text(stub, encoding="utf-8")
        # Rename to unique name so reports don't collide between uploads
        unique_root = skill_root.parent / skill_name
        if unique_root.exists():
            unique_root = skill_root.parent / f"{skill_name}_{job['job_id'][:8]}"
        skill_root.rename(unique_root)
        # Load API creds from vm_config.json (optional - if absent, Claude is skipped)
        cfg_path = REPO_ROOT / "asg" / "vm_config.json"
        api_env: dict[str, str] = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                key = cfg.get("remote_anthropic_api_key", "")
                if key and "REPLACE" not in key:
                    api_env["ANTHROPIC_API_KEY"] = key
                    base = cfg.get("remote_anthropic_base_url")
                    if base:
                        api_env["ANTHROPIC_BASE_URL"] = base
            except json.JSONDecodeError:
                pass
        cmd = [sys.executable, "-m", "asg.asg_cli", "scan",
               str(unique_root), "--enable-honeypot"]
        if api_env:
            cmd.append("--enable-claude")
        env = {**os.environ, **api_env}
        try:
            subprocess.run(
                cmd, cwd=str(REPO_ROOT), check=True,
                capture_output=True, text=True, timeout=180, env=env,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"ASG scan failed: {exc.stderr or exc}")
            return
        except subprocess.TimeoutExpired:
            self.send_error(504, "ASG scan timed out (>180s)")
            return
        self.redirect("/results")

    def _asg_scan_job(self, job_id: str) -> None:
        import subprocess
        try:
            job = job_store.load_job(job_id)
        except FileNotFoundError:
            self.send_error(404, "job not found")
            return
        skill_root = job.get("extracted_skill_path")
        if not skill_root:
            self.send_error(400, "job has no extracted skill")
            return
        try:
            result = subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "scan", skill_root, "--enable-honeypot"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=120,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"ASG scan failed: {exc.stderr or exc}")
            return
        # Stash a minimal summary into the job for display
        try:
            asg_summary = json.loads(result.stdout)
        except json.JSONDecodeError:
            asg_summary = {"raw_stdout": result.stdout[:1000]}
        job["asg_summary"] = asg_summary
        job_store.save_job(job)
        self.redirect(f"/job/{job_id}")

    def handle_job_get(self, path: str) -> None:
        parts = path.strip("/").split("/")
        if len(parts) < 2:
            self.send_error(404, "not found")
            return
        job_id = parts[1]
        try:
            ensure_valid_job_id(job_id)
            job = job_store.load_job(job_id)
        except (FileNotFoundError, ValueError):
            self.send_error(404, "job not found")
            return
        if len(parts) == 2:
            self.send_html(render_safeskill_report(job))
        elif len(parts) == 3 and parts[2] == "report":
            self.send_html(render_safeskill_report(job))
        elif len(parts) == 3 and parts[2] == "legacy":
            self.send_html(render_job_page(job))
        elif len(parts) == 3 and parts[2] == "download_job_json":
            self.send_json(job)
        elif len(parts) == 4 and parts[2] == "download":
            self.send_report_download(job, parts[3])
        else:
            self.send_error(404, "not found")

    def handle_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error(400, "multipart form required")
            return
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        skill_name = form.getfirst("skill_name", "uploaded_skill")
        note = form.getfirst("note", "")
        upload = form["archive"] if "archive" in form else None
        if upload is None or not getattr(upload, "filename", ""):
            self.send_error(400, "archive upload required")
            return

        job = job_store.create_job(skill_name, note)
        try:
            filename = sanitize_filename(upload.filename)
            if not (filename.lower().endswith(".zip") or filename.lower().endswith(".tar.gz") or filename.lower().endswith(".tgz")):
                raise SafeExtractError("unsupported archive extension")
            job_dir = job_store.job_dir(job["job_id"])
            archive_dir = job_dir / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / filename
            with archive_path.open("wb") as output:
                shutil.copyfileobj(upload.file, output, length=1024 * 1024)
            extracted_path = job_dir / "uploaded_skill"
            result = safe_extract_archive(archive_path, extracted_path)
            job["uploaded_archive"] = str(archive_path.relative_to(REPO_ROOT))
            job["extracted_skill_path"] = result.extracted_path
            job["status"] = "extracted"
            job_store.save_job(job)
            self.redirect(f"/job/{job['job_id']}")
        except SafeExtractError as exc:
            job["uploaded_archive"] = str(archive_path.relative_to(REPO_ROOT)) if "archive_path" in locals() else None
            job["status"] = "failed"
            job.setdefault("errors", []).append({"message": str(exc)})
            job_store.save_job(job)
            self.send_html(render_job_page(job, "Upload rejected by safe extraction gate."))

    def read_urlencoded_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
        parsed = parse_qs(body)
        return {key: values[0] if values else "" for key, values in parsed.items()}

    def send_report_download(self, job: dict[str, object], download_name: str) -> None:
        if download_name not in DOWNLOAD_REPORT_KEYS:
            self.send_error(404, "download not found")
            return
        report_key, content_type, filename = DOWNLOAD_REPORT_KEYS[download_name]
        rel_path = (job.get("report_paths") or {}).get(report_key)
        if not isinstance(rel_path, str):
            self.send_error(404, "report not generated")
            return
        try:
            job_root = job_store.job_dir(str(job["job_id"])).resolve()
            path = (REPO_ROOT / rel_path).resolve()
            path.relative_to(job_root)
        except (OSError, ValueError):
            self.send_error(403, "report path rejected")
            return
        if not path.exists() or not path.is_file():
            self.send_error(404, "report missing")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f"attachment; filename={filename}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def delete_job(self, job_id: str) -> None:
        try:
            target = job_store.job_dir(job_id).resolve()
            jobs_root = job_store.JOBS_ROOT.resolve()
            target.relative_to(jobs_root)
        except ValueError:
            self.send_error(403, "job path rejected")
            return
        if target.exists() and target.is_dir():
            shutil.rmtree(target)
        self.redirect("/results")

    def send_html(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data: object) -> None:
        body = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=job.json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            allowed_roots = [
                WEB_ROOT.resolve(),
                (REPO_ROOT / "dashboard").resolve(),
                (REPO_ROOT / "asg").resolve(),
                (REPO_ROOT / "analysis_results" / "asg").resolve(),
            ]
            if not any(resolved == root or root in resolved.parents for root in allowed_roots):
                self.send_error(403, "static path rejected")
                return
            if not resolved.exists() or not resolved.is_file():
                self.send_error(404, "not found")
                return
            body = resolved.read_bytes()
        except OSError:
            self.send_error(404, "not found")
            return
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def main() -> None:
    query = parse_qs(urlparse("").query)
    del query
    server = ThreadingHTTPServer((HOST, PORT), PortalHandler)
    print(f"Codex Runtime Security Prototype portal listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
