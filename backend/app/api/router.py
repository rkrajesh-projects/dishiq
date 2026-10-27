from fastapi import APIRouter
from app.api import auth, health, recipes, stores, products, recommendations, ingredients, grocery, cart, pantry, cooking, profile, swiggy_auth, meal_plans, shopping_lists
from app.api.recommendations import ml_router

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(swiggy_auth.router)
api_router.include_router(health.router)
api_router.include_router(recipes.router)
api_router.include_router(stores.router)
api_router.include_router(products.router)
api_router.include_router(grocery.router)
api_router.include_router(recommendations.router)
api_router.include_router(ml_router)
api_router.include_router(ingredients.router)
api_router.include_router(cart.router)
api_router.include_router(pantry.router)
api_router.include_router(cooking.router)
api_router.include_router(profile.router)
api_router.include_router(meal_plans.router)
api_router.include_router(shopping_lists.router)

