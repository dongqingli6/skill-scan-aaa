from __future__ import annotations


SAFE_SESSION_COMMANDS = ("help", "version", "metadata", "inspect")


def session_plan(rounds: int) -> list[dict[str, object]]:
    commands = ["help", "version", "metadata", "inspect"]
    plan = []
    for index in range(max(1, rounds)):
        plan.append(
            {
                "session_id": f"stage28-session-{index + 1:02d}",
                "round_id": index + 1,
                "command": commands[index % len(commands)],
                "fake_home_reused": index > 0,
            }
        )
    return plan


def evaluate_session_command(command: str) -> dict[str, object]:
    if command not in SAFE_SESSION_COMMANDS:
        return {"allowed": False, "reason": "session command is not in safe allowlist"}
    return {"allowed": True, "reason": "safe metadata-only session command"}
