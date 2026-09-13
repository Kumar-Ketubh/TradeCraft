# backend/tests/test_sources.py

def setup_competitor(client, email="source_user@example.com"):
    res = client.post(
        "/auth/register",
        json={"name": "Source User", "email": email, "password": "password123"},
    ).json()
    headers = {"Authorization": f"Bearer {res['access_token']}"}
    ws = client.post("/workspaces", json={"name": "Tech Market"}, headers=headers).json()
    comp = client.post(
        f"/workspaces/{ws['id']}/competitors",
        json={"name": "OmniCorp", "website": "https://omni.example.com"},
        headers=headers,
    ).json()
    return headers, comp["id"]

def test_sources_crud(client):
    headers, comp_id = setup_competitor(client, "src1@example.com")

    # Create source
    create_res = client.post(
        f"/competitors/{comp_id}/sources",
        json={
            "name": "Pricing Page",
            "url": "https://omni.example.com/pricing",
            "source_type": "pricing",
            "monitoring_enabled": True,
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    src = create_res.json()
    src_id = src["id"]
    assert src["name"] == "Pricing Page"
    assert src["source_type"] == "pricing"

    # List sources
    list_res = client.get(f"/competitors/{comp_id}/sources", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Update source
    up_res = client.put(
        f"/competitors/{comp_id}/sources/{src_id}",
        json={"name": "Updated Pricing Page", "monitoring_enabled": False},
        headers=headers,
    )
    assert up_res.status_code == 200
    assert up_res.json()["name"] == "Updated Pricing Page"
    assert up_res.json()["monitoring_enabled"] is False

    # Delete source
    del_res = client.delete(f"/competitors/{comp_id}/sources/{src_id}", headers=headers)
    assert del_res.status_code == 204

def test_sources_unauthorized(client):
    headers1, comp1_id = setup_competitor(client, "userA@example.com")
    headers2, comp2_id = setup_competitor(client, "userB@example.com")

    src = client.post(
        f"/competitors/{comp1_id}/sources",
        json={"name": "Blog", "url": "https://omni.example.com/blog", "source_type": "blog"},
        headers=headers1,
    ).json()

    # User B cannot access User A's source
    res = client.get(f"/competitors/{comp1_id}/sources/{src['id']}", headers=headers2)
    assert res.status_code == 404
