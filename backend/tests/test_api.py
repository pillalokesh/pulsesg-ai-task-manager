import bcrypt
from sqlalchemy.exc import OperationalError

from app.db import get_db
from app.main import app
from app.security import jwt_algorithm, verify_password


def register(client, email="user@example.com"):
    return client.post(
        "/api/auth/register",
        json={"fullName": "Example User", "email": email, "password": "password123"},
    )


def auth_header(client, email="user@example.com"):
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def ticket_payload(title="A support issue"):
    return {
        "title": title,
        "description": "Detailed issue description",
        "category": "TECHNICAL",
        "priority": "MEDIUM",
    }


def test_health_and_authentication(client):
    assert client.get("/actuator/health").json() == {"status": "UP"}
    assert client.get("/api/auth/me").status_code == 401
    created = register(client)
    assert created.status_code == 201
    assert created.json()["user"]["fullName"] == "Example User"
    assert (
        client.post(
            "/api/auth/login", json={"email": "user@example.com", "password": "incorrect1"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "user@example.com", "password": "password123"}
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me", headers=auth_header(client)).status_code == 200


def test_profile_and_validation(client):
    register(client)
    headers = auth_header(client)
    updated = client.put("/api/users/me", json={"fullName": "Updated Name"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["fullName"] == "Updated Name"
    assert register(client).status_code == 409
    invalid = client.post("/api/auth/register", json={"email": "bad", "password": "short"})
    assert invalid.status_code == 400


def test_ticket_crud_messages_and_suggestions(client):
    register(client)
    headers = auth_header(client)
    created = client.post("/api/tickets", json=ticket_payload(), headers=headers)
    assert created.status_code == 201
    ticket = created.json()
    assert ticket["status"] == "OPEN"
    assert "createdAt" in ticket and "updatedAt" in ticket
    ticket_id = ticket["id"]
    assert len(client.get("/api/tickets", headers=headers).json()) == 1
    assert (
        client.put(
            f"/api/tickets/{ticket_id}", json={"status": "IN_PROGRESS"}, headers=headers
        ).json()["status"]
        == "IN_PROGRESS"
    )
    unchanged = client.put(f"/api/tickets/{ticket_id}", json={"title": None}, headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["title"] == "A support issue"
    message = client.post(
        f"/api/tickets/{ticket_id}/messages",
        json={"message": "Please investigate"},
        headers=headers,
    )
    assert message.status_code == 201
    assert message.json()["message"] == "Please investigate"
    assert len(client.get(f"/api/tickets/{ticket_id}/messages", headers=headers).json()) == 1
    assert (
        "technical"
        in client.post(f"/api/tickets/{ticket_id}/ai-suggestion", headers=headers).json()[
            "suggestion"
        ]
    )
    assert client.delete(f"/api/tickets/{ticket_id}", headers=headers).status_code == 204
    assert client.get(f"/api/tickets/{ticket_id}", headers=headers).status_code == 404


def test_ticket_ownership_is_enforced(client):
    register(client)
    first_headers = auth_header(client)
    ticket = client.post("/api/tickets", json=ticket_payload(), headers=first_headers).json()
    register(client, "other@example.com")
    second_headers = auth_header(client, "other@example.com")
    assert client.get(f"/api/tickets/{ticket['id']}", headers=second_headers).status_code == 404
    assert (
        client.post(
            f"/api/tickets/{ticket['id']}/messages",
            json={"message": "unauthorized"},
            headers=second_headers,
        ).status_code
        == 404
    )


def test_java_bcrypt_hash_and_jjwt_algorithm_compatibility():
    java_style_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
    java_style_hash = java_style_hash.replace("$2b$", "$2a$", 1)
    assert verify_password("password123", java_style_hash)
    assert jwt_algorithm("s" * 32) == "HS256"
    assert jwt_algorithm("s" * 48) == "HS384"
    assert jwt_algorithm("s" * 64) == "HS512"


def test_health_reports_database_failure(client, monkeypatch):
    class UnavailableDatabase:
        def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("database unavailable"))

    def unavailable_db():
        yield UnavailableDatabase()

    monkeypatch.setitem(app.dependency_overrides, get_db, unavailable_db)
    response = client.get("/actuator/health")
    assert response.status_code == 503
    assert response.json() == {"status": "DOWN"}
