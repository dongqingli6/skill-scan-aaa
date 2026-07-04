from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sub_memory.config import Settings
from sub_memory.embeddings import Embedder, SentenceTransformerEmbedder
from sub_memory.store import MemoryStore


@dataclass(slots=True)
class MemoryService:
    settings: Settings
    embedder: Embedder
    store: MemoryStore

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        embedder: Embedder | None = None,
    ) -> "MemoryService":
        resolved_embedder = embedder or SentenceTransformerEmbedder(
            settings.embedding_model_name
        )
        store = MemoryStore(settings, resolved_embedder)
        return cls(
            settings=settings,
            embedder=resolved_embedder,
            store=store,
        )

    def close(self) -> None:
        self.store.close()

    def store_memory(self, user_text: str, ai_response: str) -> dict[str, Any]:
        return self.store.store_memory(user_text=user_text, ai_response=ai_response)

    def recall_associated_memory(
        self,
        query: str,
        depth: int | None = None,
    ) -> dict[str, Any]:
        return self.store.recall_associated_memory(
            query=query,
            depth=depth or self.settings.recall_depth,
        )

    def reinforce_memory(self, node_ids: list[str]) -> dict[str, Any]:
        return self.store.reinforce_memory(node_ids=node_ids)

    def delete_memory(self, node_id: str) -> dict[str, Any]:
        return self.store.delete_memory(node_id)

    def get_status(self) -> dict[str, Any]:
        return {
            "db_path": str(self.settings.db_path),
            "embedding_model_name": self.settings.embedding_model_name,
            "recall_depth": self.settings.recall_depth,
            "recall_limit": self.settings.recall_limit,
            "compact_after_turns": self.settings.compact_after_turns,
            "compact_keep_recent_turns": self.settings.compact_keep_recent_turns,
            "node_count": self.store.count_nodes(),
        }

    def get_dashboard_stats(self) -> dict[str, Any]:
        return self.store.get_dashboard_stats()

    def list_memories(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.store.list_memories(limit=limit, offset=offset, query=query)

    def get_memory(self, node_id: str) -> dict[str, Any] | None:
        memory = self.store.get_memory(node_id)
        if memory is None:
            return None
        return {
            **memory,
            "connected_memories": self.store.get_connected_memories(node_id),
        }

    def get_graph_subtree(
        self,
        node_id: str,
        *,
        depth: int = 2,
        limit: int = 20,
    ) -> dict[str, Any]:
        return self.store.get_graph_subtree(node_id, depth=depth, limit=limit)
