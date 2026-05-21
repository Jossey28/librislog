import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import UserRole


# ── get_profile ──────────────────────────────────────────────────────────────

def test_get_profile_returns_current_user(client: TestClient):
    resp = client.get("/api/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"


# ── get_settings / update_settings (missing settings row) ────────────────────

def test_get_settings_creates_default_when_missing(client: TestClient, session: Session):
    from app.auth import generate_api_key, get_api_key_prefix, get_password_hash, hash_api_key, encrypt_api_key
    from app.models import User, UserRole, ApiKey

    user = User(
        firstname="No",
        lastname="Settings",
        email="no_settings@example.com",
        role=UserRole.user,
        hashed_password=get_password_hash("secret"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    key_plain = generate_api_key()
    session.add(
        ApiKey(
            user_id=user.id,
            key_prefix=get_api_key_prefix(key_plain),
            key_hash=hash_api_key(key_plain),
            key_encrypted=encrypt_api_key(key_plain),
            description="Test",
        )
    )
    session.commit()

    client.headers["X-API-Key"] = key_plain
    resp = client.get("/api/profile/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "en"
    assert data["user_id"] == user.id


def test_update_settings_creates_default_when_missing(client: TestClient, session: Session):
    from app.auth import generate_api_key, get_api_key_prefix, get_password_hash, hash_api_key, encrypt_api_key
    from app.models import User, UserRole, ApiKey

    user = User(
        firstname="No",
        lastname="Settings2",
        email="no_settings2@example.com",
        role=UserRole.user,
        hashed_password=get_password_hash("secret"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    key_plain = generate_api_key()
    session.add(
        ApiKey(
            user_id=user.id,
            key_prefix=get_api_key_prefix(key_plain),
            key_hash=hash_api_key(key_plain),
            key_encrypted=encrypt_api_key(key_plain),
            description="Test",
        )
    )
    session.commit()

    client.headers["X-API-Key"] = key_plain
    resp = client.patch("/api/profile/settings", json={"language": "de"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "de"
    assert data["user_id"] == user.id


# ── reset_data exception handling ────────────────────────────────────────────

def test_reset_data_rolls_back_on_exception(client: TestClient, monkeypatch):
    import app.routers.profile as profile_module

    def fake_delete(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(profile_module, "delete_user_reading_data", fake_delete)

    with pytest.raises(RuntimeError, match="boom"):
        client.post(
            "/api/profile/reset-data",
            json={"confirmation": "DELETE ALL MY DATA"},
        )


# ── delete_own_account exception handling ────────────────────────────────────

def test_delete_account_rolls_back_on_exception(client: TestClient, create_user_with_key, monkeypatch):
    import app.routers.profile as profile_module

    user, key = create_user_with_key(email="delete_me@example.com", role=UserRole.user)
    client.headers["X-API-Key"] = key

    def fake_delete(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(profile_module, "delete_user_account_data", fake_delete)

    with pytest.raises(RuntimeError, match="boom"):
        client.request(
            "DELETE",
            "/api/profile/account",
            json={"confirmation": "DELETE MY ACCOUNT"},
        )


# ── delete_api_key 404 ───────────────────────────────────────────────────────

def test_delete_api_key_not_found(client: TestClient):
    resp = client.delete("/api/profile/api-keys/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "API key not found"
