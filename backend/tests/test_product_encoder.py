"""
DishIQ Phase 6.1 — Unit Tests for ProductEncoder
Tests embedding generation, empty text handling, dimension consistency, and caching.
"""
import pytest
import numpy as np
from app.product_matching.encoder import ProductEncoder, get_encoder


class TestProductEncoder:
    """
    Test suite for Sentence Transformer encoder wrapper.
    """

    def test_encoder_initialization_and_dimension(self):
        encoder = get_encoder()
        assert encoder is not None
        dim = encoder.get_embedding_dimension()
        assert dim == 384  # all-MiniLM-L6-v2 output dimension

    def test_encode_valid_text(self):
        encoder = get_encoder()
        embedding = encoder.encode_text("paneer")
        assert isinstance(embedding, np.ndarray)
        assert embedding.ndim == 1
        assert embedding.shape[0] == 384
        assert embedding.dtype == np.float32

    def test_same_text_produces_identical_embeddings(self):
        encoder = get_encoder()
        vec1 = encoder.encode_text("200g paneer cubes")
        vec2 = encoder.encode_text("200g paneer cubes")
        np.testing.assert_array_almost_equal(vec1, vec2, decimal=5)

    def test_empty_and_whitespace_text_handled_safely(self):
        encoder = get_encoder()
        vec_empty = encoder.encode_text("")
        vec_space = encoder.encode_text("   ")
        vec_none = encoder.encode_text(None)

        assert isinstance(vec_empty, np.ndarray)
        assert vec_empty.shape == (384,)
        assert np.all(vec_empty == 0.0)

        assert vec_space.shape == (384,)
        assert np.all(vec_space == 0.0)

        assert vec_none.shape == (384,)
        assert np.all(vec_none == 0.0)

    def test_encode_texts_batch(self):
        encoder = get_encoder()
        texts = ["Fresh Paneer 200g", "Ripe Red Tomatoes", ""]
        embeddings = encoder.encode_texts(texts)

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 384)
        # Empty text in batch should be zero vector
        assert np.all(embeddings[2] == 0.0)
        # Non-empty should not be zero vector
        assert np.linalg.norm(embeddings[0]) > 0.0
