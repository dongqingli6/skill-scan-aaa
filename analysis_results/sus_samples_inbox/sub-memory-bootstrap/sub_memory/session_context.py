from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic


@dataclass(slots=True)
class SessionTurn:
    user_text: str
    answer: str


class SessionContext:
    # This object is responsible for compacting older turns into a bounded working summary.
    def __init__(
        self,
        *,
        compact_after_turns: int,
        keep_recent_turns: int,
        summary_char_limit: int,
    ) -> None:
        self._compact_after_turns = compact_after_turns
        self._keep_recent_turns = keep_recent_turns
        self._summary_char_limit = summary_char_limit
        self._summary = ""
        self._recent_turns: list[SessionTurn] = []
        self._turns_since_compact = 0

    def render(self) -> str:
        parts: list[str] = []
        if self._summary:
            parts.append(f"Compact session summary:\n{self._summary}")
        else:
            parts.append("Compact session summary:\nNone yet.")

        if self._recent_turns:
            rendered_turns = []
            for index, turn in enumerate(self._recent_turns, start=1):
                rendered_turns.append(
                    f"{index}. User: {turn.user_text}\n"
                    f"   Assistant: {turn.answer}"
                )
            parts.append("Recent uncompressed turns:\n" + "\n".join(rendered_turns))
        else:
            parts.append("Recent uncompressed turns:\nNone yet.")

        return "\n\n".join(parts)

    def summary_char_count(self) -> int:
        return len(self._summary)

    def recent_turns_char_count(self) -> int:
        return sum(
            len(turn.user_text) + len(turn.answer)
            for turn in self._recent_turns
        )

    def recent_turn_count(self) -> int:
        return len(self._recent_turns)

    def append_turn(self, user_text: str, answer: str) -> bool:
        self._recent_turns.append(SessionTurn(user_text=user_text, answer=answer))
        self._turns_since_compact += 1

        if (
            self._turns_since_compact < self._compact_after_turns
            or len(self._recent_turns) <= self._keep_recent_turns
        ):
            return False

        self._compact_recent_turns()
        return True

    def snapshot(self) -> dict[str, object]:
        return {
            "summary": self._summary,
            "recent_turns": [
                {
                    "user_text": turn.user_text,
                    "answer": turn.answer,
                }
                for turn in self._recent_turns
            ],
            "rendered": self.render(),
            "summary_chars": self.summary_char_count(),
            "recent_turn_count": self.recent_turn_count(),
            "recent_turn_chars": self.recent_turns_char_count(),
            "turns_since_compact": self._turns_since_compact,
        }

    def _compact_recent_turns(self) -> None:
        compact_until = max(0, len(self._recent_turns) - self._keep_recent_turns)
        turns_to_compact = self._recent_turns[:compact_until]
        if not turns_to_compact:
            return

        compact_block = self._summarize_turns(turns_to_compact)
        if self._summary:
            merged = f"{self._summary}\n{compact_block}"
        else:
            merged = compact_block

        self._summary = self._clip_text(merged, self._summary_char_limit)
        self._recent_turns = self._recent_turns[compact_until:]
        self._turns_since_compact = 0

    def _summarize_turns(self, turns: list[SessionTurn]) -> str:
        lines = ["Compacted working context:"]
        for turn in turns:
            lines.append(
                "- User requested: "
                + self._clip_text(turn.user_text.replace("\n", " "), 180)
            )
            lines.append(
                "  Outcome: "
                + self._clip_text(turn.answer.replace("\n", " "), 240)
            )
        return "\n".join(lines)

    def _clip_text(self, text: str, limit: int) -> str:
        collapsed = " ".join(text.split())
        if len(collapsed) <= limit:
            return collapsed
        return collapsed[: max(0, limit - 3)].rstrip() + "..."


@dataclass(slots=True)
class SessionContextEntry:
    context: SessionContext
    last_seen_at: float


class SessionContextRegistry:
    # This object is responsible for retaining compact working context per MCP session.
    def __init__(
        self,
        *,
        compact_after_turns: int,
        keep_recent_turns: int,
        summary_char_limit: int,
        idle_ttl_seconds: int = 3600,
    ) -> None:
        self._compact_after_turns = compact_after_turns
        self._keep_recent_turns = keep_recent_turns
        self._summary_char_limit = summary_char_limit
        self._idle_ttl_seconds = idle_ttl_seconds
        self._entries: dict[str, SessionContextEntry] = {}
        self._lock = RLock()

    def append_turn(self, session_key: str, user_text: str, answer: str) -> dict[str, object]:
        with self._lock:
            self._cleanup_locked()
            entry = self._entries.get(session_key)
            if entry is None:
                entry = SessionContextEntry(
                    context=SessionContext(
                        compact_after_turns=self._compact_after_turns,
                        keep_recent_turns=self._keep_recent_turns,
                        summary_char_limit=self._summary_char_limit,
                    ),
                    last_seen_at=monotonic(),
                )
                self._entries[session_key] = entry

            compacted = entry.context.append_turn(user_text, answer)
            entry.last_seen_at = monotonic()
            snapshot = entry.context.snapshot()
            snapshot["compacted"] = compacted
            return snapshot

    def get_snapshot(self, session_key: str) -> dict[str, object]:
        with self._lock:
            self._cleanup_locked()
            entry = self._entries.get(session_key)
            if entry is None:
                context = SessionContext(
                    compact_after_turns=self._compact_after_turns,
                    keep_recent_turns=self._keep_recent_turns,
                    summary_char_limit=self._summary_char_limit,
                )
                snapshot = context.snapshot()
                snapshot["compacted"] = False
                return snapshot

            entry.last_seen_at = monotonic()
            snapshot = entry.context.snapshot()
            snapshot["compacted"] = False
            return snapshot

    def active_session_count(self) -> int:
        with self._lock:
            self._cleanup_locked()
            return len(self._entries)

    def _cleanup_locked(self) -> None:
        now = monotonic()
        expired_keys = [
            session_key
            for session_key, entry in self._entries.items()
            if now - entry.last_seen_at > self._idle_ttl_seconds
        ]
        for session_key in expired_keys:
            self._entries.pop(session_key, None)
