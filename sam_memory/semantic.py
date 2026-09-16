"""
Semantic Vector and Text Similarity Engine for Tier 3 Memory.
Provides cosine similarity ranking over vector embeddings or lightweight TF-IDF fallback.
"""
import math

from sam_memory.models import MemoryEntry, MemorySearchResult


class SemanticMemoryEngine:
    """
    Ranks memories by semantic embedding or token overlap similarity.
    """

    def __init__(self) -> None:
        self._embeddings: dict[str, list[float]] = {}

    def _compute_cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        if len(v1) != len(v2) or not v1:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))

    def _compute_token_similarity(self, query: str, text: str) -> float:
        """Jaccard similarity on tokens as universal fallback without PyTorch/ONNX."""
        q_tokens = set(query.lower().split())
        t_tokens = set(text.lower().split())
        if not q_tokens or not t_tokens:
            return 0.0
        intersection = len(q_tokens & t_tokens)
        union = len(q_tokens | t_tokens)
        return intersection / union

    def rank(self, query: str, entries: list[MemoryEntry], limit: int = 5) -> list[MemorySearchResult]:
        """Rank entries based on semantic token overlap and importance score."""
        scored = []
        for entry in entries:
            target_text = f"{entry.key} {entry.value} {' '.join(entry.tags)}"
            sim = self._compute_token_similarity(query, target_text)
            importance_boost = entry.importance * 0.05
            final_score = min(1.0, sim + importance_boost)
            if sim > 0.0:
                scored.append(MemorySearchResult(entry=entry, score=round(final_score, 3)))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]
