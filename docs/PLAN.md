# Project implementation plan

## Delivery rules

- Work through Parts 1-10 in order.
- At the end of every part, update this checklist, summarize changes and test results, and stop for explicit user approval before starting the next part.
- Keep the MVP to one board per user and exactly five renameable columns. Columns cannot be added or removed.
- Use the hardcoded credentials `user` / `password` and a cookie-backed session that lasts until logout. The database schema will still support multiple users.
- Store SQLite inside the container. Persistence across container recreation is not required.
- Apply valid AI-generated board changes immediately and refresh the UI without a confirmation step.
- Never expose `OPENROUTER_API_KEY` to the browser, logs, committed files, or Docker image layers.
- Prefer small, idiomatic modules and add tests with each behavior rather than deferring testing.

## Current status

- Parts 1-7 are implemented and explicitly approved by the user.
- Part 8 has not started and requires explicit approval before implementation.
- The approved Parts 6-7 implementation is committed on `main`.

## Implemented design decisions

### Runtime and deployment

- FastAPI serves both `/api/*` and the statically exported Next.js application
  from one origin; there is no production Next.js server or CORS layer.
- The production image uses a Node build stage and a pinned `uv` Python runtime
  stage. Frontend lint, unit tests, and the static build run during the image
  build.
- Docker Compose remains compatible with Docker Engine, Rancher Desktop,
  Colima, and Docker Desktop. The macOS start script uses the native platform
  and excludes inherited proxy variables by default; `--use-proxy` opts back
  into the terminal's proxy settings.
- SQLite defaults to `/app/data/app.db` and can be changed with
  `DATABASE_PATH`. It remains in the container writable layer with no mounted
  volume, so it survives logout, page reload, and normal use of the same
  container, but not container recreation.

### Authentication

- Authentication intentionally accepts only the MVP credentials `user` /
  `password`; the password is not stored in SQLite. The normalized database
  still supports additional users when a future authentication flow is added.
- The session is an HTTP-only, SameSite=Lax, HMAC-signed cookie without a
  persistent expiry. It is Secure on HTTPS and is deleted on logout.
- `SESSION_SECRET` keeps sessions valid across application restarts. When it is
  absent, the backend creates an ephemeral signing secret for that process.

### Database and board API

- The approved normalized schema and rationale live in
  [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md); the canonical response example
  lives in [`board.example.json`](./board.example.json).
- The backend uses Python's standard `sqlite3` module rather than an ORM. A
  FastAPI lifespan hook creates the directory, applies ordered migrations using
  `PRAGMA user_version`, and seeds a user and board only when absent.
- Server-generated UUID-based text IDs are opaque. Seed IDs are also generated
  per board so multiple users cannot collide.
- All writes use `BEGIN IMMEDIATE`, verify ownership through the authenticated
  username, maintain dense card positions, and roll back on failure.
- Board routes are:
  - `GET /api/board`
  - `PATCH /api/board/columns/{column_id}`
  - `POST /api/board/cards`
  - `PATCH /api/board/cards/{card_id}`
  - `DELETE /api/board/cards/{card_id}`
  - `POST /api/board/cards/{card_id}/move`
- Every successful mutation returns the complete canonical board. Card creation
  returns `201`; authentication, missing ownership-scoped resources, and
  invalid input use concise `401`, `404`, and `422` responses respectively.

### Frontend state synchronization

- A small typed same-origin API client is the only board transport boundary.
  Runtime board data is fetched after authentication; `initialData` is no
  longer displayed as application state.
- The UI does not optimistically maintain a competing board. After every
  successful mutation, it replaces board state with the canonical server
  response; failures retain the last persisted board and show a focused error.
- Column and card forms keep only temporary draft input. Column rename saves on
  blur or Enter; failed creates or edits preserve useful form context.
- A `401` from the board API returns the user to sign-in. Initial loading,
  retryable load failures, mutation progress, and mutation failures have
  explicit UI states.
- Cards use a dedicated drag handle with pointer and keyboard sensors. Drag
  results are converted to an authoritative target column and zero-based
  position before calling the move API.

### Verification through Part 7

- Backend: 8 focused tests passed against isolated temporary SQLite databases.
- Frontend: lint passed; 9 API, pure-logic, and component tests passed.
- Production static build and TypeScript validation passed.
- Browser integration: 3 Playwright tests passed against the production static
  export served by FastAPI, including login and persisted rename, create, edit,
  drag/move, delete, logout/login, and page reload behavior.
