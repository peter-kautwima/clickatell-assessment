from typing import List


def embed_texts(texts: List[str]) -> List[List[float]]:
    return [[0.0] * 384 for _ in texts]
