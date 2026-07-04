from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
import sqlite3
import threading
from typing import Any
from uuid import uuid4

import networkx as nx

from sub_memory.config import Settings
from sub_memory.embeddings import Embedder


@dataclass(slots=True)
class MemoryRecord:
    node_id: str
    text: str
    timestamp: str


@dataclass(slots=True)
class MemoryMatch(MemoryRecord):
    distance: float


@dataclass(slots=True)
class ConnectedMemory(MemoryRecord):
    weight: float


def _serialize_vector(values: list[float]) -> bytes:
    try:
        import sqlite_vec  # type: ignore

        if hasattr(sqlite_vec, "serialize_float32"):
            return sqlite_vec.serialize_float32(values)
    except ImportError:
        pass

    return array("f", values).tobytes()


class MemoryStore:
    def __init__(self, settings: Settings, embedder: Embedder) -> None:
        self._settings = settings
        self._embedder = embedder
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self._settings.db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._graph = nx.Graph()
        self._last_node_id: str | None = None

        self._load_sqlite_vec()
        self._create_schema()
        self._sync_embedding_metadata()
        self._load_graph()

    @property
    def graph(self) -> nx.Graph:
        return self._graph

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def count_nodes(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM nodes").fetchone()
        assert row is not None
        return int(row["count"])

    def count_edges(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM edges").fetchone()
        assert row is not None
        return int(row["count"])

    def list_memories(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                n.id,
                n.text,
                n.timestamp,
                COUNT(e.source_id) + COUNT(e2.target_id) AS connection_count
            FROM nodes n
            LEFT JOIN edges e ON e.source_id = n.id
            LEFT JOIN edges e2 ON e2.target_id = n.id
        """
        params: list[Any] = []
        if query and query.strip():
            sql += " WHERE n.text LIKE ?"
            params.append(f"%{query.strip()}%")

        sql += """
            GROUP BY n.id, n.text, n.timestamp
            ORDER BY n.timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()

        return [
            {
                "node_id": row["id"],
                "text": row["text"],
                "timestamp": row["timestamp"],
                "connection_count": int(row["connection_count"] or 0),
            }
            for row in rows
        ]

    def get_memory(self, node_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, text, timestamp
                FROM nodes
                WHERE id = ?
                """,
                (node_id,),
            ).fetchone()
            if row is None:
                return None

        return {
            "node_id": row["id"],
            "text": row["text"],
            "timestamp": row["timestamp"],
        }

    def get_connected_memories(
        self,
        node_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                WITH connected AS (
                    SELECT target_id AS connected_id, weight
                    FROM edges
                    WHERE source_id = ?
                    UNION ALL
                    SELECT source_id AS connected_id, weight
                    FROM edges
                    WHERE target_id = ?
                )
                SELECT n.id, n.text, n.timestamp, c.weight
                FROM connected c
                JOIN nodes n ON n.id = c.connected_id
                ORDER BY c.weight DESC, n.timestamp DESC
                LIMIT ?
                """,
                (node_id, node_id, limit),
            ).fetchall()

        return [
            {
                "node_id": row["id"],
                "text": row["text"],
                "timestamp": row["timestamp"],
                "weight": float(row["weight"]),
            }
            for row in rows
        ]

    def get_graph_subtree(
        self,
        node_id: str,
        *,
        depth: int = 2,
        limit: int = 20,
    ) -> dict[str, Any]:
        with self._lock:
            self._ensure_graph_contains_locked(node_id)
            ordered_node_ids, depth_by_node, parent_by_node = self._weighted_bfs_locked(
                node_id,
                depth=depth,
                limit=limit,
            )
            if not ordered_node_ids:
                return {"center_node_id": node_id, "nodes": [], "edges": []}

            records = self._fetch_nodes_locked(ordered_node_ids)
            node_set = set(ordered_node_ids)
            edge_rows = self._conn.execute(
                f"""
                SELECT source_id, target_id, weight
                FROM edges
                WHERE source_id IN ({", ".join("?" for _ in ordered_node_ids)})
                  AND target_id IN ({", ".join("?" for _ in ordered_node_ids)})
                ORDER BY weight DESC
                """,
                ordered_node_ids + ordered_node_ids,
            ).fetchall()

        nodes = [
            {
                "node_id": record.node_id,
                "text": record.text,
                "timestamp": record.timestamp,
                "depth": depth_by_node.get(record.node_id, 0),
                "parent_id": parent_by_node.get(record.node_id),
            }
            for record in records
            if record.node_id in node_set
        ]
        edges = [
            {
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "weight": float(row["weight"]),
            }
            for row in edge_rows
        ]
        return {
            "center_node_id": node_id,
            "nodes": nodes,
            "edges": edges,
        }

    def get_dashboard_stats(self) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT
                    COUNT(*) AS node_count,
                    MAX(timestamp) AS last_timestamp,
                    SUM(CASE
                        WHEN datetime(timestamp) >= datetime('now', '-1 day')
                        THEN 1 ELSE 0 END) AS recent_24h_count,
                    SUM(CASE
                        WHEN datetime(timestamp) >= datetime('now', '-7 day')
                        THEN 1 ELSE 0 END) AS recent_7d_count
                FROM nodes
                """
            ).fetchone()
            edge_count = self.count_edges()
            recent_memories = self.list_memories(limit=10, offset=0)

        assert row is not None
        node_count = int(row["node_count"] or 0)
        return {
            "db_path": str(self._settings.db_path),
            "node_count": node_count,
            "edge_count": edge_count,
            "last_timestamp": row["last_timestamp"],
            "recent_24h_count": int(row["recent_24h_count"] or 0),
            "recent_7d_count": int(row["recent_7d_count"] or 0),
            "average_connections": round((edge_count * 2 / node_count), 3)
            if node_count
            else 0.0,
            "recent_memories": recent_memories,
        }

    def get_edge_weight(self, left_id: str, right_id: str) -> float | None:
        source_id, target_id = sorted((left_id, right_id))
        row = self._conn.execute(
            """
            SELECT weight
            FROM edges
            WHERE source_id = ? AND target_id = ?
            """,
            (source_id, target_id),
        ).fetchone()
        if row is None:
            return None
        return float(row["weight"])

    def store_memory(self, user_text: str, ai_response: str) -> dict[str, Any]:
        memory_text = self._format_turn_text(user_text, ai_response)
        embedding = self._embedder.embed_text(memory_text)
        node_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO nodes (id, text, embedding, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (node_id, memory_text, _serialize_vector(embedding), timestamp),
            )
            self._conn.commit()

            self._graph.add_node(node_id, text=memory_text, timestamp=timestamp)

            previous_node_id = self._last_node_id
            # This object is responsible for tolerating runtime DB replacement without linking to stale node ids.
            if (
                previous_node_id is not None
                and previous_node_id != node_id
                and self._node_exists_locked(previous_node_id)
            ):
                try:
                    self._upsert_edge_locked(
                        previous_node_id,
                        node_id,
                        create_weight=1.0,
                        increment=0.0,
                    )
                except sqlite3.IntegrityError:
                    # This object is responsible for surviving cross-process graph churn
                    # where the previous node disappears after the existence check.
                    self._graph.remove_nodes_from([previous_node_id])
            elif previous_node_id is not None and previous_node_id != node_id:
                self._graph.remove_nodes_from([previous_node_id])

            self._last_node_id = node_id

        return {
            "status": "stored",
            "node_id": node_id,
            "timestamp": timestamp,
        }

    def delete_memory(self, node_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, text, timestamp
                FROM nodes
                WHERE id = ?
                """,
                (node_id,),
            ).fetchone()
            if row is None:
                return {"status": "not_found", "node_id": node_id}

            connection_count = int(self._graph.degree(node_id)) if node_id in self._graph else 0

            self._conn.execute(
                """
                DELETE FROM nodes
                WHERE id = ?
                """,
                (node_id,),
            )
            self._conn.commit()

            if node_id in self._graph:
                self._graph.remove_node(node_id)

            if self._last_node_id == node_id:
                last_row = self._conn.execute(
                    """
                    SELECT id
                    FROM nodes
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """
                ).fetchone()
                self._last_node_id = str(last_row["id"]) if last_row else None

        return {
            "status": "deleted",
            "node_id": node_id,
            "timestamp": row["timestamp"],
            "deleted_connection_count": connection_count,
        }

    def recall_associated_memory(
        self,
        query: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        if not query.strip():
            return {"query": query, "node_ids": [], "memories": []}

        query_embedding = self._embedder.embed_text(query)
        seed_matches = self.search_similar(query_embedding, limit=1)
        if not seed_matches:
            return {"query": query, "node_ids": [], "memories": []}

        seed = seed_matches[0]
        with self._lock:
            ordered_node_ids, depth_by_node, _parent_by_node = self._weighted_bfs_locked(
                seed.node_id,
                depth=depth,
                limit=self._settings.recall_limit,
            )
            records = self._fetch_nodes_locked(ordered_node_ids)

        memories = [
            {
                "node_id": record.node_id,
                "text": record.text,
                "timestamp": record.timestamp,
                "depth": depth_by_node[record.node_id],
            }
            for record in records
        ]

        return {
            "query": query,
            "seed_id": seed.node_id,
            "seed_distance": round(seed.distance, 6),
            "node_ids": [record.node_id for record in records],
            "memories": memories,
        }

    def reinforce_memory(self, node_ids: list[str]) -> dict[str, Any]:
        unique_ids = list(dict.fromkeys(node_ids))
        if len(unique_ids) < 2:
            return {"status": "skipped", "updated_edges": []}

        updated_edges: list[dict[str, Any]] = []

        with self._lock:
            for left_id, right_id in combinations(unique_ids, 2):
                new_weight = self._upsert_edge_locked(
                    left_id,
                    right_id,
                    create_weight=1.0,
                    increment=0.1,
                )
                updated_edges.append(
                    {
                        "source_id": min(left_id, right_id),
                        "target_id": max(left_id, right_id),
                        "weight": round(new_weight, 3),
                    }
                )

        return {"status": "reinforced", "updated_edges": updated_edges}

    def search_similar(
        self,
        query_embedding: list[float],
        limit: int,
    ) -> list[MemoryMatch]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, text, timestamp, vec_distance_cosine(embedding, ?) AS distance
                FROM nodes
                ORDER BY distance ASC
                LIMIT ?
                """,
                (_serialize_vector(query_embedding), limit),
            ).fetchall()

        return [
            MemoryMatch(
                node_id=row["id"],
                text=row["text"],
                timestamp=row["timestamp"],
                distance=float(row["distance"]),
            )
            for row in rows
        ]

    def _create_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    PRIMARY KEY (source_id, target_id),
                    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_timestamp
                    ON nodes (timestamp DESC);

                CREATE INDEX IF NOT EXISTS idx_edges_source
                    ON edges (source_id, weight DESC);

                CREATE INDEX IF NOT EXISTS idx_edges_target
                    ON edges (target_id, weight DESC);
                """
            )
            self._conn.commit()

    def _sync_embedding_metadata(self) -> None:
        model_name = self._settings.embedding_model_name
        dimension = str(self._embedder.dimension)

        with self._lock:
            stored_model_name = self._get_metadata_locked("embedding_model_name")
            stored_dimension = self._get_metadata_locked("embedding_dimension")
            is_empty = self.count_nodes() == 0

            if stored_model_name is None and stored_dimension is None:
                self._set_metadata_locked("embedding_model_name", model_name)
                self._set_metadata_locked("embedding_dimension", dimension)
                self._conn.commit()
                return

            if (
                stored_model_name == model_name
                and stored_dimension == dimension
            ):
                return

            if is_empty:
                self._set_metadata_locked("embedding_model_name", model_name)
                self._set_metadata_locked("embedding_dimension", dimension)
                self._conn.commit()
                return

        raise RuntimeError(
            "The existing memory database was created with a different embedding "
            f"model ({stored_model_name}/{stored_dimension}). Start with a fresh "
            "memory.db or reuse the same model."
        )

    def _load_graph(self) -> None:
        with self._lock:
            node_rows = self._conn.execute(
                """
                SELECT id, text, timestamp
                FROM nodes
                ORDER BY timestamp ASC
                """
            ).fetchall()
            edge_rows = self._conn.execute(
                """
                SELECT source_id, target_id, weight
                FROM edges
                """
            ).fetchall()

            self._graph.clear()
            for row in node_rows:
                self._graph.add_node(
                    row["id"],
                    text=row["text"],
                    timestamp=row["timestamp"],
                )
                self._last_node_id = row["id"]

            for row in edge_rows:
                self._graph.add_edge(
                    row["source_id"],
                    row["target_id"],
                    weight=float(row["weight"]),
                )

    def _ensure_graph_contains_locked(self, node_id: str) -> None:
        if node_id in self._graph:
            return

        if not self._node_exists_locked(node_id):
            return

        self._load_graph()

    def _load_sqlite_vec(self) -> None:
        load_errors: list[str] = []
        self._conn.enable_load_extension(True)

        if self._settings.sqlite_vec_path:
            try:
                self._conn.load_extension(self._settings.sqlite_vec_path)
                self._conn.enable_load_extension(False)
                return
            except sqlite3.OperationalError as exc:
                load_errors.append(
                    f"load_extension({self._settings.sqlite_vec_path!r}) failed: {exc}"
                )

        try:
            import sqlite_vec  # type: ignore
        except ImportError as exc:
            load_errors.append(f"sqlite_vec import failed: {exc}")
        else:
            try:
                sqlite_vec.load(self._conn)
                self._conn.enable_load_extension(False)
                return
            except Exception as exc:  # pragma: no cover - depends on native wheel
                load_errors.append(f"sqlite_vec.load(...) failed: {exc}")

        self._conn.enable_load_extension(False)
        raise RuntimeError(
            "Failed to load sqlite-vec. Install the sqlite-vec package or set "
            "SQLITE_VEC_PATH to the compiled extension.\n"
            + "\n".join(load_errors)
        )

    def _fetch_nodes_locked(self, ordered_node_ids: list[str]) -> list[MemoryRecord]:
        if not ordered_node_ids:
            return []

        placeholders = ", ".join("?" for _ in ordered_node_ids)
        rows = self._conn.execute(
            f"""
            SELECT id, text, timestamp
            FROM nodes
            WHERE id IN ({placeholders})
            """,
            ordered_node_ids,
        ).fetchall()

        by_id = {
            row["id"]: MemoryRecord(
                node_id=row["id"],
                text=row["text"],
                timestamp=row["timestamp"],
            )
            for row in rows
        }
        return [by_id[node_id] for node_id in ordered_node_ids if node_id in by_id]

    def _weighted_bfs_locked(
        self,
        seed_id: str,
        depth: int,
        limit: int,
    ) -> tuple[list[str], dict[str, int], dict[str, str | None]]:
        if seed_id not in self._graph:
            return [], {}, {}

        visited = {seed_id}
        depth_by_node = {seed_id: 0}
        parent_by_node = {seed_id: None}
        ordered_node_ids = [seed_id]
        queue = deque([seed_id])

        while queue and len(ordered_node_ids) < limit:
            current = queue.popleft()
            current_depth = depth_by_node[current]
            if current_depth >= depth:
                continue

            neighbors = sorted(
                self._graph[current].items(),
                key=lambda item: float(item[1].get("weight", 0.0)),
                reverse=True,
            )
            for neighbor_id, _edge_data in neighbors:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                depth_by_node[neighbor_id] = current_depth + 1
                parent_by_node[neighbor_id] = current
                ordered_node_ids.append(neighbor_id)
                queue.append(neighbor_id)
                if len(ordered_node_ids) >= limit:
                    break

        return ordered_node_ids, depth_by_node, parent_by_node

    def _upsert_edge_locked(
        self,
        left_id: str,
        right_id: str,
        *,
        create_weight: float,
        increment: float,
    ) -> float:
        source_id, target_id = sorted((left_id, right_id))
        row = self._conn.execute(
            """
            SELECT weight
            FROM edges
            WHERE source_id = ? AND target_id = ?
            """,
            (source_id, target_id),
        ).fetchone()

        if row is None:
            new_weight = create_weight + increment
            self._conn.execute(
                """
                INSERT INTO edges (source_id, target_id, weight)
                VALUES (?, ?, ?)
                """,
                (source_id, target_id, new_weight),
            )
        else:
            new_weight = float(row["weight"]) + increment
            self._conn.execute(
                """
                UPDATE edges
                SET weight = ?
                WHERE source_id = ? AND target_id = ?
                """,
                (new_weight, source_id, target_id),
            )

        self._conn.commit()
        self._graph.add_edge(source_id, target_id, weight=new_weight)
        return new_weight

    def _format_turn_text(self, user_text: str, ai_response: str) -> str:
        return f"User: {user_text.strip()}\nAssistant: {ai_response.strip()}"

    def _get_metadata_locked(self, key: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT value
            FROM metadata
            WHERE key = ?
            """,
            (key,),
        ).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def _set_metadata_locked(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def _node_exists_locked(self, node_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM nodes
            WHERE id = ?
            """,
            (node_id,),
        ).fetchone()
        return row is not None