- The running Compose image was subsequently verified to expose the new
  authenticated board API. A controlled move, logout, login, read, and restore
  cycle proved that state persists across logout/login in the same container.

## Part 1: Plan

### Checklist

- [x] Review the root `AGENTS.md` and the existing frontend structure.
- [x] Record the agreed MVP decisions and approval gates in this plan.
- [x] Break Parts 2-10 into implementation checklists.
- [x] Define tests and success criteria for every part.
- [x] Add `frontend/AGENTS.md` describing the current frontend and its conventions.
- [x] Receive explicit user approval to begin Part 2.

### Tests and review

- Confirm every business requirement maps to at least one implementation part.
- Confirm every part has concrete tests and observable success criteria.
- Confirm frontend guidance matches the files and scripts currently present.

### Success criteria

- `docs/PLAN.md` is detailed enough to execute without unresolved architectural decisions for the next part.
- `frontend/AGENTS.md` accurately explains the current demo, its data flow, and validation commands.
- The user approves Part 1 before any scaffolding begins.

## Part 2: Scaffolding

### Checklist

- [x] Confirm current stable dependency versions from primary documentation before pinning them.
- [x] Create a minimal `backend/` FastAPI application managed by `uv`.
- [x] Add a health/example API endpoint and a small static hello-world page that calls it.
- [x] Add a production Dockerfile that installs the Python environment and runs FastAPI.
- [x] Add a minimal Docker Compose configuration for local build and execution.
- [x] Pass configuration through environment variables without copying `.env` into the image.
- [x] Add start and stop scripts for macOS, Linux, and Windows under `scripts/`.
- [x] Add concise root README instructions for prerequisites, start, stop, and verification.
- [x] Update ignore files for generated Python, Docker, test, database, and frontend artifacts as needed.
- [x] Mark Part 2 complete and request explicit approval for Part 3.

### Tests

- Backend unit test: the example API returns the expected status and JSON.
- Container smoke test: build and start the image, then verify `/` serves HTML and the page can successfully call the example API.
- Script smoke tests: validate shell syntax and PowerShell parsing where supported; document any platform script that cannot be executed on the development host.
- Image inspection: confirm `.env`, local database files, caches, and development-only artifacts are absent from the image.

### Success criteria

- A fresh checkout can be started locally using the documented platform script.
- One container serves both the example page and FastAPI from one origin.
- Stop scripts cleanly stop the local application.
- The example UI visibly displays data returned by the API.

## Part 3: Add the frontend

### Checklist

- [x] Configure Next.js for a static export compatible with FastAPI static hosting.
- [x] Adjust font/assets or browser-only assumptions that prevent an offline static production build.
- [x] Add a Docker build stage that installs locked npm dependencies, tests, and exports the frontend.
- [x] Copy the exported assets into the backend image and serve them at `/` with SPA/static fallback behavior where required.
- [x] Preserve the existing five-column Kanban behavior and color scheme.
- [x] Keep backend/API paths from being shadowed by static routing.
- [x] Update run and test documentation.
- [x] Mark Part 3 complete and request explicit approval for Part 4.

### Tests

- Existing Vitest tests for five columns, rename, add/remove, and card movement logic pass.
- Existing Playwright tests run against the container-served production export, including loading, adding, and dragging a card.
- Backend/static integration tests verify `/`, static assets, and API routes return the correct content types and status codes.
- Run frontend lint, TypeScript/build checks, unit tests, and browser tests.

### Success criteria

- The Docker container serves the current Kanban demo at `/` with no Next.js development server.
- All current board interactions still work in a browser.
- Frontend and API operate from the same origin without CORS configuration.

## Part 4: Fake user sign-in

### Checklist

- [x] Add a minimal login page using the project color scheme.
- [x] Add backend login, logout, and current-session endpoints.
- [x] Validate only the hardcoded MVP credentials `user` / `password`.
- [x] Issue an HTTP-only, same-site session cookie with no persistent expiry; set `Secure` when appropriate for the environment.
- [x] Keep session signing secrets configurable and out of source control.
- [x] Require authentication for the board page and protected API routes.
- [x] Add logout behavior and redirect unauthenticated or expired sessions to login.
- [x] Ensure authentication errors are concise and do not reveal sensitive details.
- [x] Mark Part 4 complete and request explicit approval for Part 5.

### Tests

