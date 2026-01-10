from app.models import UserDB
import pytest 

@pytest.fixture(autouse=True)
def _mock_publish(monkeypatch):
    from app import main
    monkeypatch.setattr(main, "publish_payment_created", lambda message: None)

def _create_user(db_session, user_id: int = 1, name: str = "Nathan McCormack"):
    user = UserDB(id=user_id, name=name)
    db_session.add(user)
    db_session.commit()
    return user

def test_create_payment_requires_user(client):
    r = client.post(
        "/api/payments",
        json={
            "user_id": 999,
            "amount_cents": 5000,
            "currency": "EUR",
            "description": "Annual membership",
            "payment_method": "visa",
        },
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"

def test_create_list_get_patch_delete_payment(client, db_session):
    _create_user(db_session, user_id=1)

    # Create
    r = client.post(
        "/api/payments",
        json={
            "user_id": 1,
            "amount_cents": 1299,
            "currency": "EUR",
            "description": "Club fee",
            "payment_method": "stripe",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user_id"] == 1
    assert body["amount_cents"] == 1299
    assert body["currency"] == "EUR"
    assert body["status"] == "pending"
    payment_id = body["id"]

    # List all
    r = client.get("/api/payments")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Get by id
    r = client.get(f"/api/payments/{payment_id}")
    assert r.status_code == 200
    assert r.json()["id"] == payment_id

    # List by user
    r = client.get("/api/users/1/payments")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == payment_id

    # Patch
    r = client.patch(f"/api/payments/{payment_id}", json={"status": "completed"})
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    # Delete
    r = client.delete(f"/api/payments/{payment_id}")
    assert r.status_code == 204

    # Verify removed
    r = client.get(f"/api/payments/{payment_id}")
    assert r.status_code == 404

def test_not_found_cases(client, db_session):
    _create_user(db_session, user_id=1)

    r = client.get("/api/payments/999")
    assert r.status_code == 404

    r = client.patch("/api/payments/999", json={"status": "completed"})
    assert r.status_code == 404

    r = client.delete("/api/payments/999")
    assert r.status_code == 404

def test_validation_errors(client, db_session):
    _create_user(db_session, user_id=1)

    # amount_cents must be >= 1
    r = client.post(
        "/api/payments",
        json={
            "user_id": 1,
            "amount_cents": 0,
            "currency": "EUR",
            "description": "Invalid",
            "payment_method": "visa",
        },
    )
    assert r.status_code == 422

    # currency must be 3 characters
    r = client.post(
        "/api/payments",
        json={
            "user_id": 1,
            "amount_cents": 100,
            "currency": "EU",
            "description": "Invalid",
            "payment_method": "visa",
        },
    )
    assert r.status_code == 422
