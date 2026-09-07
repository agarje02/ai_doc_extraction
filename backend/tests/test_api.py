from fastapi.testclient import TestClient

from app.main import app
from app.models.db import init_db

init_db()  # ensure tables exist without relying on lifespan
client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_end_to_end_upload_extract_correct_export():
    files = {
        "file": (
            "invoice.txt",
            b"Invoice Number: INV-77\nTotal Amount: $50.00\n",
            "text/plain",
        )
    }
    up = client.post("/documents", files=files)
    assert up.status_code == 201
    doc_id = up.json()["id"]

    run = client.post(
        "/extractions", json={"document_id": doc_id, "doc_type": "invoice"}
    )
    assert run.status_code == 201
    run_json = run.json()
    run_id = run_json["id"]
    assert run_json["result"]["data"]["invoice_number"] == "INV-77"

    corrected = client.post(
        f"/extractions/{run_id}/corrections",
        json={"field_name": "vendor_name", "value": "ACME"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["result"]["data"]["vendor_name"] == "ACME"

    csv = client.get(f"/extractions/{run_id}/export", params={"format": "csv"})
    assert csv.status_code == 200
    assert "invoice_number" in csv.text


def test_list_schemas_endpoint():
    res = client.get("/schemas")
    assert res.status_code == 200
    keys = {s["key"] for s in res.json()}
    assert {"invoice", "resume", "contract", "generic"} <= keys
