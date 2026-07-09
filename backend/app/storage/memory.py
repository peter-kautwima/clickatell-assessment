from __future__ import annotations

from typing import Any, List

from backend.app.storage.base import VectorStore


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self.items: List[tuple[List[float], Any]] = []

    def add(self, vector: List[float], metadata: Any) -> None:
        self.items.append((vector, metadata))

    def search(self, vector: List[float], top_k: int) -> List[Any]:
        return [metadata for _, metadata in self.items[:top_k]]