- Backend tests cover valid login, invalid credentials, missing/invalid session, current user, logout, and protected endpoint access.
- Playwright tests cover form validation, failed login feedback, authenticated board display, session refresh, and logout.
- Inspect response headers to verify cookie security attributes and absence of credentials in responses.

### Success criteria

- An unauthenticated visitor cannot view the board or call protected routes.
- Correct credentials establish a session that survives page refresh and lasts until logout/browser session end.
- Logout invalidates access and returns the user to the login experience.

## Part 5: Database modeling

### Checklist

- [x] Inventory the frontend board fields and the operations required by UI and AI flows.
- [x] Compare a normalized relational model with a single JSON-document model for this MVP.
- [x] Propose the simplest SQLite schema that supports multiple users, one board per user, exactly five ordered columns, ordered cards, and future migrations.
- [x] Define IDs, ownership, ordering, constraints, timestamps if justified, and delete behavior.
- [x] Define the canonical API/AI board JSON shape and save an example JSON document under `docs/`.
- [x] Document initialization, transaction, migration, and container-local storage behavior.
- [x] Document how the hardcoded MVP user is seeded idempotently.
- [x] Do not implement the schema in this part.
- [x] Request explicit approval of the database design before Part 6.

### Tests and review

- Walk through rename column, create/edit/delete/move card, full-board read, AI multi-card update, and user isolation against the proposed schema.
- Validate constraints can enforce one board per user and five columns per board at the application/transaction boundary.
- Validate the JSON example round-trips without losing ordering or identity.

### Success criteria

- The schema and canonical JSON are documented with clear rationale and no unnecessary entities.
- Every required board operation has an unambiguous transactional mapping.
- The user explicitly approves the database design before implementation.

## Part 6: Backend board API

### Checklist

- [x] Implement the approved SQLite model with a small, explicit migration/initialization path.
- [x] Create the database and seed the MVP user and five-column board idempotently when absent.
- [x] Add authenticated routes to read the current user's board.
- [x] Add authenticated routes to rename columns and create, edit, delete, and move cards.
- [x] Preserve card order within and across columns using transactions.
- [x] Scope every query and mutation to the authenticated user.
- [x] Validate input with FastAPI/Pydantic request and response models.
- [x] Return predictable HTTP statuses and concise error bodies.
- [x] Add backend test fixtures using isolated temporary databases.
- [x] Mark Part 6 complete and request explicit approval for Part 7.

### Tests

- Unit tests cover serialization, validation, ordering, and move logic.
- API tests cover initial database creation, idempotent seeding, board retrieval, every mutation, invalid IDs/input, and authentication.
- Transaction tests cover moves within a column, between columns, into empty columns, and rollback on failure.
- Isolation tests create a second user and prove users cannot read or mutate one another's board.
- Restart test proves an existing database is reused without duplicate seed data.

### Success criteria

- The complete board can be safely read and mutated through authenticated APIs.
- Database creation requires no manual command on first startup.
- Exactly five columns and consistent card ordering are maintained after all supported operations.
- Backend tests pass against temporary SQLite databases.

## Part 7: Connect frontend and backend

### Checklist

- [x] Replace `initialData` runtime state with an authenticated board fetch.
- [x] Add a small typed API client and keep API transport separate from presentational components.
- [x] Connect rename, add, edit, delete, and drag/move actions to backend mutations.
- [x] Add the missing card-edit UI required by the business requirements.
- [x] Show focused loading and error states for initial load and mutations.
- [x] Keep the UI synchronized with server responses; avoid maintaining competing board representations.
- [x] Handle unauthorized responses by returning to login.
- [x] Preserve the existing visual design and five-column responsive layout.
- [x] Mark Part 7 complete and request explicit approval for Part 8.

### Tests

- API-client unit tests cover move request shape, canonical response parsing, and error mapping.
- Pure board tests cover same-column reorder, cross-column move, and dropping at a column end.
- Component tests mock the API and cover load, rename, add, edit, delete, load failure, mutation failure, and unauthorized state.
- Backend/frontend integration tests verify mutations persist after page refresh.
- Playwright tests cover login followed by every board operation, including drag-and-drop and card editing.
- Run lint, frontend unit tests, backend tests, the static build, and Playwright against the production export served by FastAPI; verify the resulting Compose image and API separately.

### Success criteria

- All board data displayed by the frontend comes from the authenticated backend.
- Every user action persists to SQLite and remains visible after refresh.
- Failures are visible and do not silently leave the UI inconsistent with the server.

