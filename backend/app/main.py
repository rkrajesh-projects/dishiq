from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestLoggingMiddleware, logger
from app.db.session import init_db


def _preload_sentence_transformer() -> None:
    """
    Eagerly load the SentenceTransformer model into the ProductEncoder class-level
    singleton cache during process startup.

    This prevents the model from being loaded (≈7–10 s cold-start) on the very first
    grocery-matching or cart-optimization request, which would otherwise cause the
    frontend's 10-second HTTP timeout to fire.

    The model is loaded exactly ONCE per uvicorn process.  All subsequent calls to
    ProductEncoder.get_model() or get_encoder() will hit the already-populated
    _model_cache and return instantly.
    """
    try:
        from app.product_matching.encoder import ProductEncoder
        model_name = settings.SENTENCE_TRANSFORMER_MODEL
        logger.info(f"Preloading SentenceTransformer model [{model_name}] at startup...")
        ProductEncoder.get_model(model_name)
        logger.info(f"SentenceTransformer [{model_name}] warm and ready.")
    except Exception as exc:  # pragma: no cover
        # Non-fatal: if the model fails to preload, requests will still work —
        # they will just pay the cold-start cost on first use.
        logger.warning(f"SentenceTransformer preload failed (will lazy-load on first request): {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Event Handler.
    Handles database table initialization, ML model warm-up, and startup/shutdown logging.
    """
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in [{settings.ENVIRONMENT}] environment..."
    )
    logger.info(f"Database target: [{settings.DATABASE_URL}]")

    # Initialize database tables and seed data if missing
    init_db()

    # Preload the SentenceTransformer model so the first API request is fast
    _preload_sentence_transformer()

    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_application() -> FastAPI:
    """
    FastAPI Application Factory.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="DishIQ Intelligent Kitchen & Meal Planning API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Register Exception Handlers
    register_exception_handlers(app)

    # Include Main API Router
    app.include_router(api_router, prefix="/api")

    return app


app = create_application()
