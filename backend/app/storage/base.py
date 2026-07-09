from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List


class VectorStore(ABC):
    @abstractmethod
    def add(self, vector: List[float], metadata: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, vector: List[float], top_k: int) -> List[Any]:
        raise NotImplementedError
