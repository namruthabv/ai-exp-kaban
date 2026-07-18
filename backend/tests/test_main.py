from fastapi.testclient import TestClient

from app.auth import SESSION_COOKIE
from app.main import app, create_app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hello() -> None:
    response = client.get("/api/hello")

    assert response.status_code == 401


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
    api_response = frontend_client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Test frontend" in response.text
    assert asset_response.status_code == 200
    assert asset_response.headers["content-type"].startswith("text/javascript")
    assert api_response.json() == {"status": "ok"}


def test_authentication_lifecycle(tmp_path) -> None:
    auth_client = TestClient(
        create_app(tmp_path, session_secret="test-session-secret"),
        base_url="https://testserver",
    )

    assert auth_client.get("/api/auth/me").status_code == 401
    assert auth_client.get("/api/hello").status_code == 401

    login_response = auth_client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )

    assert login_response.status_code == 200
    assert login_response.json() == {"username": "user"}
    assert "password" not in login_response.text
    set_cookie = login_response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Secure" in set_cookie
    assert "Max-Age" not in set_cookie
    assert "expires=" not in set_cookie.lower()

    assert auth_client.get("/api/auth/me").json() == {"username": "user"}
    assert auth_client.get("/api/hello").json() == {
        "message": "Hello from FastAPI"
    }

    logout_response = auth_client.post("/api/auth/logout")

    assert logout_response.status_code == 204
    assert auth_client.get("/api/auth/me").status_code == 401


def test_invalid_credentials_and_tampered_session(tmp_path) -> None:
    auth_client = TestClient(
        create_app(tmp_path, session_secret="test-session-secret")
    )

    invalid_response = auth_client.post(
        "/api/auth/login",
        json={"username": "user", "password": "wrong"},
    )

    assert invalid_response.status_code == 401
    assert invalid_response.json() == {"detail": "Invalid username or password"}

    auth_client.cookies.set(SESSION_COOKIE, "tampered.session")
    assert auth_client.get("/api/auth/me").status_code == 401
