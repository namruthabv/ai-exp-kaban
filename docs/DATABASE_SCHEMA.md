# Database design

## Decision

Use four normalized SQLite tables: `users`, `boards`, `board_columns`, and
`cards`. These are the four records already present in the product model; no
repository, audit, session, chat, or generic settings tables are needed yet.

The API returns one canonical board document assembled from these tables. The
document preserves the frontend's current `columns`, `cardIds`, and `cards`
shape, while adding the board ID.

## Requirements inventory

The current board contains:

- A signed-in user identified by username.
- One board owned by that user.
- Exactly five ordered columns with stable IDs and renameable titles.
- Zero or more cards, each with a stable ID, title, details, column, and order.

Persisted operations are full-board read, column rename, card create, card edit,
card delete, card reorder, and card move between columns. Later AI changes may
combine several of those operations and must commit atomically.

## Alternatives considered

| Model | Advantages | Costs |
| --- | --- | --- |
| One JSON document per board | Very small schema and direct whole-board serialization | SQLite cannot simply enforce card references, unique ordering, or five columns; every small change rewrites the full document |
| Normalized core tables | Foreign keys and uniqueness protect ownership and ordering; individual mutations remain explicit; future migrations stay straightforward | The API must assemble rows into one board document |

The normalized model is preferred because it adds only the domain entities the
application already has and gives useful database constraints without triggers.

## Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE
        CHECK (length(trim(username)) BETWEEN 1 AND 100)
) STRICT;

CREATE TABLE boards (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) STRICT;

CREATE TABLE board_columns (
    id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL,
    title TEXT NOT NULL
        CHECK (length(trim(title)) BETWEEN 1 AND 80),
    position INTEGER NOT NULL
        CHECK (position BETWEEN 0 AND 4),
    UNIQUE (board_id, position),
    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
) STRICT;

CREATE TABLE cards (
    id TEXT PRIMARY KEY,
    column_id TEXT NOT NULL,
    title TEXT NOT NULL
        CHECK (length(trim(title)) BETWEEN 1 AND 200),
    details TEXT NOT NULL DEFAULT ''
        CHECK (length(details) <= 4000),
    position INTEGER NOT NULL
        CHECK (position >= 0),
    UNIQUE (column_id, position),
    FOREIGN KEY (column_id) REFERENCES board_columns(id) ON DELETE CASCADE
) STRICT;
```

`STRICT` tables reject values that cannot be stored as their declared SQLite
types. The unique indexes created by the constraints also cover the ordered
board and card queries, so no additional indexes are needed initially.

## Invariants

- `boards.user_id UNIQUE` enforces at most one board per user.
- Column positions are unique and limited to `0` through `4`, so a board cannot
  contain more than five positioned columns.
- Application validation requires every board to contain all five positions
  before commit. A row-count invariant cannot be expressed with a simple SQLite
  `CHECK` constraint, and triggers are not justified for this MVP.
- There is no API to create or delete columns. Titles may change; column IDs and
  positions remain stable.
- Card positions are unique within a column and are stored densely from zero.
- Every card belongs to exactly one column. The column links it to its board and
  owner, so `board_id` and `user_id` are not duplicated on cards.
- Every mutation resolves ownership from the authenticated user through
  `boards.user_id`. Client-supplied user IDs are never trusted.
- IDs are opaque server-generated `TEXT` values. Clients must not infer meaning
  from their format.
- Deleting a user or board cascades through its owned data. Individual column
  deletion is not exposed. Deleting a card compacts the remaining positions in
  the same transaction.
- Timestamps are intentionally omitted because no current behavior consumes
  audit or synchronization time. They can be added by a migration when a real
  requirement exists.

## Canonical board JSON

The API and later AI synchronization use the shape in
[`board.example.json`](./board.example.json):

- `columns` array order is the board column order.
- Each column's `cardIds` array is its card order.
- Every `cardIds` entry must name one entry in `cards`.
- Every card must be referenced exactly once, with no duplicate or orphan IDs.
- Each `cards` object key must equal that card's `id` field.
- The document must have exactly five columns with the current board's stable
  column ID set.

The backend generates authoritative IDs for newly created cards. Storage-only
fields such as row positions and owner IDs are not exposed in this document.

## Transaction mapping

| Operation | Transaction behavior |
| --- | --- |
| Read board | Select the authenticated user's board, columns ordered by `position`, then cards ordered by `position`; assemble canonical JSON |
| Rename column | Update one owned column title; reject empty or overlong titles |
| Create card | Verify the owned target column, insert at its current card count, and return the refreshed board |
| Edit card | Update title/details only after resolving the card through the authenticated user's board |
| Delete card | Delete the owned card and compact later positions in its former column |
| Reorder or move card | Load the affected ordered card IDs, compute the new lists, stage affected positions above their normal range to avoid unique collisions, then write dense positions |
| AI multi-change | Validate the entire proposed change first, then apply every rename/card mutation in one write transaction; any error rolls back all changes |

Mutations use `BEGIN IMMEDIATE` so a write reservation is obtained before
reading and rewriting ordered positions. The affected lists are small, making a
simple position rewrite clearer than fractional or sparse ordering.

## Initialization and migrations

- The default path is `/app/data/app.db`, configurable with `DATABASE_PATH`.
- The directory and database are created at application startup when absent.
- The database remains in the container writable layer. No Docker volume is
  added, so persistence across container recreation is intentionally not
  guaranteed.
- Each connection enables `PRAGMA foreign_keys = ON` and a short
  `busy_timeout`.
- A small ordered migration list is kept in backend code. `PRAGMA user_version`
  records the last successfully applied migration; migrations and the version
  update run transactionally before requests are served.
- The initial migration creates only the four tables above. Later chat or
  authentication storage is added through later migrations rather than being
  anticipated here.

## MVP user and board seed

Startup seeds the hardcoded user and sample board in one transaction:

1. Insert the `user` row with `ON CONFLICT(username) DO NOTHING`.
2. Read that user's stable database ID.
3. Insert a board with `ON CONFLICT(user_id) DO NOTHING`.
4. Only when the board is newly inserted, create positions `0` through `4` and
   the sample cards represented by the canonical example.

If the board already exists, startup never overwrites renamed columns, cards,
or ordering. The password remains the Part 4 hardcoded application credential;
it is not stored in SQLite.

## Design walkthrough

- Rename changes one owned `board_columns` row.
- Create, edit, delete, reorder, and cross-column move each have one explicit
  transaction and preserve dense order.
- Moving into an empty column writes position `0`.
- Full-board reads round-trip all IDs and both ordering arrays.
- AI multi-card changes validate before opening the write transaction and commit
  as one unit.
- A second user's board cannot be reached because every lookup starts from the
  authenticated user's unique board.
- Database constraints allow no sixth column, duplicate column position,
  duplicate card position, or orphan board/column/card row.

Part 5 defines this design only. Schema creation and persistence code begin
only after explicit approval for Part 6.
