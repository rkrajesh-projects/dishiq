import logging
from typing import Dict
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.recipe import Recipe, Ingredient, RecipeIngredient
from app.models.grocery import GroceryStore, GroceryProduct, ProductPrice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dishiq.seed")


INGREDIENT_SEED_DATA = [
    {"canonical_name": "paneer", "category": "Dairy", "default_unit": "grams"},
    {"canonical_name": "tomato", "category": "Produce", "default_unit": "pieces"},
    {"canonical_name": "onion", "category": "Produce", "default_unit": "pieces"},
    {"canonical_name": "green chili", "category": "Produce", "default_unit": "pieces"},
    {"canonical_name": "coriander", "category": "Produce", "default_unit": "bunch"},
    {"canonical_name": "butter", "category": "Dairy", "default_unit": "grams"},
    {"canonical_name": "toor dal", "category": "Grains & Pulses", "default_unit": "grams"},
    {"canonical_name": "cumin seeds", "category": "Spices", "default_unit": "teaspoon"},
    {"canonical_name": "turmeric powder", "category": "Spices", "default_unit": "teaspoon"},
    {"canonical_name": "garam masala", "category": "Spices", "default_unit": "teaspoon"},
    {"canonical_name": "basmati rice", "category": "Grains & Pulses", "default_unit": "grams"},
    {"canonical_name": "ginger", "category": "Produce", "default_unit": "grams"},
    {"canonical_name": "garlic", "category": "Produce", "default_unit": "cloves"},
    {"canonical_name": "chicken breast", "category": "Meat", "default_unit": "grams"},
    {"canonical_name": "heavy cream", "category": "Dairy", "default_unit": "ml"},
    {"canonical_name": "chana", "category": "Grains & Pulses", "default_unit": "grams"},
    {"canonical_name": "spinach", "category": "Produce", "default_unit": "grams"},
    {"canonical_name": "potato", "category": "Produce", "default_unit": "pieces"},
    {"canonical_name": "cauliflower", "category": "Produce", "default_unit": "head"},
    {"canonical_name": "rice batter", "category": "Grains & Pulses", "default_unit": "ml"},
    {"canonical_name": "egg", "category": "Poultry", "default_unit": "pieces"},
    {"canonical_name": "cooking oil", "category": "Oils", "default_unit": "ml"},
    {"canonical_name": "mustard seeds", "category": "Spices", "default_unit": "teaspoon"},
    {"canonical_name": "red chili powder", "category": "Spices", "default_unit": "teaspoon"},
    {"canonical_name": "salt", "category": "Spices", "default_unit": "teaspoon"},
    {"canonical_name": "pasta", "category": "Grains & Pulses", "default_unit": "grams"},
    {"canonical_name": "olive oil", "category": "Oils", "default_unit": "ml"},
    {"canonical_name": "cucumber", "category": "Produce", "default_unit": "pieces"},
    {"canonical_name": "feta cheese", "category": "Dairy", "default_unit": "grams"},
    {"canonical_name": "tortilla", "category": "Grains & Pulses", "default_unit": "pieces"},
    {"canonical_name": "bell pepper", "category": "Produce", "default_unit": "pieces"},
    {"canonical_name": "soy sauce", "category": "Condiments", "default_unit": "tbsp"},
    {"canonical_name": "carrot", "category": "Produce", "default_unit": "pieces"},
    {"canonical_name": "peas", "category": "Produce", "default_unit": "grams"},
    {"canonical_name": "lemon", "category": "Produce", "default_unit": "pieces"},
    {"canonical_name": "curd", "category": "Dairy", "default_unit": "grams"},
    {"canonical_name": "cashews", "category": "Nuts & Seeds", "default_unit": "grams"},
    {"canonical_name": "coriander powder", "category": "Spices", "default_unit": "teaspoon"},
    {"canonical_name": "black pepper", "category": "Spices", "default_unit": "teaspoon"},
    {"canonical_name": "kasuri methi", "category": "Spices", "default_unit": "teaspoon"},
]

