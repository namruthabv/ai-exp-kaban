from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import uuid

from app.board_models import BoardResponse, CardResponse, ColumnResponse


MIGRATIONS: tuple[tuple[str, ...], ...] = (
    (
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE
                CHECK (length(trim(username)) BETWEEN 1 AND 100)
        ) STRICT
        """,
        """
        CREATE TABLE boards (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) STRICT
        """,
        """
        CREATE TABLE board_columns (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL,
            title TEXT NOT NULL
                CHECK (length(trim(title)) BETWEEN 1 AND 80),
            position INTEGER NOT NULL CHECK (position BETWEEN 0 AND 4),
            UNIQUE (board_id, position),
            FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
        ) STRICT
        """,
        """
        CREATE TABLE cards (
            id TEXT PRIMARY KEY,
            column_id TEXT NOT NULL,
            title TEXT NOT NULL
                CHECK (length(trim(title)) BETWEEN 1 AND 200),
            details TEXT NOT NULL DEFAULT '' CHECK (length(details) <= 4000),
            position INTEGER NOT NULL CHECK (position >= 0),
            UNIQUE (column_id, position),
            FOREIGN KEY (column_id) REFERENCES board_columns(id) ON DELETE CASCADE
        ) STRICT
        """,
    ),
)

SEED_COLUMNS = ("Backlog", "Discovery", "In Progress", "Review", "Done")

SEED_CARDS = (
    (
        0,
        "Align roadmap themes",
        "Draft quarterly themes with impact statements and metrics.",
    ),
    (
        0,
        "Gather customer signals",
        "Review support tags, sales notes, and churn feedback.",
    ),
    (
        2,
        "Design card layout",
        "Add hierarchy and spacing for scanning dense lists.",
    ),
)


class BoardNotFoundError(Exception):
    pass


class InvalidMoveError(Exception):
    pass


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def immediate_transaction(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: Path, username: str) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with immediate_transaction(database_path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > len(MIGRATIONS):
            raise RuntimeError("Database schema is newer than this application")

        for migration_number, statements in enumerate(
            MIGRATIONS[version:], start=version + 1
        ):
            for statement in statements:
                connection.execute(statement)
            connection.execute(f"PRAGMA user_version = {migration_number}")

        _seed_board(connection, username)


def _seed_board(connection: sqlite3.Connection, username: str) -> None:
    connection.execute(
        "INSERT INTO users (id, username) VALUES (?, ?) "
        "ON CONFLICT(username) DO NOTHING",
        (new_id("user"), username),
    )
    user_id = connection.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()["id"]
    board_id = new_id("board")
    inserted = connection.execute(
        "INSERT INTO boards (id, user_id) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO NOTHING",
        (board_id, user_id),
    ).rowcount
    if not inserted:
        return

    columns = [
        (new_id("column"), board_id, title, position)
        for position, title in enumerate(SEED_COLUMNS)
    ]
    connection.executemany(
        "INSERT INTO board_columns (id, board_id, title, position) "
        "VALUES (?, ?, ?, ?)",
        columns,
    )
    next_positions: dict[int, int] = {}
    cards = []
    for column_position, title, details in SEED_CARDS:
        card_position = next_positions.get(column_position, 0)
        cards.append(
            (
                new_id("card"),
                columns[column_position][0],
                title,
                details,
                card_position,
            )
        )
        next_positions[column_position] = card_position + 1
    connection.executemany(
        "INSERT INTO cards (id, column_id, title, details, position) "
        "VALUES (?, ?, ?, ?, ?)",
        cards,
    )


def get_board(database_path: Path, username: str) -> BoardResponse:
    connection = connect(database_path)
    try:
        return _read_board(connection, username)
    finally:
        connection.close()


def _read_board(connection: sqlite3.Connection, username: str) -> BoardResponse:
    board = connection.execute(
        """
        SELECT boards.id
        FROM boards
        JOIN users ON users.id = boards.user_id
        WHERE users.username = ?
        """,
        (username,),
    ).fetchone()
    if board is None:
        raise BoardNotFoundError

    columns = connection.execute(
        "SELECT id, title, position FROM board_columns "
        "WHERE board_id = ? ORDER BY position",
        (board["id"],),
    ).fetchall()
    if [row["position"] for row in columns] != list(range(5)):
        raise RuntimeError("Board must contain exactly five ordered columns")

    card_rows = connection.execute(
        """
        SELECT cards.id, cards.column_id, cards.title, cards.details
        FROM cards
        JOIN board_columns ON board_columns.id = cards.column_id
        WHERE board_columns.board_id = ?
        ORDER BY board_columns.position, cards.position
        """,
        (board["id"],),
    ).fetchall()
    card_ids_by_column = {row["id"]: [] for row in columns}
    cards: dict[str, CardResponse] = {}
    for row in card_rows:
        card_ids_by_column[row["column_id"]].append(row["id"])
        cards[row["id"]] = CardResponse(
            id=row["id"], title=row["title"], details=row["details"]
        )

    return BoardResponse(
        id=board["id"],
        columns=[
            ColumnResponse(
                id=row["id"],
                title=row["title"],
                card_ids=card_ids_by_column[row["id"]],
            )
            for row in columns
        ],
        cards=cards,
    )


def rename_column(
    database_path: Path, username: str, column_id: str, title: str
) -> BoardResponse:
    with immediate_transaction(database_path) as connection:
        result = connection.execute(
            """
            UPDATE board_columns SET title = ?
            WHERE id = ? AND board_id = (
                SELECT boards.id FROM boards
                JOIN users ON users.id = boards.user_id
                WHERE users.username = ?
            )
            """,
            (title, column_id, username),
        )
        if result.rowcount != 1:
            raise BoardNotFoundError
        return _read_board(connection, username)


def create_card(
    database_path: Path,
    username: str,
    column_id: str,
    title: str,
    details: str,
) -> BoardResponse:
    with immediate_transaction(database_path) as connection:
        if not _owned_column(connection, username, column_id):
            raise BoardNotFoundError
        position = connection.execute(
            "SELECT count(*) FROM cards WHERE column_id = ?", (column_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO cards (id, column_id, title, details, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (new_id("card"), column_id, title, details, position),
        )
        return _read_board(connection, username)


def edit_card(
    database_path: Path,
    username: str,
    card_id: str,
    title: str,
    details: str,
) -> BoardResponse:
    with immediate_transaction(database_path) as connection:
        result = connection.execute(
            """
            UPDATE cards SET title = ?, details = ?
            WHERE id = ? AND column_id IN (
                SELECT board_columns.id FROM board_columns
                JOIN boards ON boards.id = board_columns.board_id
                JOIN users ON users.id = boards.user_id
                WHERE users.username = ?
            )
            """,
            (title, details, card_id, username),
        )
        if result.rowcount != 1:
            raise BoardNotFoundError
        return _read_board(connection, username)


def delete_card(database_path: Path, username: str, card_id: str) -> BoardResponse:
    with immediate_transaction(database_path) as connection:
        card = _owned_card(connection, username, card_id)
        if card is None:
            raise BoardNotFoundError
        connection.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        remaining_ids = [
            row["id"]
            for row in connection.execute(
                "SELECT id FROM cards WHERE column_id = ? ORDER BY position",
                (card["column_id"],),
            )
        ]
        _rewrite_columns(connection, {card["column_id"]: remaining_ids})
        return _read_board(connection, username)


def move_card(
    database_path: Path,
    username: str,
    card_id: str,
    target_column_id: str,
    position: int,
) -> BoardResponse:
    with immediate_transaction(database_path) as connection:
        card = _owned_card(connection, username, card_id)
        if card is None or not _owned_column(connection, username, target_column_id):
            raise BoardNotFoundError

        source_column_id = card["column_id"]
        source_ids = _ordered_card_ids(connection, source_column_id)
        source_ids.remove(card_id)
        if source_column_id == target_column_id:
            target_ids = source_ids
            rewrites = {source_column_id: target_ids}
        else:
            target_ids = _ordered_card_ids(connection, target_column_id)
            rewrites = {
                source_column_id: source_ids,
                target_column_id: target_ids,
            }

        if position > len(target_ids):
            raise InvalidMoveError
        target_ids.insert(position, card_id)
        _rewrite_columns(connection, rewrites)
        return _read_board(connection, username)


def _owned_column(
    connection: sqlite3.Connection, username: str, column_id: str
) -> bool:
    return connection.execute(
        """
        SELECT 1 FROM board_columns
        JOIN boards ON boards.id = board_columns.board_id
        JOIN users ON users.id = boards.user_id
        WHERE users.username = ? AND board_columns.id = ?
        """,
        (username, column_id),
    ).fetchone() is not None


def _owned_card(
    connection: sqlite3.Connection, username: str, card_id: str
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT cards.column_id, cards.position FROM cards
        JOIN board_columns ON board_columns.id = cards.column_id
        JOIN boards ON boards.id = board_columns.board_id
        JOIN users ON users.id = boards.user_id
        WHERE users.username = ? AND cards.id = ?
        """,
        (username, card_id),
    ).fetchone()


def _ordered_card_ids(
    connection: sqlite3.Connection, column_id: str
) -> list[str]:
    return [
        row["id"]
        for row in connection.execute(
            "SELECT id FROM cards WHERE column_id = ? ORDER BY position",
            (column_id,),
        )
    ]


def _rewrite_columns(
    connection: sqlite3.Connection, ordered_ids: dict[str, list[str]]
) -> None:
    column_ids = tuple(ordered_ids)
    placeholders = ", ".join("?" for _ in column_ids)
    connection.execute(
        f"UPDATE cards SET position = position + 1000000 "
        f"WHERE column_id IN ({placeholders})",
        column_ids,
    )
    for column_id, card_ids in ordered_ids.items():
        connection.executemany(
            "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
            [
                (column_id, position, card_id)
                for position, card_id in enumerate(card_ids)
            ],
        )
