import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.database import (
    BoardNotFoundError,
    InvalidMoveError,
    get_board,
    initialize_database,
    move_card,
    rename_column,
)
from app.main import create_app


def login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def card_id_with_title(board: dict, title: str) -> str:
    return next(
        card_id
        for card_id, card in board["cards"].items()
        if card["title"] == title
    )


def test_database_initialization_is_idempotent_and_supports_multiple_users(
    tmp_path,
) -> None:
    database_path = tmp_path / "nested" / "app.db"
    initialize_database(database_path, "user")
    original = get_board(database_path, "user")
    renamed = rename_column(
        database_path, "user", original.columns[0].id, "Ideas"
    )

    initialize_database(database_path, "user")
    initialize_database(database_path, "other")

    persisted = get_board(database_path, "user")
    other = get_board(database_path, "other")
    assert persisted.id == original.id
    assert persisted.columns[0].title == renamed.columns[0].title == "Ideas"
    assert len(persisted.columns) == len(other.columns) == 5
    assert {column.id for column in persisted.columns}.isdisjoint(
        column.id for column in other.columns
    )
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM boards").fetchone()[0] == 2


def test_authenticated_board_api_mutation_workflow(tmp_path) -> None:
    app = create_app(
        tmp_path,
        session_secret="test-session-secret",
        database_path=tmp_path / "app.db",
    )
    with TestClient(app) as client:
        assert client.get("/api/board").status_code == 401
        login(client)

        board = client.get("/api/board").json()
        assert len(board["columns"]) == 5
        backlog, discovery, progress, review, _done = board["columns"]

        response = client.patch(
            f"/api/board/columns/{backlog['id']}", json={"title": "Ideas"}
        )
        assert response.status_code == 200
        assert response.json()["columns"][0]["title"] == "Ideas"

        response = client.post(
            "/api/board/cards",
            json={
                "columnId": discovery["id"],
                "title": "New card",
                "details": "Initial details",
            },
        )
        assert response.status_code == 201
        board = response.json()
        new_card_id = card_id_with_title(board, "New card")
        assert board["columns"][1]["cardIds"] == [new_card_id]

        response = client.patch(
            f"/api/board/cards/{new_card_id}",
            json={"title": "Edited card", "details": "Updated details"},
        )
        assert response.status_code == 200
        assert response.json()["cards"][new_card_id]["details"] == "Updated details"

        response = client.post(
            f"/api/board/cards/{new_card_id}/move",
            json={"columnId": review["id"], "position": 0},
        )
        assert response.status_code == 200
        board = response.json()
        assert board["columns"][1]["cardIds"] == []
        assert board["columns"][3]["cardIds"] == [new_card_id]

        progress_card_id = progress["cardIds"][0]
        backlog_second_card_id = backlog["cardIds"][1]
        response = client.post(
            f"/api/board/cards/{backlog_second_card_id}/move",
            json={"columnId": backlog["id"], "position": 0},
        )
        assert response.status_code == 200
        assert response.json()["columns"][0]["cardIds"][0] == backlog_second_card_id

        response = client.delete(f"/api/board/cards/{progress_card_id}")
        assert response.status_code == 200
        assert progress_card_id not in response.json()["cards"]
        assert response.json()["columns"][2]["cardIds"] == []


def test_invalid_requests_roll_back_and_ownership_is_enforced(tmp_path) -> None:
    database_path = tmp_path / "app.db"
    initialize_database(database_path, "user")
    initialize_database(database_path, "other")
    user_board = get_board(database_path, "user")
    other_board = get_board(database_path, "other")
    card_id = user_board.columns[0].card_ids[0]

    with pytest.raises(InvalidMoveError):
        move_card(
            database_path,
            "user",
            card_id,
            user_board.columns[1].id,
            99,
        )
    assert get_board(database_path, "user") == user_board

    with pytest.raises(BoardNotFoundError):
        rename_column(
            database_path, "other", user_board.columns[0].id, "Not yours"
        )
    assert get_board(database_path, "other") == other_board

    app = create_app(
        tmp_path,
        session_secret="test-session-secret",
        database_path=database_path,
    )
    with TestClient(app) as client:
        login(client)
        assert client.patch(
            "/api/board/columns/missing", json={"title": "Valid"}
        ).status_code == 404
        assert client.patch(
            f"/api/board/columns/{user_board.columns[0].id}",
            json={"title": "   "},
        ).status_code == 422
        assert client.post(
            f"/api/board/cards/{card_id}/move",
            json={"columnId": user_board.columns[1].id, "position": 99},
        ).json() == {"detail": "Position is outside the target column"}
