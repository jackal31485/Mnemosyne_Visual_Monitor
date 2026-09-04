import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_browser_page_has_controls():
    resp = client.get("/browser/")
    assert resp.status_code == 200
    # Ensure script file is referenced
    assert "/static/browser.js" in resp.text
    # Verify control pane present
    assert 'id="control-center"' in resp.text
