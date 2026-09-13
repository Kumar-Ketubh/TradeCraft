# backend/tests/test_competitors.py

def get_user_workspace(client, email="comp_user@example.com"):
    res = client.post(
        "/auth/register",
        json={"name": "Comp User", "email": email, "password": "password123"},
    ).json()
    headers = {"Authorization": f"Bearer {res['access_token']}"}
    ws = client.post("/workspaces", json={"name": "Target Market"}, headers=headers).json()
    return headers, ws["id"]

def test_competitors_crud(client):
    headers, ws_id = get_user_workspace(client, "comp1@example.com")

    # Create competitor
    create_res = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={
            "name": "Acme Corp",
            "description": "Leading manufacturer of tech widgets",
            "website": "https://acme.example.com",
            "monitoring_enabled": True,
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    comp = create_res.json()
    comp_id = comp["id"]
    assert comp["name"] == "Acme Corp"
    assert comp["monitoring_enabled"] is True

    # List competitors
    list_res = client.get(f"/workspaces/{ws_id}/competitors", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Update competitor
    up_res = client.put(
        f"/workspaces/{ws_id}/competitors/{comp_id}",
        json={"name": "Acme Inc.", "monitoring_enabled": False},
        headers=headers,
    )
    assert up_res.status_code == 200
    assert up_res.json()["name"] == "Acme Inc."
    assert up_res.json()["monitoring_enabled"] is False

    # Delete competitor
    del_res = client.delete(f"/workspaces/{ws_id}/competitors/{comp_id}", headers=headers)
    assert del_res.status_code == 204

def test_competitor_isolation(client):
    headers1, ws1_id = get_user_workspace(client, "owner1@example.com")
    headers2, ws2_id = get_user_workspace(client, "owner2@example.com")

    comp1 = client.post(
        f"/workspaces/{ws1_id}/competitors",
        json={"name": "Secret Competitor"},
        headers=headers1,
    ).json()
    comp1_id = comp1["id"]

    # User 2 cannot view User 1 competitor
    res = client.get(f"/workspaces/{ws1_id}/competitors/{comp1_id}", headers=headers2)
    assert res.status_code == 404
