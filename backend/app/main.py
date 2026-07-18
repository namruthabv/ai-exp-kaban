from pathlib import Path
import secrets

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.auth import (
    MVP_PASSWORD,
    MVP_USERNAME,
    SESSION_COOKIE,
    create_session_token,
    get_session_secret,
    read_session_token,
)


STATIC_DIR = Path(__file__).parent / "static"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str


def create_app(
    static_dir: Path = STATIC_DIR, session_secret: str | None = None
) -> FastAPI:
    app = FastAPI(title="Project Management MVP")
    signing_secret = get_session_secret(session_secret)

    def require_user(request: Request) -> str:
        username = read_session_token(
            request.cookies.get(SESSION_COOKIE), signing_secret
        )
        if username != MVP_USERNAME:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return username

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/login", response_model=UserResponse)
    def login(
        credentials: LoginRequest, request: Request, response: Response
    ) -> UserResponse:
        valid_username = secrets.compare_digest(credentials.username, MVP_USERNAME)
        valid_password = secrets.compare_digest(credentials.password, MVP_PASSWORD)
        if not (valid_username and valid_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        response.set_cookie(
            key=SESSION_COOKIE,
            value=create_session_token(MVP_USERNAME, signing_secret),
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            path="/",
        )
        return UserResponse(username=MVP_USERNAME)

    @app.get("/api/auth/me", response_model=UserResponse)
    def current_user(username: str = Depends(require_user)) -> UserResponse:
        return UserResponse(username=username)

    @app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request, response: Response) -> None:
        response.delete_cookie(
            key=SESSION_COOKIE,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            path="/",
        )

    @app.get("/api/hello")
    def hello(_username: str = Depends(require_user)) -> dict[str, str]:
        return {"message": "Hello from FastAPI"}

    app.frontend("/", directory=static_dir)
    return app


app = create_app()
