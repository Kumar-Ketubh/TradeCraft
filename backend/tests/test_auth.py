# backend/tests/test_auth.py

def test_register_user_success(client):
    response = client.post(
        "/auth/register",
        json={"name": "Alice Innovator", "email": "alice@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["name"] == "Alice Innovator"

def test_register_duplicate_email(client):
    client.post(
        "/auth/register",
        json={"name": "Alice Innovator", "email": "alice@example.com", "password": "securepassword123"},
    )
    response = client.post(
        "/auth/register",
        json={"name": "Alice Clone", "email": "alice@example.com", "password": "anotherpassword"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_login_success(client):
    client.post(
        "/auth/register",
        json={"name": "Bob Builder", "email": "bob@example.com", "password": "password123"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "bob@example.com"

def test_login_invalid_password(client):
    client.post(
        "/auth/register",
        json={"name": "Bob Builder", "email": "bob@example.com", "password": "password123"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

def test_get_me_authenticated(client):
    reg = client.post(
        "/auth/register",
        json={"name": "Carol Creator", "email": "carol@example.com", "password": "password123"},
    ).json()
    token = reg["access_token"]
    
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "carol@example.com"

def test_protected_route_unauthenticated(client):
    response = client.get("/workspaces")
    assert response.status_code == 403 or response.status_code == 401
