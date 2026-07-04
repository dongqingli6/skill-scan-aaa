from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class Embedder(Protocol):
    @property
    def dimension(self) -> int: ...

    def embed_text(self, text: str) -> list[float]: ...


@dataclass(slots=True)
class SentenceTransformerEmbedder:
    model_name: str
    _model: object | None = field(default=None, init=False, repr=False)
    _dimension: int | None = field(default=None, init=False, repr=False)

    def _ensure_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Create a virtualenv and install requirements.txt first."
            ) from exc

        self._model = SentenceTransformer(self.model_name)
        self._dimension = int(self._model.get_sentence_embedding_dimension())
        return self._model

    @property
    def dimension(self) -> int:
        self._ensure_model()
        assert self._dimension is not None
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot embed empty text.")

        model = self._ensure_model()
        vector = model.encode(text, normalize_embeddings=True)
        return [float(value) for value in vector]

