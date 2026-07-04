from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from sub_memory.config import Settings
from sub_memory.metrics import MetricsLogger, count_chars, estimate_tokens_from_text
from sub_memory.session_context import SessionContextRegistry
from sub_memory.service import MemoryService


MCP_INSTRUCTIONS = """Local memory tools backed by SQLite, sqlite-vec, networkx, and local embeddings.

Use recall_associated_memory to fetch relevant prior memory before answering.
After each substantive turn, call store_memory with the latest user request and your final answer unless the current host runtime already stores turns automatically.
Use reinforce_memory after the answer when recalled memory materially influenced the answer.
If a multi-turn session grows long, compact the active thread into a short working summary and rely on that summary plus recalled memory instead of the full raw transcript.
"""


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_mcp_server(
    service: MemoryService,
    *,
    metrics_logger: MetricsLogger | None = None,
    log_level: str = "INFO",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> FastMCP:
    session_contexts = SessionContextRegistry(
        compact_after_turns=service.settings.compact_after_turns,
        keep_recent_turns=service.settings.compact_keep_recent_turns,
        summary_char_limit=service.settings.compact_summary_char_limit,
    )
    server = FastMCP(
        "sub-memory",
        instructions=MCP_INSTRUCTIONS,
        log_level=log_level.upper(),
        host=host,
        port=port,
    )

    def resolve_session_key(ctx: Context | None) -> str:
        if ctx is None:
            return "default"

        try:
            client_id = ctx.client_id
        except Exception:
            client_id = None
        if client_id:
            return f"client:{client_id}"

        try:
            return f"session:{id(ctx.session)}"
        except Exception:
            try:
                return f"request:{ctx.request_id}"
            except Exception:
                return "default"

    @server.tool(
        name="recall_associated_memory",
        description=(
            "Recall the most similar memory for a query and expand related memories "
            "through the weighted graph."
        ),
        structured_output=True,
    )
    def recall_associated_memory(
        query: str,
        depth: int = 2,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Recall related memory nodes for a natural-language query."""
        started = perf_counter()
        result = service.recall_associated_memory(query=query, depth=depth)
        result["session_context"] = session_contexts.get_snapshot(resolve_session_key(ctx))
        if metrics_logger is not None:
            memory_chars = sum(
                len(memory.get("text", "")) for memory in result.get("memories", [])
            )
            metrics_logger.log_event(
                "mcp_recall",
                {
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "query_chars": len(query),
                    "depth": depth,
                    "seed_id": result.get("seed_id"),
                    "seed_distance": result.get("seed_distance"),
                    "node_count": len(result.get("node_ids", [])),
                    "memory_chars": memory_chars,
                    "session_summary_chars": result["session_context"].get("summary_chars", 0),
                    "session_recent_turn_count": result["session_context"].get("recent_turn_count", 0),
                    "estimated_memory_tokens": estimate_tokens_from_text(
                        "\n".join(
                            memory.get("text", "")
                            for memory in result.get("memories", [])
                        )
                    ),
                },
            )
        return result

    @server.tool(
        name="store_memory",
        description=(
            "Store a user/assistant exchange in local long-term memory and connect it "
            "to the previous turn."
        ),
        structured_output=True,
    )
    def store_memory(
        user_text: str,
        ai_response: str,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Persist a new memory node using the provided conversation turn."""
        started = perf_counter()
        result = service.store_memory(user_text=user_text, ai_response=ai_response)
        result["session_context"] = session_contexts.append_turn(
            resolve_session_key(ctx),
            user_text,
            ai_response,
        )
        if metrics_logger is not None:
            metrics_logger.log_event(
                "mcp_store",
                {
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "user_chars": len(user_text),
                    "answer_chars": len(ai_response),
                    "stored_chars": len(user_text) + len(ai_response),
                    "node_id": result.get("node_id"),
                    "session_summary_chars": result["session_context"].get("summary_chars", 0),
                    "session_recent_turn_count": result["session_context"].get("recent_turn_count", 0),
                    "session_compacted": result["session_context"].get("compacted", False),
                },
            )
        return result

    @server.tool(
        name="reinforce_memory",
        description=(
            "Increase association weights between memory nodes that were useful "
            "together."
        ),
        structured_output=True,
    )
    def reinforce_memory(node_ids: list[str]) -> dict[str, Any]:
        """Increase edge weights between the provided memory node IDs."""
        started = perf_counter()
        result = service.reinforce_memory(node_ids=node_ids)
        if metrics_logger is not None:
            metrics_logger.log_event(
                "mcp_reinforce",
                {
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "input_node_count": len(node_ids),
                    "updated_edge_count": len(result.get("updated_edges", [])),
                },
            )
        return result

    @server.tool(
        name="get_memory_status",
        description=(
            "Return local memory store status for installation validation and "
            "operational debugging."
        ),
        structured_output=True,
    )
    def get_memory_status(ctx: Context | None = None) -> dict[str, Any]:
        """Expose the current local memory store configuration and node count."""
        started = perf_counter()
        result = service.get_status()
        result["active_session_contexts"] = session_contexts.active_session_count()
        result["session_context"] = session_contexts.get_snapshot(resolve_session_key(ctx))
        if metrics_logger is not None:
            metrics_logger.log_event(
                "mcp_status",
                {
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "result_chars": count_chars(result),
                    "node_count": result.get("node_count", 0),
                    "active_session_contexts": result.get("active_session_contexts", 0),
                },
            )
        return result

    return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="sub-memory MCP server")
    parser.add_argument(
        "--base-dir",
        default=str(Path.cwd()),
        help="Project directory containing .env and memory.db.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="MCP transport. Local agent integrations should use stdio.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP-based transports.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP-based transports.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Logging level written to stderr.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_level)

    try:
        settings = Settings.from_env(Path(args.base_dir))
        service = MemoryService.from_settings(settings)
        metrics_logger = MetricsLogger(
            settings.metrics_log_path,
            retention_days=settings.metrics_retention_days,
        )
    except Exception as exc:
        logging.getLogger(__name__).error("Failed to initialize memory service: %s", exc)
        return 1

    try:
        server = build_mcp_server(
            service,
            metrics_logger=metrics_logger,
            log_level=args.log_level,
            host=args.host,
            port=args.port,
        )
        server.run(transport=args.transport)
        return 0
    except Exception as exc:
        logging.getLogger(__name__).error("MCP server failed: %s", exc)
        return 1
    finally:
        service.close()
