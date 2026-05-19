# Big Stage 26 Document-Behavior Divergence Analysis Layer

- Mode: static existing evidence only
- Skill execution: false
- Docker executed: false
- Codex / Claude Code executed: false
- Strace executed: false
- Real API called: false
- Network enabled: false

## Summary

- Total samples: 5
- Divergence counts: `{"critical": 0, "high": 1, "low": 0, "medium": 0, "none": 4}`
- Decision counts: `{"blocked": 1, "consistent": 4, "manual_review": 0, "note": 0}`

## Per-Skill Comparison

### implementation-guide.zip

Claims:
- purpose: Generate comprehensive implementation guides for coding tasks instead of writing code directly. Use when the user requests detailed implementation documentation, step-by-step development guides, or when they want to implement features thems
- network: declared
- filesystem: declared
- credentials: declared
- install/setup: declared
- execution: declared
- docker: not_declared

Evidence:
- evidence flags: `{"credential": true, "docker": false, "execution": false, "filesystem": false, "install": false, "network": true, "prompt_injection": false}`
- deterministic highest: high
- agent highest: high

Divergence:
- HIGH `under_disclosed_risky_behavior`: SKILL.md presents writing/advice behavior while evidence shows possible command, file, or network behavior.

Final recommendation: HIGH / CRITICAL divergence: blocked pending human security review.

### logging-best-practices.zip

Claims:
- purpose: Use before implementing logs in a medium to large scale production system.
- network: declared
- filesystem: declared
- credentials: declared
- install/setup: not_declared
- execution: declared
- docker: not_declared

Evidence:
- evidence flags: `{"credential": false, "docker": false, "execution": false, "filesystem": false, "install": false, "network": true, "prompt_injection": false}`
- deterministic highest: medium
- agent highest: medium

Divergence:
- none

Final recommendation: No document-behavior divergence found in existing evidence; existing risk gates still apply.

### val-town-cli.zip

Claims:
- purpose: Manage Val Town projects using the vt CLI. Use when working with Vals (Val Town serverless functions), syncing code to Val Town, creating HTTP endpoints, streaming logs, or managing Val Town branches. Triggers on tasks involving Val Town de
- network: declared
- filesystem: declared
- credentials: not_declared
- install/setup: not_declared
- execution: declared
- docker: not_declared

Evidence:
- evidence flags: `{"credential": false, "docker": false, "execution": false, "filesystem": false, "install": false, "network": true, "prompt_injection": false}`
- deterministic highest: medium
- agent highest: medium

Divergence:
- none

Final recommendation: No document-behavior divergence found in existing evidence; existing risk gates still apply.

### ideation.zip

Claims:
- purpose: Guides structured ideation through Socratic questioning to explore problems, opportunities, and solutions. Use when brainstorming features, exploring use cases, or thinking through new ideas.
- network: not_declared
- filesystem: not_declared
- credentials: not_declared
- install/setup: not_declared
- execution: declared
- docker: not_declared

Evidence:
- evidence flags: `{"credential": false, "docker": false, "execution": false, "filesystem": false, "install": false, "network": false, "prompt_injection": false}`
- deterministic highest: none
- agent highest: none

Divergence:
- none

Final recommendation: No document-behavior divergence found in existing evidence; existing risk gates still apply.

### react-effect-patterns.zip

Claims:
- purpose: Guidelines for proper React useEffect usage and avoiding unnecessary Effects. Use when writing, reviewing, or refactoring React components that use useEffect, useState, or handle side effects. Triggers on tasks involving React Effects, deri
- network: denied
- filesystem: declared
- credentials: declared
- install/setup: not_declared
- execution: declared
- docker: not_declared

Evidence:
- evidence flags: `{"credential": false, "docker": false, "execution": false, "filesystem": false, "install": false, "network": false, "prompt_injection": false}`
- deterministic highest: none
- agent highest: none

Divergence:
- none

Final recommendation: No document-behavior divergence found in existing evidence; existing risk gates still apply.
