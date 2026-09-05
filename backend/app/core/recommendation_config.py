from pydantic_settings import BaseSettings, SettingsConfigDict


class RecommendationSettings(BaseSettings):
    """
    Configurable weights for the multi-factor ML recommendation scoring engine.
    """
    base_score: float = 0.50
    cosine_similarity_weight: float = 0.80
    ingredient_overlap_weight: float = 0.25
    dietary_match_weight: float = 0.20
    rating_weight: float = 0.10
    cooking_time_weight: float = 0.15

    model_config = SettingsConfigDict(
        env_prefix="REC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


recommendation_settings = RecommendationSettings()