RECIPE_SEED_DATA = [
    {
        "name": "Paneer Bhurji",
        "description": "Scrambled cottage cheese cooked with chopped onions, tomatoes, and aromatic Indian spices.",
        "cuisine": "Indian",
        "dietary_type": "Vegetarian",
        "preparation_minutes": 10,
        "cooking_minutes": 15,
        "servings": 4,
        "instructions": [
            "Crumble paneer finely in a bowl.",
            "Heat oil and butter in a pan, add cumin seeds and green chilies.",
            "Sauté onions until golden brown, then add ginger-garlic paste and chopped tomatoes.",
            "Add turmeric, red chili powder, and salt. Cook until tomatoes turn soft.",
            "Add crumbled paneer, mix gently, and cook for 3-4 minutes.",
            "Garnish with fresh chopped coriander and serve hot with rotis."
        ],
        "ingredients": [
            {"canonical": "paneer", "quantity": 250, "unit": "grams", "raw": "250g crumbled paneer"},
            {"canonical": "onion", "quantity": 2, "unit": "pieces", "raw": "2 finely chopped onions"},
            {"canonical": "tomato", "quantity": 2, "unit": "pieces", "raw": "2 chopped tomatoes"},
            {"canonical": "green chili", "quantity": 2, "unit": "pieces", "raw": "2 slit green chilies"},
            {"canonical": "coriander", "quantity": 1, "unit": "bunch", "raw": "1 bunch fresh coriander leaves"},
            {"canonical": "butter", "quantity": 20, "unit": "grams", "raw": "20g butter"},
            {"canonical": "cumin seeds", "quantity": 1, "unit": "teaspoon", "raw": "1 tsp cumin seeds"},
        ]
    },
    {
        "name": "Dal Tadka",
        "description": "Comforting yellow lentil soup tempered with cumin seeds, garlic, and ghee.",
        "cuisine": "Indian",
        "dietary_type": "Vegetarian",
        "preparation_minutes": 10,
        "cooking_minutes": 20,
        "servings": 4,
        "instructions": [
            "Pressure cook toor dal with turmeric and water until soft.",
            "Heat ghee or oil in a pan, add cumin seeds, garlic cloves, and green chilies.",
            "Pour hot tempering over the cooked dal and stir well.",
            "Garnish with coriander and serve with rice."
        ],
        "ingredients": [
            {"canonical": "toor dal", "quantity": 200, "unit": "grams", "raw": "200g yellow toor dal"},
            {"canonical": "garlic", "quantity": 5, "unit": "cloves", "raw": "5 crushed garlic cloves"},
            {"canonical": "cumin seeds", "quantity": 1, "unit": "teaspoon", "raw": "1 tsp cumin seeds"},
            {"canonical": "turmeric powder", "quantity": 0.5, "unit": "teaspoon", "raw": "1/2 tsp turmeric powder"},
        ]
    },
    {
        "name": "Vegetable Biryani",
        "description": "Fragrant basmati rice layered with spiced vegetables and herbs.",
        "cuisine": "Indian",
        "dietary_type": "Vegetarian",
        "preparation_minutes": 20,
        "cooking_minutes": 30,
        "servings": 6,
        "instructions": [
            "Soak basmati rice for 30 minutes and boil until 80% done.",
            "Sauté chopped vegetables with biryani spices and curd.",
            "Layer rice over vegetables, cover, and dum cook on low heat for 15 minutes."
        ],
        "ingredients": [
            {"canonical": "basmati rice", "quantity": 400, "unit": "grams", "raw": "400g aged basmati rice"},
            {"canonical": "potato", "quantity": 2, "unit": "pieces", "raw": "2 cubed potatoes"},
            {"canonical": "carrot", "quantity": 2, "unit": "pieces", "raw": "2 diced carrots"},
            {"canonical": "peas", "quantity": 100, "unit": "grams", "raw": "100g green peas"},
            {"canonical": "curd", "quantity": 100, "unit": "grams", "raw": "100g plain curd"},
        ]
    },
    {
        "name": "Butter Chicken",
        "description": "Tender chicken cooked in a rich, velvety tomato and butter cream sauce.",
        "cuisine": "Indian",
        "dietary_type": "Non-Vegetarian",
        "preparation_minutes": 20,
        "cooking_minutes": 25,
        "servings": 4,
        "instructions": [
            "Marinate chicken with curd and spices, then grill until lightly charred.",
            "Prepare tomato gravy with butter, cream, and kasuri methi.",
            "Simmer chicken in gravy for 10 minutes until creamy."
        ],
        "ingredients": [
            {"canonical": "chicken breast", "quantity": 500, "unit": "grams", "raw": "500g boneless chicken breast"},
            {"canonical": "butter", "quantity": 50, "unit": "grams", "raw": "50g unsalted butter"},
            {"canonical": "heavy cream", "quantity": 100, "unit": "ml", "raw": "100ml heavy cream"},
            {"canonical": "tomato", "quantity": 4, "unit": "pieces", "raw": "4 pureed tomatoes"},
            {"canonical": "kasuri methi", "quantity": 1, "unit": "teaspoon", "raw": "1 tsp kasuri methi"},
        ]
    },
    {
        "name": "Chana Masala",
        "description": "Zesty chickpea curry cooked with onion, tomato, and aromatic chana spices.",
        "cuisine": "Indian",
        "dietary_type": "Vegan",
        "preparation_minutes": 15,
        "cooking_minutes": 25,
        "servings": 4,
        "instructions": [
            "Soak and boil chickpeas until tender.",
            "Sauté onions, ginger, garlic, and tomato puree with ground spices.",
            "Add chickpeas and simmer for 15 minutes."
        ],
        "ingredients": [
            {"canonical": "chana", "quantity": 250, "unit": "grams", "raw": "250g white chickpeas"},
            {"canonical": "onion", "quantity": 2, "unit": "pieces", "raw": "2 chopped onions"},
            {"canonical": "tomato", "quantity": 2, "unit": "pieces", "raw": "2 tomato purees"},
            {"canonical": "coriander powder", "quantity": 1, "unit": "teaspoon", "raw": "1 tsp coriander powder"},
        ]
    },
    {
        "name": "Palak Paneer",
        "description": "Soft paneer cubes simmered in a smooth, spiced spinach puree.",
        "cuisine": "Indian",
        "dietary_type": "Vegetarian",
        "preparation_minutes": 15,
        "cooking_minutes": 20,
        "servings": 4,
        "instructions": [
            "Blanch spinach leaves and puree with green chili.",
            "Sauté garlic and onions, add spinach puree and spices.",
            "Add paneer cubes and simmer gently for 5 minutes."
        ],
        "ingredients": [
            {"canonical": "paneer", "quantity": 200, "unit": "grams", "raw": "200g paneer cubes"},
            {"canonical": "spinach", "quantity": 300, "unit": "grams", "raw": "300g fresh spinach"},
            {"canonical": "garlic", "quantity": 4, "unit": "cloves", "raw": "4 garlic cloves"},
            {"canonical": "heavy cream", "quantity": 30, "unit": "ml", "raw": "30ml fresh cream"},
        ]
    },
    {
        "name": "Aloo Gobi",
        "description": "Classic dry North Indian dish made with potatoes, cauliflower, and spices.",
        "cuisine": "Indian",
        "dietary_type": "Vegan",
        "preparation_minutes": 15,
        "cooking_minutes": 20,
        "servings": 4,
        "instructions": [
            "Cut potatoes and cauliflower florets.",
            "Heat oil, add cumin seeds, ginger, turmeric, and vegetables.",
            "Cover and cook on low heat until tender."
        ],
        "ingredients": [
            {"canonical": "potato", "quantity": 2, "unit": "pieces", "raw": "2 medium potatoes"},
            {"canonical": "cauliflower", "quantity": 1, "unit": "head", "raw": "1 medium cauliflower head"},
            {"canonical": "turmeric powder", "quantity": 1, "unit": "teaspoon", "raw": "1 tsp turmeric powder"},
        ]
    },
    {
        "name": "Masala Dosa",
        "description": "Crispy fermented rice crepe filled with spiced potato masala.",
        "cuisine": "South Indian",
        "dietary_type": "Vegan",
        "preparation_minutes": 10,
        "cooking_minutes": 15,
        "servings": 2,
        "instructions": [
            "Prepare potato masala with mustard seeds, curry leaves, and turmeric.",
            "Spread rice batter thinly on a hot tawa, drizzle oil, cook until golden.",
            "Place potato filling in center, fold, and serve with chutney."
        ],
        "ingredients": [
            {"canonical": "rice batter", "quantity": 300, "unit": "ml", "raw": "300ml fermented dosa batter"},
            {"canonical": "potato", "quantity": 3, "unit": "pieces", "raw": "3 boiled potatoes"},
            {"canonical": "mustard seeds", "quantity": 1, "unit": "teaspoon", "raw": "1 tsp mustard seeds"},
        ]
    },
    {
        "name": "Egg Curry",
        "description": "Hard-boiled eggs simmered in a spicy onion and tomato gravy.",
        "cuisine": "Indian",
        "dietary_type": "Non-Vegetarian",
        "preparation_minutes": 10,
        "cooking_minutes": 20,
        "servings": 3,
        "instructions": [
            "Hard boil eggs, peel, and lightly fry in oil with turmeric.",
            "Prepare onion tomato masala gravy and add boiled eggs.",
            "Simmer for 8 minutes."
        ],
        "ingredients": [
            {"canonical": "egg", "quantity": 6, "unit": "pieces", "raw": "6 large eggs"},
            {"canonical": "onion", "quantity": 2, "unit": "pieces", "raw": "2 sliced onions"},
            {"canonical": "tomato", "quantity": 2, "unit": "pieces", "raw": "2 chopped tomatoes"},
        ]
    },
    {
        "name": "Chicken Curry",
        "description": "Homestyle rustic chicken curry prepared with garlic, onion, and ground spices.",
        "cuisine": "Indian",
        "dietary_type": "Non-Vegetarian",
        "preparation_minutes": 15,
        "cooking_minutes": 30,
        "servings": 4,
        "instructions": [
            "Heat oil in a heavy pot, add whole spices and chopped onions.",
            "Add chicken pieces, ginger-garlic paste, and powdered spices.",
            "Add water and cook covered for 25 minutes."
        ],
        "ingredients": [
            {"canonical": "chicken breast", "quantity": 600, "unit": "grams", "raw": "600g chicken pieces"},
            {"canonical": "onion", "quantity": 3, "unit": "pieces", "raw": "3 chopped onions"},
            {"canonical": "cooking oil", "quantity": 30, "unit": "ml", "raw": "30ml oil"},
        ]
    },
    {
        "name": "Vegetable Pasta",
        "description": "Penne pasta tossed in olive oil with bell peppers, tomatoes, and herbs.",
        "cuisine": "Italian",
        "dietary_type": "Vegetarian",
        "preparation_minutes": 10,
        "cooking_minutes": 15,
        "servings": 3,
        "instructions": [
            "Boil pasta until al dente.",
            "Sauté garlic and bell peppers in olive oil.",
            "Toss pasta with sautéed vegetables, salt, and black pepper."
        ],
        "ingredients": [
            {"canonical": "pasta", "quantity": 250, "unit": "grams", "raw": "250g penne pasta"},
            {"canonical": "bell pepper", "quantity": 2, "unit": "pieces", "raw": "2 sliced bell peppers"},
            {"canonical": "olive oil", "quantity": 25, "unit": "ml", "raw": "25ml olive oil"},
            {"canonical": "black pepper", "quantity": 1, "unit": "teaspoon", "raw": "1 tsp black pepper"},
        ]
    },
    {
        "name": "Greek Salad",
        "description": "Refreshing salad with crisp cucumbers, tomatoes, bell peppers, and feta cheese.",
        "cuisine": "Mediterranean",
        "dietary_type": "Vegetarian",
        "preparation_minutes": 10,
        "cooking_minutes": 0,
        "servings": 2,
        "instructions": [
            "Chop tomatoes, cucumbers, and bell peppers into bite-sized cubes.",
            "Toss in a bowl with olive oil, lemon juice, and crumbled feta cheese."
        ],
        "ingredients": [
            {"canonical": "cucumber", "quantity": 1, "unit": "pieces", "raw": "1 English cucumber"},
            {"canonical": "tomato", "quantity": 2, "unit": "pieces", "raw": "2 ripe tomatoes"},
            {"canonical": "feta cheese", "quantity": 100, "unit": "grams", "raw": "100g feta cheese"},
            {"canonical": "lemon", "quantity": 1, "unit": "pieces", "raw": "1 lemon juice"},
        ]
    },
    {
        "name": "Veggie Tacos",
        "description": "Warm tortillas stuffed with seasoned beans, peppers, onions, and fresh salsa.",
        "cuisine": "Mexican",
        "dietary_type": "Vegan",
        "preparation_minutes": 15,
        "cooking_minutes": 10,
        "servings": 4,
        "instructions": [
            "Sauté bell peppers, onions, and spices.",
            "Warm tortillas on pan.",
            "Fill tortillas with sautéed veggies and top with chopped coriander."
        ],
        "ingredients": [
            {"canonical": "tortilla", "quantity": 8, "unit": "pieces", "raw": "8 corn tortillas"},
            {"canonical": "bell pepper", "quantity": 2, "unit": "pieces", "raw": "2 bell peppers"},
            {"canonical": "onion", "quantity": 1, "unit": "pieces", "raw": "1 red onion"},
        ]
    },
    {
        "name": "Vegetable Fried Rice",
        "description": "Wok-fried rice with finely chopped carrots, peas, and soy sauce.",
        "cuisine": "Asian",
        "dietary_type": "Vegan",
        "preparation_minutes": 15,
        "cooking_minutes": 10,
        "servings": 3,
        "instructions": [
            "Stir-fry chopped garlic, carrots, and peas on high heat.",
            "Add cooked cold rice and soy sauce, toss quickly for 3 minutes."
        ],
        "ingredients": [
            {"canonical": "basmati rice", "quantity": 300, "unit": "grams", "raw": "300g cooked rice"},
            {"canonical": "carrot", "quantity": 1, "unit": "pieces", "raw": "1 finely diced carrot"},
            {"canonical": "peas", "quantity": 50, "unit": "grams", "raw": "50g green peas"},
            {"canonical": "soy sauce", "quantity": 2, "unit": "tbsp", "raw": "2 tbsp dark soy sauce"},
        ]
    },
    {
        "name": "Classic Tomato Soup",
        "description": "Smooth and velvety tomato soup seasoned with garlic and fresh herbs.",
        "cuisine": "Continental",
        "dietary_type": "Vegetarian",
        "preparation_minutes": 10,
        "cooking_minutes": 20,
        "servings": 4,
        "instructions": [
            "Roast tomatoes, onions, and garlic in butter.",
            "Blend until smooth, strain, and bring to boil with cream and pepper."
        ],
        "ingredients": [
            {"canonical": "tomato", "quantity": 6, "unit": "pieces", "raw": "6 ripe tomatoes"},
            {"canonical": "butter", "quantity": 20, "unit": "grams", "raw": "20g butter"},
            {"canonical": "heavy cream", "quantity": 50, "unit": "ml", "raw": "50ml fresh cream"},
        ]
    }
]

