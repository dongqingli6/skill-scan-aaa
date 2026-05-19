"""Compatibility wrapper for the Codex strace parser.

The active implementation lives in `strace_parser.py` and supports
`strace.log` / `strace.log.*` multi-file input.
"""

from __future__ import annotations

from .strace_parser import *  # noqa: F403
