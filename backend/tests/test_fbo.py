"""FBO supply endpoints tests (create, list, get, import-barcodes)."""


async def test_fbo_create_wb_with_box_count_without_keys_returns_400(client, auth_headers, unique_inn):
    """Create WB supply with box_count > 0 without API key returns 400."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb", "box_count": 2},
        headers=auth_headers,
    )
    assert create_resp.status_code == 400
    assert "API" in create_resp.json().get("detail", "") or "ключ" in create_resp.json().get("detail", "").lower()


async def test_fbo_create_ozon_with_box_count_without_keys_returns_400(client, auth_headers, unique_inn):
    """Create Ozon supply with box_count > 0 without API keys returns 400."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "ozon", "box_count": 1},
        headers=auth_headers,
    )
    assert create_resp.status_code == 400
    assert "Ozon" in create_resp.json().get("detail", "") or "ключ" in create_resp.json().get("detail", "").lower()


async def test_fbo_create_draft(client, auth_headers, unique_inn):
    """Create FBO supply draft (no box_count, no external API call)."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
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


async def test_fbo_list_and_get(client, auth_headers, unique_inn):
    """List FBO supplies and get by id."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    # WB draft без ключей (Ozon требует Client ID и API Key даже для черновика)
    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200

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
    assert get_resp.json()["marketplace"] == "wb"


async def test_fbo_import_barcodes(client, auth_headers, unique_inn):
    """Import barcodes adds boxes to supply."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
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


async def test_fbo_import_barcodes_validation(client, auth_headers, unique_inn):
    """Import rejects barcode longer than 128 chars."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
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


async def test_fbo_import_barcodes_append_box_numbering(client, auth_headers, unique_inn):
    """Append import continues box_number from existing boxes (no duplicate box_number)."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200
    supply_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/fbo/supplies/{supply_id}/import-barcodes",
        json={"barcodes": ["A1", "A2", "A3"]},
        headers=auth_headers,
    )
    append_resp = await client.post(
        f"/api/v1/fbo/supplies/{supply_id}/import-barcodes",
        json={"barcodes": ["A4", "A5"]},
        headers=auth_headers,
    )
    assert append_resp.status_code == 200
    new_boxes = append_resp.json()["boxes"]
    assert len(new_boxes) == 2
    numbers = sorted(b["box_number"] for b in new_boxes)
    assert numbers == [4, 5], "Append must continue from max(existing box_number)"

    get_resp = await client.get(f"/api/v1/fbo/supplies/{supply_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    all_boxes = sorted(get_resp.json()["boxes"], key=lambda b: b["box_number"])
    assert len(all_boxes) == 5
    assert [b["box_number"] for b in all_boxes] == [1, 2, 3, 4, 5]
    assert [b["external_barcode"] for b in all_boxes] == ["A1", "A2", "A3", "A4", "A5"]


async def test_fbo_import_barcodes_skips_duplicate_in_payload(client, auth_headers, unique_inn):
    """Import with duplicate barcodes in payload adds only one box per unique barcode."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb"},
        headers=auth_headers,
    )
    supply_id = create_resp.json()["id"]

    import_resp = await client.post(
        f"/api/v1/fbo/supplies/{supply_id}/import-barcodes",
        json={"barcodes": ["DUP", "DUP", "DUP"]},
        headers=auth_headers,
    )
    assert import_resp.status_code == 200
    assert len(import_resp.json()["boxes"]) == 1
    assert import_resp.json()["boxes"][0]["external_barcode"] == "DUP"
    assert import_resp.json()["boxes"][0]["box_number"] == 1


async def test_fbo_sync_requires_external_id(client, auth_headers, unique_inn):
    """Sync returns 400 when supply has no external_supply_id."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
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
