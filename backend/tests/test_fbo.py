"""FBO supply endpoints tests (create, list, get, import-barcodes)."""


async def test_fbo_create_draft(client, auth_headers):
    """Create FBO supply draft (no box_count, no external API call)."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223335"}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert data["company_id"] == company_id
    assert data["marketplace"] == "wb"
    assert data["status"] == "draft"
    assert data["external_supply_id"] is None
    assert data["boxes"] == []


async def test_fbo_list_and_get(client, auth_headers):
    """List FBO supplies and get by id."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223336"}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "ozon"},
        headers=auth_headers,
    )

    list_resp = await client.get(
        f"/api/v1/fbo/supplies?company_id={company_id}&page=1&limit=10",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert len(list_data["items"]) >= 1
    supply_id = list_data["items"][0]["id"]

    get_resp = await client.get(f"/api/v1/fbo/supplies/{supply_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == supply_id
    assert get_resp.json()["marketplace"] == "ozon"


async def test_fbo_import_barcodes(client, auth_headers):
    """Import barcodes adds boxes to supply."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223337"}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200
    supply_id = create_resp.json()["id"]

    import_resp = await client.post(
        f"/api/v1/fbo/supplies/{supply_id}/import-barcodes",
        json={"barcodes": ["BC001", "BC002", "BC003"]},
        headers=auth_headers,
    )
    assert import_resp.status_code == 200
    data = import_resp.json()
    assert len(data["boxes"]) == 3
    boxes = sorted(data["boxes"], key=lambda b: b["box_number"])
    assert boxes[0]["external_barcode"] == "BC001"
    assert boxes[1]["external_barcode"] == "BC002"
    assert boxes[2]["external_barcode"] == "BC003"


async def test_fbo_import_barcodes_validation(client, auth_headers):
    """Import rejects barcode longer than 128 chars."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223338"}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb"},
        headers=auth_headers,
    )
    supply_id = create_resp.json()["id"]

    long_barcode = "x" * 129
    import_resp = await client.post(
        f"/api/v1/fbo/supplies/{supply_id}/import-barcodes",
        json={"barcodes": [long_barcode]},
        headers=auth_headers,
    )
    assert import_resp.status_code == 422


async def test_fbo_sync_requires_external_id(client, auth_headers):
    """Sync returns 400 when supply has no external_supply_id."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223339"}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb"},
        headers=auth_headers,
    )
    supply_id = create_resp.json()["id"]

    sync_resp = await client.post(f"/api/v1/fbo/supplies/{supply_id}/sync", headers=auth_headers)
    assert sync_resp.status_code == 400
    assert "внешнего ID" in sync_resp.json().get("detail", "")
