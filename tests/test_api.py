import sys
from pathlib import Path

# Add root folder to python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

def run_test():
    client = TestClient(app)
    
    print("Testing API Health endpoint...")
    response = client.get("/health")
    assert response.status_code == 200, "Health endpoint failed."
    assert response.json().get("status") == "ok", "Health status payload invalid."
    print("API Health passed.")
    
    print("\nTesting trace retrieval for non-existent session...")
    response = client.get("/trace/empty_session_123")
    assert response.status_code == 200
    assert response.json() == []
    print("Trace endpoint passed.")
    
    print("\nTesting download Markdown error handling for invalid ID...")
    response = client.get("/download/invalid_id_000")
    assert response.status_code == 404, "Invalid ID did not throw 404."
    print("Markdown download error handling passed.")
    
    print("\nAll integration API tests passed successfully!")

if __name__ == "__main__":
    run_test()
