"""
DishIQ Phase 6.1 — Unit Tests for ProductMatcher & Cosine Similarity
Tests semantic similarity ranking, threshold filtering, and error handling.
"""
import pytest
import numpy as np
from app.product_matching.matcher import ProductMatcher, compute_cosine_similarity
from app.product_matching.encoder import get_encoder
from app.product_matching.schemas import MatchIngredientsResponse, ProductMatchResult


class TestCosineSimilarity:
    """
    Unit tests for vector cosine similarity math.
    """

    def test_identical_vectors_have_high_similarity(self):
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        score = compute_cosine_similarity(v, v)
        assert abs(score - 1.0) < 1e-4

    def test_orthogonal_vectors_have_zero_similarity(self):
        v1 = np.array([1.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0], dtype=np.float32)
        score = compute_cosine_similarity(v1, v2)
        assert score == 0.0

    def test_zero_vector_handling_does_not_crash(self):
        v1 = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        assert compute_cosine_similarity(v1, v2) == 0.0
        assert compute_cosine_similarity(v1, v1) == 0.0
        assert compute_cosine_similarity(None, v2) == 0.0


class TestProductMatcher:
    """
    Unit tests for product matching engine.
    """

    @pytest.fixture
    def sample_products(self):
        return [
            {
                "product_id": "p1",
                "product_name": "Amul Fresh Paneer 200g",
                "brand": "Amul",
                "category": "Dairy",
                "price": 95.0,
            },
            {
                "product_id": "p2",
                "product_name": "Mother Dairy Malai Paneer 250g",
                "brand": "Mother Dairy",
                "category": "Dairy",
                "price": 115.0,
            },
            {
                "product_id": "p3",
                "product_name": "Aashirvaad Whole Wheat Atta 5kg",
                "brand": "Aashirvaad",
                "category": "Grains & Pulses",
                "price": 240.0,
            },
            {
                "product_id": "p4",
                "product_name": "Tata Iodized Salt 1kg",
                "brand": "Tata",
                "category": "Spices",
                "price": 22.0,
            },
        ]

    def test_paneer_matching_ranks_paneer_products_first(self, sample_products):
        matcher = ProductMatcher()
        response = matcher.match_products("paneer", sample_products, include_unmatched=True)

        assert isinstance(response, MatchIngredientsResponse)
        assert response.total_matches >= 2
        assert len(response.results) == 4

        # Top 2 results must be paneer products
        top_1_name = response.results[0].product_name.lower()
        top_2_name = response.results[1].product_name.lower()

        assert "paneer" in top_1_name
        assert "paneer" in top_2_name

        # Paneer similarity should be significantly higher than Atta or Salt
        paneer_score = response.results[0].similarity_score
        atta_score = [
            r.similarity_score for r in response.results if "atta" in r.product_name.lower()
        ][0]

        assert paneer_score > atta_score + 0.20

    def test_results_sorted_descending_by_similarity(self, sample_products):
        matcher = ProductMatcher()
        response = matcher.match_products("fresh paneer cubes", sample_products)

        scores = [r.similarity_score for r in response.results]
        assert scores == sorted(scores, reverse=True)

        for i, res in enumerate(response.results):
            assert res.rank == i + 1

    def test_threshold_filtering(self, sample_products):
        matcher = ProductMatcher(default_threshold=0.50)
        response = matcher.match_products("paneer", sample_products, threshold=0.50, include_unmatched=True)

        matched_results = [r for r in response.results if r.match_status == "matched"]
        low_confidence_results = [
            r for r in response.results if r.match_status == "low_confidence"
        ]

        assert len(matched_results) >= 2
        for r in matched_results:
            assert r.similarity_score >= 0.50

        for r in low_confidence_results:
            assert r.similarity_score < 0.50

    def test_empty_ingredient_and_empty_products(self, sample_products):
        matcher = ProductMatcher()

        res_empty_ing = matcher.match_products("", sample_products)
        assert res_empty_ing.total_matches == 0
        assert len(res_empty_ing.results) == 0

        res_empty_prods = matcher.match_products("paneer", [])
        assert res_empty_prods.total_matches == 0
        assert len(res_empty_prods.results) == 0

    def test_invalid_product_objects_handled_safely(self):
        matcher = ProductMatcher()
        invalid_prods = [
            {"product_name": ""},
            {"product_name": "   "},
            {"random_key": 123},
        ]
        response = matcher.match_products("paneer", invalid_prods)
        assert len(response.results) == 0
