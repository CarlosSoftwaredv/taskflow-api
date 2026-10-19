import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from app.auth import totp_code
from app.database import Base, engine
from app.main import app
from app.routers import auth as auth_routes

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def verification_tokens(monkeypatch):
    tokens = []
    monkeypatch.setattr(auth_routes, "send_verification", lambda email, token: tokens.append(token))
    return tokens


def _register_and_login(verification_tokens, email="vitor.teste@example.com"):
    registration = client.post(
        "/auth/register",
        json={"name": "Vitor Teste", "email": email, "password": "SenhaForte123"},
    )
    assert registration.status_code == 201
    assert len(verification_tokens) == 1
    verified = client.post("/auth/email/verify", json={"token": verification_tokens.pop()})
    assert verified.status_code == 200

    response = client.post(
        "/auth/login",
        data={"username": email, "password": "SenhaForte123"},
    )
    assert response.status_code == 200
    setup = client.post("/auth/mfa/setup", json={"token": response.json()["setup_token"]})
    assert setup.status_code == 200
    enabled = client.post(
        "/auth/mfa/enable",
        json={"token": response.json()["setup_token"], "code": totp_code(setup.json()["secret"])},
    )
    assert enabled.status_code == 200
    return {"Authorization": f"Bearer {enabled.json()['access_token']}"}, setup.json()["secret"]


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_register_user(verification_tokens):
    response = client.post(
        "/auth/register",
        json={"name": "Novo User", "email": "novo.user@example.com", "password": "SenhaForte123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "novo.user@example.com"
    assert len(verification_tokens) == 1


def test_register_rejects_weak_password():
    response = client.post(
        "/auth/register",
        json={"name": "Novo User", "email": "novo.user@example.com", "password": "curta123"},
    )
    assert response.status_code == 422


def test_login_and_create_task(verification_tokens):
    headers, _ = _register_and_login(verification_tokens)

    response = client.post(
        "/tasks/",
        json={"title": "Estudar Docker", "description": "Concluir curso", "status": "pending"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Estudar Docker"


def test_list_and_update_task(verification_tokens):
    headers, _ = _register_and_login(verification_tokens)

    create = client.post(
        "/tasks/",
        json={"title": "Revisar PR", "status": "pending"},
        headers=headers,
    )
    task_id = create.json()["id"]

    update = client.put(
        f"/tasks/{task_id}",
        json={"status": "done"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["status"] == "done"

    listing = client.get("/tasks/", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 1


def test_mfa_login(verification_tokens):
    _, secret = _register_and_login(verification_tokens)

    response = client.post(
        "/auth/login",
        data={"username": "vitor.teste@example.com", "password": "SenhaForte123"},
    )
    assert response.status_code == 200
    assert response.json()["requires_mfa"] is True

    verified = client.post(
        "/auth/mfa/verify",
        json={"token": response.json()["challenge_token"], "code": totp_code(secret)},
    )
    assert verified.status_code == 200
    assert verified.json()["access_token"]


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test.db"):
        os.remove("test.db")