DEMO_STORES = [
    {"name": "Demo QuickMart", "store_type": "Convenience Supermarket", "city": "Demo City", "is_demo_store": True},
    {"name": "Demo FreshBasket", "store_type": "Organic Fresh Market", "city": "Demo City", "is_demo_store": True},
    {"name": "Demo LocalGrocer", "store_type": "Neighborhood Grocery", "city": "Demo City", "is_demo_store": True},
]

# ---------------------------------------------------------------
# Base product templates with realistic Indian Rupee (INR) prices
# Columns: (display_name, canonical_name, brand, qty, unit, category, base_price_inr)
# ---------------------------------------------------------------
base_product_templates = [
    ("Fresh Paneer 200g",            "paneer",           "Amul",           200.0, "grams",  "Dairy",             95.00),
    ("Organic Malai Paneer 250g",    "paneer",           "Mother Dairy",   250.0, "grams",  "Dairy",            115.00),
    ("Roma Tomatoes 1kg",            "tomato",           "Fresh Farm",       1.0, "kg",     "Produce",           40.00),
    ("Organic Red Tomatoes 500g",    "tomato",           "Organic Choice", 500.0, "grams",  "Produce",           25.00),
    ("Yellow Onions 1kg",            "onion",            "Generic",          1.0, "kg",     "Produce",           35.00),
    ("Red Onions 500g",              "onion",            "Farm Select",    500.0, "grams",  "Produce",           20.00),
    ("Green Chilies Bunch 100g",     "green chili",      "Fresh Harvest",  100.0, "grams",  "Produce",           15.00),
    ("Fresh Coriander Bunch",        "coriander",        "Local Farm",       1.0, "bunch",  "Produce",           10.00),
    ("Unsalted Butter 200g",         "butter",           "Amul",           200.0, "grams",  "Dairy",             58.00),
    ("Salted Cooking Butter 500g",   "butter",           "Britannia",      500.0, "grams",  "Dairy",            130.00),
    ("Yellow Toor Dal 1kg",          "toor dal",         "Tata Sampann",     1.0, "kg",     "Grains & Pulses",  120.00),
    ("Organic Arhar Dal 500g",       "toor dal",         "Organic India",  500.0, "grams",  "Grains & Pulses",   70.00),
    ("Cumin Seeds 100g",             "cumin seeds",      "Catch",          100.0, "grams",  "Spices",            45.00),
    ("Turmeric Powder 200g",         "turmeric powder",  "MDH",            200.0, "grams",  "Spices",            55.00),
    ("Garam Masala 100g",            "garam masala",     "Everest",        100.0, "grams",  "Spices",            65.00),
    ("Royal Basmati Rice 1kg",       "basmati rice",     "India Gate",       1.0, "kg",     "Grains & Pulses",   72.00),
    ("Aged Basmati Rice 5kg",        "basmati rice",     "Daawat",           5.0, "kg",     "Grains & Pulses",  340.00),
    ("Fresh Ginger Root 250g",       "ginger",           "Fresh Produce",  250.0, "grams",  "Produce",           30.00),
    ("Garlic Bulb Pack 200g",        "garlic",           "Fresh Produce",  200.0, "grams",  "Produce",           38.00),
    ("Boneless Chicken Breast 500g", "chicken breast",   "Fresh Meat",     500.0, "grams",  "Meat",             175.00),
    ("Organic Chicken Cut 1kg",      "chicken breast",   "Farm Fresh",       1.0, "kg",     "Meat",             320.00),
    ("Heavy Whipping Cream 250ml",   "heavy cream",      "Amul",           250.0, "ml",     "Dairy",             68.00),
    ("Kabuli Chana 1kg",             "chana",            "Tata Sampann",     1.0, "kg",     "Grains & Pulses",   95.00),
    ("Fresh Spinach Bunch 300g",     "spinach",          "Local Green",    300.0, "grams",  "Produce",           25.00),
    ("Russet Potatoes 2kg",          "potato",           "Farm Select",      2.0, "kg",     "Produce",           50.00),
    ("Fresh Cauliflower Head",       "cauliflower",      "Fresh Produce",    1.0, "head",   "Produce",           40.00),
    ("Fermented Dosa Batter 1L",     "rice batter",      "iD Fresh",         1.0, "liter",  "Grains & Pulses",   55.00),
    ("Large Farm Eggs 12 Pack",      "egg",              "Suguna",          12.0, "pieces", "Poultry",           92.00),
    ("Cage Free Eggs 6 Pack",        "egg",              "Country Delight",  6.0, "pieces", "Poultry",           52.00),
    ("Sunflower Cooking Oil 1L",     "cooking oil",      "Fortune",          1.0, "liter",  "Oils",             165.00),
    ("Black Mustard Seeds 100g",     "mustard seeds",    "Catch",          100.0, "grams",  "Spices",            28.00),
    ("Kashmiri Red Chili Powder 100g","red chili powder","MDH",            100.0, "grams",  "Spices",            48.00),
    ("Iodized Salt 1kg",             "salt",             "Tata",             1.0, "kg",     "Spices",            22.00),
    ("Penne Rigate Pasta 500g",      "pasta",            "Barilla",        500.0, "grams",  "Grains & Pulses",  120.00),
]


