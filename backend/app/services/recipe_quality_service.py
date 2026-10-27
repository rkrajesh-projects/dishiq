import re
from typing import List, Dict, Any, Optional
from app.models.recipe import Recipe

EQUIPMENT_KEYWORDS = [
    "oven", "pan", "pot", "skillet", "bowl", "knife", "blender", 
    "whisk", "microwave", "saucepan", "baking sheet", "spatula",
    "crock-pot", "slow cooker", "baking dish"
]

PREPARATION_VERBS = [
    "chop", "dice", "slice", "cut", "peel", "mince", "whisk", "mix",
    "combine", "stir", "blend", "mash", "grate", "pour", "spread", "press", "divide"
]

COOKING_VERBS = [
    "bake", "boil", "fry", "saute", "roast", "simmer", "cook", "brown", "grill", "heat"
]

def extract_timing(text: str) -> Optional[int]:
    text_lower = text.lower()
    
    min_match = re.search(r'(\d+)\s*(?:-|to)?\s*(\d+)?\s*(?:minute|min)s?', text_lower)
    if min_match:
        val1 = int(min_match.group(1))
        val2 = int(min_match.group(2)) if min_match.group(2) else val1
        return (val1 + val2) // 2
        
    hr_match = re.search(r'(\d+)\s*(?:-|to)?\s*(\d+)?\s*(?:hour|hr)s?', text_lower)
    if hr_match:
        val1 = int(hr_match.group(1))
        val2 = int(hr_match.group(2)) if hr_match.group(2) else val1
        return ((val1 + val2) // 2) * 60
        
    return None

def extract_temperature(text: str) -> Optional[str]:
    text_lower = text.lower()
    temp_match = re.search(r'(\d{3})\s*(?:degrees?|degree|\^f|f|c)\b', text_lower)
    if temp_match:
        return temp_match.group(0)
    return None

def determine_action_type(text: str) -> str:
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    
    if any(verb in words for verb in COOKING_VERBS):
        return "cooking"
    if any(verb in words for verb in PREPARATION_VERBS):
        return "preparation"
    return "finishing"

def extract_equipment(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    for eq in EQUIPMENT_KEYWORDS:
        if eq in text_lower:
            found.append(eq)
    return found

class RecipeQualityAnalyzer:
    @staticmethod
    def normalize_instructions(recipe: Recipe) -> bool:
        if not recipe.instructions:
            return False
            
        if isinstance(recipe.instructions[0], dict):
            return False
            
        structured_steps = []
        ingredient_names = []
        if recipe.ingredients:
            ingredient_names = [ing.ingredient.canonical_name.lower() for ing in recipe.ingredients if ing.ingredient]
        
        step_idx = 1
        for step_text in recipe.instructions:
            if not isinstance(step_text, str) or not step_text.strip():
                continue
                
            text = step_text.strip()
            text_lower = text.lower()
            
            associated_ingredients = []
            for ing_name in ingredient_names:
                if ing_name in text_lower and ing_name not in associated_ingredients:
                    associated_ingredients.append(ing_name)
                    
            structured_steps.append({
                "step_number": step_idx,
                "text": text,
                "action_type": determine_action_type(text),
                "timing_minutes": extract_timing(text),
                "temperature": extract_temperature(text),
                "equipment": extract_equipment(text),
                "ingredients": associated_ingredients
            })
            step_idx += 1
            
        recipe.instructions = structured_steps
        return True
