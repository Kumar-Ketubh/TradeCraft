# backend/tests/test_workspaces.py

def get_auth_headers(client, email="user@example.com"):
    res = client.post(
        "/auth/register",
        json={"name": "Test User", "email": email, "password": "password123"},
    ).json()
    return {"Authorization": f"Bearer {res['access_token']}"}

def test_workspace_crud(client):
    headers = get_auth_headers(client, "ws_user@example.com")
    
    # List initial auto-created default workspace
    list_res = client.get("/workspaces", headers=headers)
    assert list_res.status_code == 200
    initial_count = len(list_res.json())
    
    # Create new workspace
    create_res = client.post("/workspaces", json={"name": "SaaS Competitors"}, headers=headers)
    assert create_res.status_code == 201
    ws = create_res.json()
    assert ws["name"] == "SaaS Competitors"
    ws_id = ws["id"]

    # Get single workspace
    get_res = client.get(f"/workspaces/{ws_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "SaaS Competitors"

    # Update workspace
    update_res = client.put(f"/workspaces/{ws_id}", json={"name": "Global Competitors"}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Global Competitors"

    # Delete workspace
    del_res = client.delete(f"/workspaces/{ws_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_del = client.get(f"/workspaces/{ws_id}", headers=headers)
    assert get_del.status_code == 404

def test_workspace_user_isolation(client):
    headers1 = get_auth_headers(client, "user1@example.com")
    headers2 = get_auth_headers(client, "user2@example.com")

    # User 1 creates workspace
    ws1 = client.post("/workspaces", json={"name": "User 1 Private WS"}, headers=headers1).json()
    ws1_id = ws1["id"]

    # User 2 tries to access User 1's workspace
    res = client.get(f"/workspaces/{ws1_id}", headers=headers2)
    assert res.status_code == 404
