# Big Stage 27 Scaled Validation and Final Reporting Layer

Stage 27 builds a local synthetic corpus, combines it with the five real skill results already produced by earlier stages, computes validation metrics, and writes final reporting artifacts.

Safety boundaries:

- Static-only evaluation.
- No skill execution.
- No container execution.
- No Codex or Claude Code execution.
- No syscall tracing.
- No real API calls.
- No network access.
- Synthetic attack-like fixtures use fake placeholders only.

Outputs are written to `analysis_results/scaled_validation/`:

- `summary.json`
- `report.md`
- `risk_table.csv`
- `metrics.json`
- `confusion_matrix.json`
- `manual_review_queue.md`
- `final_research_report.md`
- `dashboard_data.json`
