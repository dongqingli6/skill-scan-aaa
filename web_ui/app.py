from __future__ import annotations

import cgi
import html
import json
import mimetypes
import re
import shutil
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_adapter
import job_store
from safe_extract import SafeExtractError, safe_extract_archive


HOST = "127.0.0.1"
PORT = 8765
REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent
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

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.send_html(render_template("index.html", {"jobs_table": render_jobs_table()}))
            return
        if path.startswith("/static/"):
            self.send_static(WEB_ROOT / path.lstrip("/"))
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
        if path.startswith("/job/"):
            self.handle_job_get(path)
            return
        self.send_error(404, "not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
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
            form = self.read_urlencoded_form()
            self._asg_vm_ssh_run(form.get("skill_path", ""))
            return
        if path == "/asg/vm_paper_run":
            form = self.read_urlencoded_form()
            self._asg_vm_paper_run(form.get("skill_path", ""))
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
            " This generates static + chain + risk scoring for all 6 synthetic samples"
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
        self.redirect("/asg")

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
                [sys.executable, "-m", "asg.asg_cli", "build-html"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=30,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"VM ingest failed: {exc.stderr or exc}")
            return
        self.redirect("/asg")

    def _asg_vm_ssh_run(self, skill_path: str) -> None:
        import subprocess
        if not skill_path:
            self.send_error(400, "skill_path required")
            return
        cfg_path = REPO_ROOT / "asg" / "vm_config.json"
        if not cfg_path.exists():
            self.send_error(
                400,
                "asg/vm_config.json not found. Create it with host/username/password before using vm-ssh-run.",
            )
            return
        try:
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli",
                 "vm-ssh-run", skill_path, "--enable-honeypot"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=600,
            )
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "build-html"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=30,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"VM SSH run failed: {exc.stderr or exc}")
            return
        self.redirect("/asg")

    def _asg_vm_paper_run(self, skill_path: str) -> None:
        import subprocess
        if not skill_path:
            self.send_error(400, "skill_path required")
            return
        cfg_path = REPO_ROOT / "asg" / "vm_config.json"
        if not cfg_path.exists():
            self.send_error(
                400,
                "asg/vm_config.json not found. Need VM host/username/password.",
            )
            return
        try:
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli",
                 "vm-paper-run", skill_path, "--enable-honeypot",
                 "--timeout-seconds", "30"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=300,
            )
            subprocess.run(
                [sys.executable, "-m", "asg.asg_cli", "build-html"],
                cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, timeout=30,
            )
        except subprocess.CalledProcessError as exc:
            self.send_error(500, f"Paper-mode VM run failed: {exc.stderr or exc}")
            return
        except subprocess.TimeoutExpired:
            self.send_error(504, "Paper-mode VM run timed out")
            return
        self.redirect("/asg")

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
            self.send_html(render_job_page(job))
        elif len(parts) == 3 and parts[2] == "report":
            self.send_html(render_report(job))
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
        self.redirect("/")

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