def seed_database(db: Session) -> None:
    logger.info("Starting database seed routine...")

    # 1. Seed Ingredients (40 items)
    ingredient_map: Dict[str, Ingredient] = {}
    for ing_data in INGREDIENT_SEED_DATA:
        existing = db.query(Ingredient).filter_by(canonical_name=ing_data["canonical_name"]).first()
        if not existing:
            existing = Ingredient(
                canonical_name=ing_data["canonical_name"],
                category=ing_data["category"],
                default_unit=ing_data["default_unit"]
            )
            db.add(existing)
            db.flush()
        ingredient_map[ing_data["canonical_name"]] = existing

    # 2. Seed Recipes (15 items)
    for rec_data in RECIPE_SEED_DATA:
        existing_recipe = db.query(Recipe).filter_by(name=rec_data["name"]).first()
        if not existing_recipe:
            existing_recipe = Recipe(
                name=rec_data["name"],
                description=rec_data["description"],
                cuisine=rec_data["cuisine"],
                dietary_type=rec_data["dietary_type"],
                preparation_minutes=rec_data["preparation_minutes"],
                cooking_minutes=rec_data["cooking_minutes"],
                servings=rec_data["servings"],
                instructions=rec_data["instructions"],
                source_name="DishIQ Demonstration Data",
                average_rating=4.7
            )
            db.add(existing_recipe)
            db.flush()

            # Add recipe ingredients
            for ing_item in rec_data["ingredients"]:
                canonical_name = ing_item["canonical"]
                ing_obj = ingredient_map.get(canonical_name)
                if ing_obj:
                    rec_ing = RecipeIngredient(
                        recipe_id=existing_recipe.id,
                        ingredient_id=ing_obj.id,
                        raw_text=ing_item["raw"],
                        quantity=ing_item["quantity"],
                        unit=ing_item["unit"],
                        preparation_note="fresh"
                    )
                    db.add(rec_ing)

    # 3. Seed Grocery Stores (3 items)
    store_map: Dict[str, GroceryStore] = {}
    for store_data in DEMO_STORES:
        existing_store = db.query(GroceryStore).filter_by(name=store_data["name"]).first()
        if not existing_store:
            existing_store = GroceryStore(
                name=store_data["name"],
                store_type=store_data["store_type"],
                city=store_data["city"],
                is_demo_store=True
            )
            db.add(existing_store)
            db.flush()
        store_map[store_data["name"]] = existing_store

    # 4. Seed Grocery Products with realistic INR prices
    # QuickMart: base INR price
    # FreshBasket: +15% premium (organic market)
    # LocalGrocer: -5% discount (neighborhood grocery)
    store_price_multipliers = {
        "Demo QuickMart":    1.00,
        "Demo FreshBasket":  1.15,
        "Demo LocalGrocer":  0.95,
    }
    # Delivery fee in INR: FreshBasket charges ₹30, others free
    store_delivery_fees = {
        "Demo QuickMart":   0.00,
        "Demo FreshBasket": 30.00,
        "Demo LocalGrocer": 0.00,
    }

    product_count = 0
    for store_name, store_obj in store_map.items():
        multiplier = store_price_multipliers.get(store_name, 1.0)
        delivery_fee = store_delivery_fees.get(store_name, 0.0)

        for item in base_product_templates:
            p_name, c_name, brand, qty, unit, cat, base_p = item

            # Unique product name per store
            store_p_name = f"{store_name} {p_name}"
            existing_prod = db.query(GroceryProduct).filter_by(store_id=store_obj.id, name=store_p_name).first()

            if not existing_prod:
                existing_prod = GroceryProduct(
                    store_id=store_obj.id,
                    name=store_p_name,
                    normalized_name=p_name.lower(),
                    brand=brand,
                    package_quantity=qty,
                    package_unit=unit,
                    category=cat,
                    in_stock=True
                )
                db.add(existing_prod)
                db.flush()

                # Demonstration price in INR
                computed_price = round(base_p * multiplier, 2)
                price_rec = ProductPrice(
                    product_id=existing_prod.id,
                    price=computed_price,
                    delivery_fee=delivery_fee,
                    data_source_type="demo"
                )
                db.add(price_rec)

            product_count += 1

    db.commit()
    logger.info(
        f"Seeding completed successfully! "
        f"Recipes: {db.query(Recipe).count()}, "
        f"Ingredients: {db.query(Ingredient).count()}, "
        f"Stores: {db.query(GroceryStore).count()}, "
        f"Products: {db.query(GroceryProduct).count()} "
        f"(All prices in INR)"
    )


if __name__ == "__main__":
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        seed_database(db)
    finally:
        db.close()
