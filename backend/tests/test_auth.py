import pytest
from app.core.security import get_password_hash, verify_password

def test_password_hashing():
    password = "ordinary_password_123!"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert len(hashed) > 0
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_existing_password_hash_verification():
    password = "test_password"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)

def test_registration_and_login(client, seeded_db):
    register_data = {
        "email": "newuser@example.com",
        "password": "securepassword",
        "full_name": "New User"
    }
    r = client.post("/api/auth/register", json=register_data)
    assert r.status_code in (200, 201)
    created_user = r.json()
    assert created_user["email"] == register_data["email"]

    login_data = {
        "username": "newuser@example.com",
        "password": "securepassword"
    }
    r2 = client.post("/api/auth/login", data=login_data)
    assert r2.status_code == 200
    token_data = r2.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
