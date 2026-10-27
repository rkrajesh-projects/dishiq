import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger
from app.db.base import Base

database_url = settings.DATABASE_URL

connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

if database_url.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initializes database tables on application startup if missing,
    and runs initial data seeding if database is empty.
    """
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            from app.models.recipe import Recipe
            from app.db.seed import seed_database
            if db.query(Recipe).count() == 0:
                logger.info("Empty database detected. Running initial seed routine...")
                seed_database(db)
        except Exception as seed_err:
            logger.warning(f"Automatic database seed check skipped: {seed_err}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional SQLAlchemy session.
    Explicitly rolls back any pending transaction if an unhandled exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
