from __future__ import annotations

import unittest

from sub_memory.session_context import SessionContext


class SessionContextTests(unittest.TestCase):
    def test_compacts_older_turns_and_keeps_recent_context(self) -> None:
        context = SessionContext(
            compact_after_turns=2,
            keep_recent_turns=1,
            summary_char_limit=1000,
        )

        self.assertFalse(context.append_turn("first user request", "first answer"))
        self.assertTrue(context.append_turn("second user request", "second answer"))

        rendered = context.render()

        self.assertIn("Compact session summary:", rendered)
        self.assertIn("first user request", rendered)
        self.assertIn("first answer", rendered)
        self.assertIn("second user request", rendered)
        self.assertIn("second answer", rendered)
        self.assertNotIn("1. User: first user request", rendered)

    def test_clips_overlong_summary_text(self) -> None:
        context = SessionContext(
            compact_after_turns=1,
            keep_recent_turns=1,
            summary_char_limit=120,
        )

        context.append_turn("alpha " * 30, "beta " * 30)
        context.append_turn("gamma", "delta")

        rendered = context.render()

        self.assertIn("...", rendered)


if __name__ == "__main__":
    unittest.main()
