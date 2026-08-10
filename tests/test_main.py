import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _register_and_login():
    client.post(
        "/auth/register",
        json={"name": "Vitor Teste", "email": "vitor.teste@example.com", "password": "senha123"},
    )
    response = client.post(
        "/auth/login",
        data={"username": "vitor.teste@example.com", "password": "senha123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_register_user():
    response = client.post(
        "/auth/register",
        json={"name": "Novo User", "email": "novo.user@example.com", "password": "123456"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "novo.user@example.com"


def test_login_and_create_task():
    headers = _register_and_login()

    response = client.post(
        "/tasks/",
        json={"title": "Estudar Docker", "description": "Concluir curso", "status": "pending"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Estudar Docker"


def test_list_and_update_task():
    headers = _register_and_login()

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


def teardown_module(module):
    if os.path.exists("test.db"):
        os.remove("test.db")
