# Frontend development guide

## Scope

This file applies to everything under `frontend/`. Follow the repository-root `AGENTS.md` as well; this file adds guidance specific to the existing frontend.

## Current application

- Next.js 16 App Router application using React 19 and TypeScript.
- The only route is `src/app/page.tsx`, which renders `KanbanBoard`.
- The board is currently a client-only demo. State starts from `initialData` and is lost on refresh.
- The MVP board has exactly five columns. Users may rename them but must not add or remove columns.
- Cards can currently be added, removed, reordered, and moved between columns. The required card-edit flow has not been implemented yet.
- Drag-and-drop uses `@dnd-kit/core` and `@dnd-kit/sortable`.
- Styling uses Tailwind CSS 4 utilities plus project color variables in `src/app/globals.css`.
- Production uses a self-contained static export and system font stacks, so builds do not fetch fonts from external services.

## Structure and data flow

- `src/app/`: route, metadata, fonts, and global styles.
- `src/components/KanbanBoard.tsx`: owns the current in-memory board state and coordinates mutations and drag events.
- `src/components/KanbanColumn.tsx`: renders a droppable column, its title, cards, and add-card form.
- `src/components/KanbanCard.tsx`: renders a sortable card and remove action.
- `src/components/KanbanCardPreview.tsx`: drag overlay presentation.
- `src/components/NewCardForm.tsx`: local form state for creating cards.
- `src/lib/kanban.ts`: board types, sample data, ID creation, and pure card-movement logic.
- `src/test/`: Vitest setup and declarations.
- `tests/`: Playwright browser tests.

Keep pure board transformations independent of React where practical. When backend integration is added, use one small typed API boundary and treat the backend response as the canonical persisted state. Do not duplicate server data across unnecessary stores or add a state-management library without a demonstrated need.

## UI rules

- Preserve the project palette defined in the root instructions and CSS variables.
- Maintain accessible names for controls and stable `data-testid` values only where browser interaction needs them.
- Keep exactly five columns visible in the board model. Renaming is allowed; adding or deleting columns is not.
- Make loading, authentication, and mutation failures visible and concise.
- Keep interactions keyboard-accessible and preserve visible focus states.
- Do not add product features beyond the approved plan.

## Testing

From `frontend/`:

```bash
npm run lint
npm run test:unit
npm run build
npm run test:e2e
```

- Vitest and Testing Library cover pure board logic and component behavior.
- Playwright covers user-visible workflows and real drag-and-drop behavior.
- Add or update tests in the same part as each behavior change.
- Browser tests run against the container-served production export at `http://127.0.0.1:8000`.
- Do not make tests depend on live OpenRouter calls; mock the backend/provider except for explicitly approved connectivity smoke tests.

## Build constraints

- Commit `package-lock.json` and use locked installs in Docker/CI.
- The production frontend will be a static export served by FastAPI; do not introduce Next.js server-only runtime dependencies.
- Browser code must never receive `OPENROUTER_API_KEY` or other backend secrets.
- Keep API calls same-origin so the local deployment does not need CORS.
