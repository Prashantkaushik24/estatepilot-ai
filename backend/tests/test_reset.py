from tests.conftest import import_example


def test_reset_demo_restores_original_data(client, admin):
    base = client.get("/api/v1/dashboard/metrics", headers=admin).json()
    assert import_example(client, admin).status_code == 200
    changed = client.get("/api/v1/dashboard/metrics", headers=admin).json()
    assert changed["total_leads"] == base["total_leads"] + 1 and changed["emails_processed"] == 1
    assert client.post("/api/v1/admin/reset-demo", headers=admin, json={}).status_code == 400
    assert client.post("/api/v1/admin/reset-demo", headers=admin, json={"confirm": True}).status_code == 200
    after = client.get("/api/v1/dashboard/metrics", headers=admin).json()
    assert after["total_leads"] == base["total_leads"] and after["emails_processed"] == 0
    assert len(client.get("/api/v1/properties", headers=admin).json()["items"]) == 8
    # same email can be imported again after reset
    assert import_example(client, admin).status_code == 200


def test_reset_demo_admin_only(client, agent, manager):
    for h in (agent, manager):
        assert client.post("/api/v1/admin/reset-demo", headers=h, json={"confirm": True}).status_code == 403
