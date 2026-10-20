import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    print("Health check test passed:", data)

def test_get_settings():
    res = client.get("/api/v1/admin/settings")
    assert res.status_code == 200
    data = res.json()
    assert "has_api_key" in data
    print("Settings check test passed:", data)

def test_list_documents():
    res = client.get("/api/v1/admin/documents")
    assert res.status_code == 200
    docs = res.json()
    assert isinstance(docs, list)
    print("List documents test passed. Count:", len(docs))

def test_static_ui():
    res = client.get("/")
    assert res.status_code == 200
    assert "DocuGen AI" in res.text
    print("Static UI test passed.")

if __name__ == "__main__":
    test_health()
    test_get_settings()
    test_list_documents()
    test_static_ui()
    print("ALL TESTS PASSED SUCCESSFULLY! [SUCCESS]")
