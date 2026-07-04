from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from openai import OpenAI, OpenAIError

from sub_memory.config import Settings
from sub_memory.metrics import MetricsLogger, count_chars, estimate_tokens_from_text
from sub_memory.session_context import SessionContext
from sub_memory.service import MemoryService
from sub_memory.tools import ToolRegistry


BASE_INSTRUCTIONS = """You are a local AI assistant with a private long-term memory graph.

Use the preloaded memory context when it is relevant to the user's request.
If the injected context is not enough, call recall_associated_memory to inspect deeper related memories.
Use the compact session summary and recent-turn context when they are relevant.
Older session turns may be compacted into a short summary to keep token usage bounded.
Call reinforce_memory only when recalled memories materially influenced your final answer.
Do not call store_memory during a normal turn unless the user explicitly asks you to save something immediately.
The host runtime automatically stores the final user/assistant exchange after you answer.
"""


@dataclass(slots=True)
class TurnResult:
    answer: str
    recalled_node_ids: set[str]
    store_called_manually: bool
    reinforce_called_manually: bool
    usage: dict[str, int]


class LocalMemoryAgent:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in."
            )

        self._settings = settings
        self._service = MemoryService.from_settings(settings)
        self._store = self._service.store
        self._tools = ToolRegistry(self._store)
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._metrics = MetricsLogger(
            settings.metrics_log_path,
            retention_days=settings.metrics_retention_days,
        )
        self._session_context = SessionContext(
            compact_after_turns=settings.compact_after_turns,
            keep_recent_turns=settings.compact_keep_recent_turns,
            summary_char_limit=settings.compact_summary_char_limit,
        )

    def close(self) -> None:
        self._executor.shutdown(wait=True)
        self._service.close()

    def run_interactive(self) -> int:
        print("Local memory agent started. Type 'exit' or 'quit' to stop.")

        while True:
            try:
                user_text = input("You> ").strip()
            except EOFError:
                print()
                return 0
            except KeyboardInterrupt:
                print("\nInterrupted.")
                return 130

            if not user_text:
                continue
            if user_text.lower() in self._settings.exit_commands:
                return 0

            try:
                answer = self.handle_turn(user_text)
            except Exception as exc:
                print(f"Error> {exc}")
                continue

            print(f"AI> {answer}")

    def run_once(self, prompt: str) -> str:
        return self.handle_turn(prompt)

    def handle_turn(self, user_text: str) -> str:
        turn_started = perf_counter()
        recall_future = self._executor.submit(
            self._store.recall_associated_memory,
            user_text,
            self._settings.recall_depth,
        )

        recall_result: dict[str, Any]
        try:
            recall_result = recall_future.result()
        except Exception as exc:
            recall_result = {
                "error": f"automatic recall failed: {exc}",
                "node_ids": [],
                "memories": [],
            }

        system_prompt = self._build_system_prompt(recall_result)
        turn_result = self._generate_response(user_text, system_prompt, recall_result)

        if not turn_result.store_called_manually:
            self._executor.submit(
                self._store.store_memory,
                user_text,
                turn_result.answer,
            )

        if (
            turn_result.recalled_node_ids
            and not turn_result.reinforce_called_manually
        ):
            self._executor.submit(
                self._store.reinforce_memory,
                sorted(turn_result.recalled_node_ids),
            )

        self._session_context.append_turn(user_text, turn_result.answer)
        self._metrics.log_event(
            "agent_turn",
            {
                "duration_ms": round((perf_counter() - turn_started) * 1000, 3),
                "user_chars": len(user_text),
                "answer_chars": len(turn_result.answer),
                "summary_chars": self._session_context.summary_char_count(),
                "recent_turn_chars": self._session_context.recent_turns_char_count(),
                "recalled_memory_count": len(recall_result.get("memories", [])),
                "recalled_memory_chars": sum(
                    len(memory.get("text", ""))
                    for memory in recall_result.get("memories", [])
                ),
                "memory_context_chars": count_chars(
                    self._build_memory_context_only(recall_result)
                ),
                "estimated_memory_context_tokens": estimate_tokens_from_text(
                    self._build_memory_context_only(recall_result)
                ),
                "system_prompt_chars": len(system_prompt),
                "input_tokens": turn_result.usage.get("input_tokens", 0),
                "output_tokens": turn_result.usage.get("output_tokens", 0),
                "total_tokens": turn_result.usage.get("total_tokens", 0),
            },
        )
        return turn_result.answer

    def _build_system_prompt(self, recall_result: dict[str, Any]) -> str:
        memory_block = self._build_memory_context_only(recall_result)
        error_line = self._build_recall_error_line(recall_result)

        session_block = self._session_context.render()
        return (
            f"{BASE_INSTRUCTIONS}\n"
            f"Retrieved memory context:\n{memory_block}{error_line}\n\n"
            f"Active session context:\n{session_block}"
        )

    def _build_memory_context_only(self, recall_result: dict[str, Any]) -> str:
        memories = recall_result.get("memories", [])
        if not memories:
            return "No relevant prior memories were retrieved for this turn."

        formatted = []
        for memory in memories:
            formatted.append(
                f"- [{memory['node_id']}] depth={memory['depth']} "
                f"{memory['text']}"
            )
        return "\n".join(formatted)

    def _build_recall_error_line(self, recall_result: dict[str, Any]) -> str:
        if "error" not in recall_result:
            return ""
        return (
            "\nAutomatic recall warning: "
            f"{recall_result['error']}. You may call recall_associated_memory yourself."
        )

    def _generate_response(
        self,
        user_text: str,
        system_prompt: str,
        recall_result: dict[str, Any],
    ) -> TurnResult:
        input_items: list[dict[str, Any]] = [{"role": "user", "content": user_text}]
        recalled_node_ids = set(recall_result.get("node_ids", []))
        store_called_manually = False
        reinforce_called_manually = False
        usage_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        while True:
            try:
                response = self._client.responses.create(
                    model=self._settings.openai_model,
                    instructions=system_prompt,
                    input=input_items,
                    tools=self._tools.schemas,
                    parallel_tool_calls=False,
                    store=False,
                )
            except OpenAIError as exc:
                raise RuntimeError(f"OpenAI response generation failed: {exc}") from exc

            self._merge_usage_totals(usage_totals, response)

            serialized_output = [
                self._serialize_item(item) for item in getattr(response, "output", [])
            ]
            function_calls = [
                item for item in serialized_output if item.get("type") == "function_call"
            ]

            if not function_calls:
                answer = (getattr(response, "output_text", "") or "").strip()
                if not answer:
                    answer = self._collect_message_text(serialized_output).strip()
                if not answer:
                    raise RuntimeError("The model returned no assistant text.")

                return TurnResult(
                    answer=answer,
                    recalled_node_ids=recalled_node_ids,
                    store_called_manually=store_called_manually,
                    reinforce_called_manually=reinforce_called_manually,
                    usage=usage_totals,
                )

            input_items.extend(serialized_output)
            for function_call in function_calls:
                tool_name = str(function_call["name"])
                arguments = self._tools.parse_arguments(function_call.get("arguments"))

                try:
                    tool_result = self._tools.execute(tool_name, arguments)
                except Exception as exc:
                    tool_result = {
                        "status": "error",
                        "tool_name": tool_name,
                        "message": str(exc),
                    }
                else:
                    if tool_name == "recall_associated_memory":
                        recalled_node_ids.update(tool_result.get("node_ids", []))
                    elif tool_name == "store_memory":
                        store_called_manually = True
                    elif tool_name == "reinforce_memory":
                        reinforce_called_manually = True

                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": function_call["call_id"],
                        "output": json.dumps(tool_result, ensure_ascii=False),
                    }
                )

    def _collect_message_text(self, items: list[dict[str, Any]]) -> str:
        chunks: list[str] = []
        for item in items:
            if item.get("type") != "message":
                continue
            for content_item in item.get("content", []):
                if content_item.get("type") in {"output_text", "text"}:
                    text = content_item.get("text")
                    if text:
                        chunks.append(str(text))
        return "\n".join(chunks)

    def _serialize_item(self, item: Any) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json", exclude_none=True)
        if isinstance(item, dict):
            return item
        raise TypeError(f"Unsupported response item type: {type(item)!r}")

    def _merge_usage_totals(self, totals: dict[str, int], response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        input_tokens = self._read_usage_value(
            usage,
            "input_tokens",
            "prompt_tokens",
        )
        output_tokens = self._read_usage_value(
            usage,
            "output_tokens",
            "completion_tokens",
        )
        total_tokens = self._read_usage_value(
            usage,
            "total_tokens",
        )

        totals["input_tokens"] += input_tokens
        totals["output_tokens"] += output_tokens
        totals["total_tokens"] += (
            total_tokens if total_tokens else input_tokens + output_tokens
        )

    def _read_usage_value(self, usage: Any, *names: str) -> int:
        for name in names:
            if hasattr(usage, name):
                value = getattr(usage, name)
            elif isinstance(usage, dict):
                value = usage.get(name)
            else:
                value = None
            if isinstance(value, int):
                return value
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local memory agent")
    parser.add_argument(
        "--once",
        help="Run a single prompt and exit.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(Path.cwd()),
        help="Project directory containing .env and memory.db.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = Settings.from_env(Path(args.base_dir))
    try:
        agent = LocalMemoryAgent(settings)
    except Exception as exc:
        print(f"Error> {exc}")
        return 1

    try:
        try:
            if args.once:
                print(agent.run_once(args.once))
                return 0
            return agent.run_interactive()
        except Exception as exc:
            print(f"Error> {exc}")
            return 1
    finally:
        agent.close()
