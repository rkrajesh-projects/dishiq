import re
from typing import Dict, Any, List


def normalize_text(text: str) -> str:
    """
    Cleans and standardizes raw input text for TF-IDF vectorization.
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def create_recipe_feature_document(recipe_dict: Dict[str, Any]) -> str:
    """
    Combines recipe name, cuisine, dietary type, description, and ingredient list
    into a single normalized document string for TF-IDF feature extraction.
    """
    name = recipe_dict.get("name", "")
    cuisine = recipe_dict.get("cuisine", "")
    dietary_type = recipe_dict.get("dietary_type", "")
    description = recipe_dict.get("description", "")
    
    ingredients: List[str] = []
    for ing in recipe_dict.get("ingredients", []):
        if isinstance(ing, str):
            ingredients.append(ing)
        elif isinstance(ing, dict):
            if "canonical_name" in ing:
                ingredients.append(ing["canonical_name"])
            elif "raw_text" in ing:
                ingredients.append(ing["raw_text"])

    ingredient_str = " ".join(ingredients)

    raw_doc = f"{name} {name} {cuisine} {dietary_type} {description} {ingredient_str}"
    return normalize_text(raw_doc)
