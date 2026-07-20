from contextlib import asynccontextmanager
import os
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
from app.board_models import (
    BoardResponse,
    CreateCardRequest,
    EditCardRequest,
    MoveCardRequest,
    RenameColumnRequest,
)
from app.database import (
    BoardNotFoundError,
    InvalidMoveError,
    create_card,
    delete_card,
    edit_card,
    get_board,
    initialize_database,
    move_card,
    rename_column,
)


STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_DATABASE_PATH = Path("/app/data/app.db")


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str


def create_app(
    static_dir: Path = STATIC_DIR,
    session_secret: str | None = None,
    database_path: Path | None = None,
) -> FastAPI:
    configured_database_path = database_path or Path(
        os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH)
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        initialize_database(configured_database_path, MVP_USERNAME)
        yield

    app = FastAPI(title="Project Management MVP", lifespan=lifespan)
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

    def board_not_found() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board resource not found",
        )

    @app.get("/api/board", response_model=BoardResponse)
    def read_board(username: str = Depends(require_user)) -> BoardResponse:
        try:
            return get_board(configured_database_path, username)
        except BoardNotFoundError:
            raise board_not_found() from None

    @app.patch(
        "/api/board/columns/{column_id}", response_model=BoardResponse
    )
    def update_column(
        column_id: str,
        update: RenameColumnRequest,
        username: str = Depends(require_user),
    ) -> BoardResponse:
        try:
            return rename_column(
                configured_database_path, username, column_id, update.title
            )
        except BoardNotFoundError:
            raise board_not_found() from None

    @app.post(
        "/api/board/cards",
        response_model=BoardResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def add_card(
        card: CreateCardRequest, username: str = Depends(require_user)
    ) -> BoardResponse:
        try:
            return create_card(
                configured_database_path,
                username,
                card.column_id,
                card.title,
                card.details,
            )
        except BoardNotFoundError:
            raise board_not_found() from None

    @app.patch("/api/board/cards/{card_id}", response_model=BoardResponse)
    def update_card(
        card_id: str,
        update: EditCardRequest,
        username: str = Depends(require_user),
    ) -> BoardResponse:
        try:
            return edit_card(
                configured_database_path,
                username,
                card_id,
                update.title,
                update.details,
            )
        except BoardNotFoundError:
            raise board_not_found() from None

    @app.delete("/api/board/cards/{card_id}", response_model=BoardResponse)
    def remove_card(
        card_id: str, username: str = Depends(require_user)
    ) -> BoardResponse:
        try:
            return delete_card(configured_database_path, username, card_id)
        except BoardNotFoundError:
            raise board_not_found() from None

    @app.post(
        "/api/board/cards/{card_id}/move", response_model=BoardResponse
    )
    def reposition_card(
        card_id: str,
        move: MoveCardRequest,
        username: str = Depends(require_user),
    ) -> BoardResponse:
        try:
            return move_card(
                configured_database_path,
                username,
                card_id,
                move.column_id,
                move.position,
            )
        except BoardNotFoundError:
            raise board_not_found() from None
        except InvalidMoveError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Position is outside the target column",
            ) from None

    app.frontend("/", directory=static_dir)
    return app


app = create_app()
