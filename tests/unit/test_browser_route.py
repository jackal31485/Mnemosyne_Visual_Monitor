# Test for browser route
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
def test_browser_route() -> None:
    resp = client.get("/browser/")
    assert resp.status_code == 200
    assert "Mnemosyne Visual Monitor – Browser" in resp.text
    # ensure divs present
    for div_id in ["control-center", "workspace", "inspector", "status-bar"]:
        assert f'id="{div_id}"' in resp.text, f"missing {div_id}"
