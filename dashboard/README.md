# SkillSentinel Security Review Dashboard

This directory contains the SkillSentinel level3.1 security review dashboard.
It renders dashboard data from `artifacts/demo-risky-skill/dashboard_data.json`
and supports triage-oriented review: decision guidance, key risk summary,
filtered evidence timeline, filtered rule findings, static/dynamic comparison,
recommended actions, and raw JSON review.

Files:

- `index.html`
- `dashboard.css`
- `dashboard.js`
- `style.css` for legacy compatibility

Generate demo data and preview locally:

```bash
python3 tools/generate_dashboard_data.py examples/demo-risky-skill
python3 -m http.server 8000
```

Then open `http://localhost:8000/dashboard/`.

The default data is demo data for visualization only. Do not present it as a
verified VM Mode C execution result.
