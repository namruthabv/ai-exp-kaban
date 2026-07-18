from fastapi.testclient import TestClient

from app.main import app, create_app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hello() -> None:
    response = client.get("/api/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI"}


def test_frontend_files_are_served_without_shadowing_api(tmp_path) -> None:
    (tmp_path / "index.html").write_text(
        "<h1>Test frontend</h1>", encoding="utf-8"
    )
    assets_dir = tmp_path / "_next" / "static"
    assets_dir.mkdir(parents=True)
    (assets_dir / "app.js").write_text("const loaded = true;", encoding="utf-8")
    frontend_client = TestClient(create_app(tmp_path))

    response = frontend_client.get("/")
    asset_response = frontend_client.get("/_next/static/app.js")
    api_response = frontend_client.get("/api/hello")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Test frontend" in response.text
    assert asset_response.status_code == 200
    assert asset_response.headers["content-type"].startswith("text/javascript")
    assert api_response.json() == {"message": "Hello from FastAPI"}
