from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from sub_memory.store import MemoryStore


@dataclass(slots=True)
class ToolRegistry:
    store: MemoryStore

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "store_memory",
                "description": (
                    "Persist the current user/assistant exchange into local long-term "
                    "memory and connect it to the previous conversation node."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_text": {
                            "type": "string",
                            "description": "The user's message to save.",
                        },
                        "ai_response": {
                            "type": "string",
                            "description": "The assistant response to save.",
                        },
                    },
                    "required": ["user_text", "ai_response"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "recall_associated_memory",
                "description": (
                    "Retrieve the closest memory for a query, then expand related "
                    "memories through the weighted association graph."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The text query used for memory retrieval.",
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Maximum BFS depth to traverse from the seed node.",
                            "minimum": 1,
                            "default": 2,
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "reinforce_memory",
                "description": (
                    "Increase association weights between memory node IDs that "
                    "materially informed the answer."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "node_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "description": "Memory node IDs to reinforce.",
                        }
                    },
                    "required": ["node_ids"],
                    "additionalProperties": False,
                },
            },
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tool_map().get(name)
        if tool is None:
            raise ValueError(f"Unknown tool requested: {name}")
        return tool(arguments)

    def _tool_map(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            "store_memory": self._store_memory,
            "recall_associated_memory": self._recall_associated_memory,
            "reinforce_memory": self._reinforce_memory,
        }

    def _store_memory(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.store.store_memory(
            user_text=str(arguments["user_text"]),
            ai_response=str(arguments["ai_response"]),
        )

    def _recall_associated_memory(self, arguments: dict[str, Any]) -> dict[str, Any]:
        depth = int(arguments.get("depth", 2))
        return self.store.recall_associated_memory(
            query=str(arguments["query"]),
            depth=depth,
        )

    def _reinforce_memory(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_node_ids = arguments["node_ids"]
        if not isinstance(raw_node_ids, list):
            raise ValueError(
                "reinforce_memory expects node_ids to be a list of strings."
            )
        node_ids = [str(node_id) for node_id in raw_node_ids]
        return self.store.reinforce_memory(node_ids)

    @staticmethod
    def parse_arguments(raw_arguments: Any) -> dict[str, Any]:
        if raw_arguments is None:
            return {}
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if isinstance(raw_arguments, str):
            return json.loads(raw_arguments)
        raise ValueError(f"Unsupported tool arguments payload: {type(raw_arguments)!r}")

