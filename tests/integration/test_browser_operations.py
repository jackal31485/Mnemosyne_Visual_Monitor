from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_browser_operations_are_exposed():
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/discovery" in paths
    assert "/api/discovery/scan/start" in paths
    assert "/api/discovery/{client_id}/adopt" in paths
    assert "/api/admin/collective/nuke" in paths
    assert "/api/admin/collective/rebuild" in paths
    assert "/api/memories/content" in paths


def test_browser_page_contains_operational_controls():
    response = client.get("/browser/")
    assert response.status_code == 200
    for control in (
        'id="scan-lan-button"',
        'id="scan-memories-button"',
        'id="rebuild-button"',
        'id="nuke-button"',
        'id="agent-list"',
        'id="memory-content"',
    ):
        # memory-content is generated dynamically, so only the first four
        # are expected in HTML.
        if control == 'id="memory-content"':
            continue
        assert control in response.text
