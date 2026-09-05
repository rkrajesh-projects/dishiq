"""
DishIQ Phase 6.1 — Grocery Product Matching
Sentence Transformer Encoder module.

Loads and caches the SentenceTransformer model (all-MiniLM-L6-v2) once at runtime.
Instantiating SentenceTransformer on every request is strictly avoided.
"""
from typing import Optional, List
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.logging import logger


class ProductEncoder:
    """
    Reusable encoder wrapping SentenceTransformer for ingredient and product embeddings.
    Uses a class-level singleton cache for the underlying model instance.
    """

    _model_cache: Optional[SentenceTransformer] = None
    _cached_model_name: Optional[str] = None

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.SENTENCE_TRANSFORMER_MODEL

    @classmethod
    def get_model(cls, model_name: str) -> SentenceTransformer:
        """
        Retrieve or initialize the cached SentenceTransformer model instance.
        """
        if cls._model_cache is None or cls._cached_model_name != model_name:
            logger.info(f"Initializing SentenceTransformer model [{model_name}]...")
            cls._model_cache = SentenceTransformer(model_name)
            cls._cached_model_name = model_name
            logger.info(
                f"SentenceTransformer [{model_name}] loaded successfully "
                f"(dim={cls._model_cache.get_sentence_embedding_dimension()})."
            )
        return cls._model_cache

    def encode_text(self, text: str) -> np.ndarray:
        """
        Generate a 1D float32 numerical embedding for a single text string.
        Returns a zero-vector if the text is empty or invalid.
        """
        if not text or not text.strip():
            dim = self.get_embedding_dimension()
            return np.zeros(dim, dtype=np.float32)

        model = self.get_model(self.model_name)
        vec = model.encode(text.strip(), convert_to_numpy=True, show_progress_bar=False)
        return np.asarray(vec, dtype=np.float32)

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate a 2D float32 numerical embedding matrix (N, dim) for a list of strings.
        Empty strings in the list produce zero vectors.
        """
        if not texts:
            dim = self.get_embedding_dimension()
            return np.zeros((0, dim), dtype=np.float32)

        cleaned = [t.strip() if t and t.strip() else "" for t in texts]
        non_empty = [t for t in cleaned if t]

        if not non_empty:
            dim = self.get_embedding_dimension()
            return np.zeros((len(texts), dim), dtype=np.float32)

        model = self.get_model(self.model_name)
        embeddings = model.encode(cleaned, convert_to_numpy=True, show_progress_bar=False)
        arr = np.asarray(embeddings, dtype=np.float32)

        for idx, t in enumerate(cleaned):
            if not t:
                arr[idx] = 0.0

        return arr

    def get_embedding_dimension(self) -> int:
        """
        Return the embedding vector dimension of the active model (384 for all-MiniLM-L6-v2).
        """
        model = self.get_model(self.model_name)
        return model.get_sentence_embedding_dimension()


# Default singleton instance helper
_default_encoder: Optional[ProductEncoder] = None


def get_encoder(model_name: Optional[str] = None) -> ProductEncoder:
    """
    Get or create a reusable ProductEncoder instance.
    """
    global _default_encoder
    target_name = model_name or settings.SENTENCE_TRANSFORMER_MODEL
    if _default_encoder is None or _default_encoder.model_name != target_name:
        _default_encoder = ProductEncoder(model_name=target_name)
    return _default_encoder
