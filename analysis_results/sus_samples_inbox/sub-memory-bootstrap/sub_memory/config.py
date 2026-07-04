from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {value!r}.") from exc

    if parsed < 1:
        raise RuntimeError(f"{name} must be >= 1, got {parsed}.")

    return parsed


@dataclass(slots=True)
class Settings:
    base_dir: Path
    db_path: Path
    openai_api_key: str | None
    openai_model: str
    embedding_model_name: str
    sqlite_vec_path: str | None
    recall_depth: int
    recall_limit: int
    compact_after_turns: int
    compact_keep_recent_turns: int
    compact_summary_char_limit: int
    metrics_log_path: Path
    metrics_retention_days: int
    exit_commands: tuple[str, ...] = ("exit", "quit")

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "Settings":
        resolved_base_dir = (base_dir or Path.cwd()).resolve()
        _load_dotenv(resolved_base_dir / ".env")

        db_name = os.getenv("MEMORY_DB_PATH", "memory.db")

        return cls(
            base_dir=resolved_base_dir,
            db_path=(resolved_base_dir / db_name).resolve(),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            embedding_model_name=os.getenv(
                "EMBEDDING_MODEL_NAME",
                "all-MiniLM-L6-v2",
            ),
            sqlite_vec_path=os.getenv("SQLITE_VEC_PATH"),
            recall_depth=_read_int("RECALL_DEPTH", 2),
            recall_limit=_read_int("RECALL_LIMIT", 6),
            compact_after_turns=_read_int("COMPACT_AFTER_TURNS", 4),
            compact_keep_recent_turns=_read_int("COMPACT_KEEP_RECENT_TURNS", 2),
            compact_summary_char_limit=_read_int(
                "COMPACT_SUMMARY_CHAR_LIMIT",
                2400,
            ),
            metrics_log_path=(
                resolved_base_dir
                / os.getenv("METRICS_LOG_PATH", ".sub-memory/metrics.jsonl")
            ).resolve(),
            metrics_retention_days=_read_int("METRICS_RETENTION_DAYS", 30),
        )
