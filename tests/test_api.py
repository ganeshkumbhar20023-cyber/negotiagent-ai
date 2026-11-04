"""
Integration Tests for FastAPI Backend Endpoints
Tests RFQs, Suppliers, Negotiations, Approvals, POs, and Reports.
"""

def test_health_check_endpoint(client):
    """GET /api/health must return online status and sponsor identity."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "Mahalaxmi" in data["sponsor"]
    assert "Kolhapur" in data["sponsor"]


def test_get_suppliers(client):
    """GET /api/suppliers must return seeded supplier agents."""
    res = client.get("/api/suppliers")
    assert res.status_code == 200
    suppliers = res.json()
    assert len(suppliers) >= 2
    assert suppliers[0]["base_price_per_box"] > 0


def test_get_rfqs(client):
    """GET /api/rfqs must return list of procurement requests."""
    res = client.get("/api/rfqs")
    assert res.status_code == 200
    rfqs = res.json()
    assert len(rfqs) >= 1
    assert rfqs[0]["id"] == "RFQ-TEST-001"


def test_create_rfq_valid(client):
    """POST /api/rfqs must successfully create an RFQ when weights sum to 100%."""
    payload = {
        "category": "Ceramic Glazed Wall Tiles",
        "size": "300x600 mm (Wall Tile)",
        "quantity": 600,
        "budget_ceiling": 210000.0,
        "delivery_deadline": "2026-12-05",
        "quality_grade": "Standard / Commercial",
        "max_breakage": 2.5,
        "weights": {
            "price": 40.0,
            "quality": 30.0,
            "delivery": 20.0,
            "warranty": 10.0
        }
    }
    res = client.post("/api/rfqs", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["quantity"] == 600
    assert data["budget_ceiling"] == 210000.0


def test_create_rfq_invalid_weights(client):
    """POST /api/rfqs must reject submissions if weights do NOT sum to 100%."""
    payload = {
        "category": "Ceramic Glazed Wall Tiles",
        "size": "300x600 mm",
        "quantity": 500,
        "budget_ceiling": 200000.0,
        "delivery_deadline": "2026-12-05",
        "quality_grade": "Standard",
        "max_breakage": 2.0,
        "weights": {
            "price": 40.0,
            "quality": 20.0,
            "delivery": 20.0,
            "warranty": 10.0
        }
    }
    res = client.post("/api/rfqs", json=payload)
    assert res.status_code == 400
    assert "Weights must sum to exactly 100%" in res.json()["detail"]


def test_start_and_get_negotiation(client):
    """POST /api/negotiations/start/{rfq_id} runs 3 rounds and archives transcript."""
    start_res = client.post("/api/negotiations/start/RFQ-TEST-001")
    assert start_res.status_code == 200
    outcome = start_res.json()
    assert outcome["winning_supplier"] is not None
    assert len(outcome["rounds"]) == 6

    hist_res = client.get("/api/negotiations/RFQ-TEST-001")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["rfq_id"] == "RFQ-TEST-001"
    assert len(hist["rounds"]) == 6


def test_human_approval_and_payment_flow(client):
    """Tests approval sign-off, Purchase Order creation, and sandbox payment transition."""
    client.post("/api/negotiations/start/RFQ-TEST-001")

    approve_res = client.post("/api/orders/approve/RFQ-TEST-001")
    assert approve_res.status_code == 200
    approve_data = approve_res.json()
    po_id = approve_data["po_id"]
    assert "PO-" in po_id

    orders_res = client.get("/api/orders")
    assert orders_res.status_code == 200
    orders = orders_res.json()
    matched_po = next((o for o in orders if o["id"] == po_id), None)
    assert matched_po is not None
    assert matched_po["payment_status"] == "PENDING"
    assert matched_po["gst_amount"] > 0

    pay_res = client.post(f"/api/orders/pay/{po_id}?action=success")
    assert pay_res.status_code == 200
    assert pay_res.json()["payment_status"] == "PAID"

    orders_updated = client.get("/api/orders").json()
    final_po = next((o for o in orders_updated if o["id"] == po_id), None)
    assert final_po["payment_status"] == "PAID"


def test_reports_and_csv_export(client):
    """Verifies analytics summary calculation and RFC 4180 CSV export."""
    client.post("/api/negotiations/start/RFQ-TEST-001")
    client.post("/api/orders/approve/RFQ-TEST-001")

    summary_res = client.get("/api/reports/summary")
    assert summary_res.status_code == 200
    s_data = summary_res.json()
    assert s_data["total_rfqs"] >= 1
    assert "total_savings" in s_data
    assert "total_orders" in s_data

    csv_res = client.get("/api/reports/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "RFQ ID" in csv_res.text