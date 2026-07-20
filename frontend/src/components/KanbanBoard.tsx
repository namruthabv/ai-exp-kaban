"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { ApiError, boardApi } from "@/lib/api";
import { moveCard, type BoardData } from "@/lib/kanban";

type KanbanBoardProps = {
  username?: string;
  logoutError?: string | null;
  onLogout?: () => void;
  onUnauthorized?: () => void;
};

export const KanbanBoard = ({
  username,
  logoutError,
  onLogout,
  onUnauthorized,
}: KanbanBoardProps = {}) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [boardError, setBoardError] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  const loadBoard = useCallback(async () => {
    setIsLoading(true);
    setBoardError(null);
    try {
      setBoard(await boardApi.read());
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized?.();
        return;
      }
      setBoardError("Unable to load your board. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const runMutation = async (
    operation: () => Promise<BoardData>
  ): Promise<boolean> => {
    if (isMutating) {
      return false;
    }
    setIsMutating(true);
    setBoardError(null);
    try {
      setBoard(await operation());
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized?.();
        return false;
      }
      setBoardError(
        error instanceof ApiError
          ? error.message
          : "Unable to save board changes. Please try again."
      );
      return false;
    } finally {
      setIsMutating(false);
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!board || !over || active.id === over.id) {
      return;
    }

    const cardId = active.id as string;
    const nextColumns = moveCard(
      board.columns,
      cardId,
      over.id as string
    );
    const targetColumn = nextColumns.find((column) =>
      column.cardIds.includes(cardId)
    );
    if (!targetColumn || nextColumns === board.columns) {
      return;
    }
    const position = targetColumn.cardIds.indexOf(cardId);
    void runMutation(() => boardApi.moveCard(cardId, targetColumn.id, position));
  };

  const handleRenameColumn = (columnId: string, title: string) =>
    runMutation(() => boardApi.renameColumn(columnId, title));

  const handleAddCard = (columnId: string, title: string, details: string) =>
    runMutation(() => boardApi.createCard(columnId, title, details));

  const handleEditCard = (cardId: string, title: string, details: string) =>
    runMutation(() => boardApi.editCard(cardId, title, details));

  const handleDeleteCard = (cardId: string) =>
    runMutation(() => boardApi.deleteCard(cardId));

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <p className="text-sm font-semibold text-[var(--gray-text)]" role="status">
          Loading your board…
        </p>
      </main>
    );
  }

  if (!board) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6">
        <p className="text-sm font-semibold text-red-700" role="alert">
          {boardError ?? "Unable to load your board."}
        </p>
        <button
          className="rounded-full bg-[var(--secondary-purple)] px-5 py-2 text-sm font-semibold text-white"
          type="button"
          onClick={() => void loadBoard()}
        >
          Try again
        </button>
      </main>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="flex flex-wrap items-stretch gap-3">
              <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                  Focus
                </p>
                <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                  One board. Five columns. Zero clutter.
                </p>
              </div>
              {username && onLogout ? (
                <div className="flex min-w-40 flex-col justify-between rounded-2xl border border-[var(--stroke)] bg-white px-5 py-4">
                  <p className="text-sm text-[var(--gray-text)]">
                    Signed in as <strong className="text-[var(--navy-dark)]">{username}</strong>
                  </p>
                  <button
                    className="mt-3 self-start text-sm font-semibold text-[var(--secondary-purple)] hover:underline"
                    type="button"
                    onClick={onLogout}
                  >
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          </div>
          {logoutError ? (
            <p className="text-sm text-red-700" role="alert">
              {logoutError}
            </p>
          ) : null}
          {boardError ? (
            <p className="text-sm text-red-700" role="alert">
              {boardError}
            </p>
          ) : null}
          {isMutating ? (
            <p className="text-sm font-semibold text-[var(--gray-text)]" role="status">
              Saving changes…
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onEditCard={handleEditCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>
    </div>
  );
};
