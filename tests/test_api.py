from backend.llm import Decision
from backend.schemas import Action
from backend.routers import tickets as tickets_router
from tests.conftest import client


def fake_decision(subject: str, description: str) -> Decision:
    return Decision(action=Action.REQUEST_MORE_INFORMATION, confidence=0.8, reason="Please provide the order number.", sources=["returns.md"])


def test_register_login_and_me():
    response = client.post("/auth/register", json={"email": "one@example.com", "password": "password123"})
    assert response.status_code == 201
    login = client.post("/auth/login", data={"username": "one@example.com", "password": "password123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "one@example.com"


def test_ticket_creation_and_history(monkeypatch):
    monkeypatch.setattr(tickets_router, "decide_ticket", fake_decision)
    client.post("/auth/register", json={"email": "two@example.com", "password": "password123"})
    token = client.post("/auth/login", data={"username": "two@example.com", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/tickets", headers=headers, json={"subject": "Need help", "description": "I need help with my order number."})
    assert created.status_code == 201
    assert created.json()["decision"]["action"] == "REQUEST_MORE_INFORMATION"
    assert len(client.get("/tickets", headers=headers).json()) == 1


def test_users_cannot_access_each_others_tickets(monkeypatch):
    monkeypatch.setattr(tickets_router, "decide_ticket", fake_decision)
    client.post("/auth/register", json={"email": "three@example.com", "password": "password123"})
    first_token = client.post("/auth/login", data={"username": "three@example.com", "password": "password123"}).json()["access_token"]
    ticket = client.post("/tickets", headers={"Authorization": f"Bearer {first_token}"}, json={"subject": "Private", "description": "This ticket belongs to the first user."}).json()
    client.post("/auth/register", json={"email": "four@example.com", "password": "password123"})
    second_token = client.post("/auth/login", data={"username": "four@example.com", "password": "password123"}).json()["access_token"]
    response = client.get(f"/tickets/{ticket['id']}", headers={"Authorization": f"Bearer {second_token}"})
    assert response.status_code == 404
