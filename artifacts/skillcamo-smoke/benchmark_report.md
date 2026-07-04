# Safe SkillCamo Benchmark Report

Evaluated: 2026-06-25T13:17:07.769531+00:00

This benchmark is inert: all attack strings are synthetic canaries, use a reserved `.invalid` domain, and are never executed.

## Headline metrics

- Attack recall: 1.000 (32/32)
- Attack success rate against scanner: 0.000
- Independent benign FPR: 0.000
- Aggregate benign FPR: 0.000
- Operational errors: 0

## Per-family results

| Family | Total | Detected | Detection rate | Missed |
|---|---:|---:|---:|---:|
| clean-base | 8 | 0 | 0.000 | 8 |
| skillject | 8 | 8 | 1.000 | 0 |
| skillcamo-full | 8 | 8 | 1.000 | 0 |
| skillcamo-cloze | 8 | 8 | 1.000 | 0 |
| skillcamo-split | 8 | 8 | 1.000 | 0 |
| benign-evaluation | 16 | 0 | 0.000 | 16 |