## Part 8: AI connectivity

### Checklist

- [ ] Add backend-only OpenRouter configuration using `OPENROUTER_API_KEY` and model `openai/gpt-oss-120b`.
- [ ] Implement a small AI client with explicit request timeout and clear provider error mapping.
- [ ] Add an authenticated diagnostic endpoint or script that asks `2+2` and returns the model response.
- [ ] Keep the provider client injectable so automated tests do not require network or spend credits.
- [ ] Document the one intentional live connectivity check.
- [ ] Ensure secrets and authorization headers are never logged or returned.
- [ ] Mark Part 8 complete and request explicit approval for Part 9.

### Tests

- Unit tests mock OpenRouter success, timeout, malformed response, authentication failure, and provider failure.
- API tests verify authentication and sanitized error responses.
- With user authorization to make the external call, run one live `2+2` connectivity smoke test and record only the non-sensitive result.
- Inspect logs and responses for accidental key/header exposure.

### Success criteria

- The backend receives a correct answer to the live `2+2` request from the configured model.
- Frontend code and built static assets contain no OpenRouter credential.
- Automated tests remain deterministic and do not call the live provider.

## Part 9: Structured AI board updates

### Checklist

- [ ] Define a minimal structured response schema containing assistant text and an optional board update.
- [ ] Send the canonical current board JSON, the user's message, and bounded conversation history to the model.
- [ ] Require OpenRouter structured output matching the schema supported by the configured model.
- [ ] Validate responses locally before applying any mutation.
- [ ] Apply valid multi-card/column changes atomically and preserve user ownership, exactly five columns, IDs, references, and ordering.
- [ ] Reject invalid structured updates without partially changing the board; still return a safe user-facing error.
- [ ] Return the assistant message and updated canonical board from the authenticated chat endpoint.
- [ ] Bound message/history size and document the conversation ownership/lifetime chosen for the MVP.
- [ ] Mark Part 9 complete and request explicit approval for Part 10.

### Tests

- Schema tests cover text-only replies, valid board updates, multiple changes, malformed JSON, invalid references, duplicate IDs, missing cards, and attempts to add/remove columns.
- Prompt/client tests verify the board, user message, and ordered history are sent without leaking secrets.
- Transaction tests prove all-or-nothing application of valid and invalid updates.
- API tests mock OpenRouter and cover authentication, provider errors, validation errors, and successful persisted updates.
- Run a small authorized live smoke test for a text-only question and a simple card mutation after mocked tests pass.

### Success criteria

- Every AI response is locally schema-validated before use.
- Valid updates are persisted atomically and invalid updates leave the board unchanged.
- The response always gives the frontend enough information to display assistant text and synchronize the board.

## Part 10: AI chat sidebar

### Checklist

- [ ] Add an accessible, responsive AI chat sidebar that complements the existing board and color scheme.
- [ ] Display the current conversation in order with distinct user, assistant, loading, and error states.
- [ ] Add message submission with disabled/duplicate-submit protection.
- [ ] Connect the sidebar to the authenticated structured chat endpoint.
- [ ] Immediately replace/refetch board state when a response includes an AI update.
- [ ] Keep chat usable on smaller screens without making the board unusable.
- [ ] Preserve board interactions while the sidebar is open.
- [ ] Add concise empty-state guidance demonstrating supported create/edit/move requests without adding extra product features.
- [ ] Complete full regression testing and minimal final documentation.
- [ ] Mark Part 10 complete and request final user review and approval.

### Tests

- Component tests cover opening/closing, text-only conversation, submit/loading/error states, retry behavior if implemented, and board-refresh behavior.
- Integration tests mock structured responses for create, edit, move, multi-card update, no update, and invalid/provider failure.
- Playwright tests cover login, a normal chat exchange, AI-created card, AI-edited card, AI-moved card, immediate UI refresh, persistence after reload, and mobile sidebar behavior.
- Accessibility checks cover labels, focus movement, keyboard submission, reading order, and visible focus.
- Run all backend tests, frontend lint/unit tests, production static build, Docker smoke tests, and container-based Playwright tests.

### Success criteria

- A signed-in user can chat with the configured model from the sidebar.
- AI text appears in conversation order and valid AI changes appear on the board immediately.
- AI-created, edited, and moved cards persist after refresh.
- The complete application runs locally in one Docker container and all automated checks pass.
