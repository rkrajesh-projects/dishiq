import os
import sys

# Ensure repository root is in sys.path for test execution
root_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.seed import seed_database

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_dishiq.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

from sqlalchemy import event

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def seeded_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    seed_database(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(seeded_db):
    from app.models.user import User
    from app.api.deps import get_current_user
    from app.core.security import get_password_hash

    user = seeded_db.query(User).first()
    if not user:
        user = User(
            email="test_user@example.com",
            hashed_password=get_password_hash("testpassword"),
            full_name="Test User",
        )
        seeded_db.add(user)
        seeded_db.commit()
        seeded_db.refresh(user)

    def override_get_db():
        try:
            yield seeded_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
