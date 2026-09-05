from fastapi import APIRouter
from app.api import health, recipes, stores, products, recommendations, ingredients, grocery, cart, pantry, cooking, profile

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(recipes.router)
api_router.include_router(stores.router)
api_router.include_router(products.router)
api_router.include_router(grocery.router)
api_router.include_router(recommendations.router)
api_router.include_router(ingredients.router)
api_router.include_router(cart.router)
api_router.include_router(pantry.router)
api_router.include_router(cooking.router)
api_router.include_router(profile.router)
