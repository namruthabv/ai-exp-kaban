import { useState, type FormEvent } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onEdit: (cardId: string, title: string, details: string) => Promise<boolean>;
  onDelete: (cardId: string) => Promise<boolean>;
};

export const KanbanCard = ({ card, onEdit, onDelete }: KanbanCardProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const handleEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      return;
    }
    setIsSaving(true);
    const saved = await onEdit(card.id, trimmedTitle, details.trim());
    setIsSaving(false);
    if (saved) {
      setIsEditing(false);
    }
  };

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      data-testid={`card-${card.id}`}
    >
      {isEditing ? (
        <form className="space-y-3" onSubmit={handleEdit}>
          <input
            aria-label="Card title"
            className="w-full rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm font-semibold text-[var(--navy-dark)]"
            maxLength={200}
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <textarea
            aria-label="Card details"
            className="w-full resize-none rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--gray-text)]"
            maxLength={4000}
            rows={3}
            value={details}
            onChange={(event) => setDetails(event.target.value)}
          />
          <div className="flex gap-2">
            <button
              className="rounded-full bg-[var(--secondary-purple)] px-3 py-1 text-xs font-semibold text-white"
              disabled={isSaving}
              type="submit"
            >
              {isSaving ? "Saving…" : "Save"}
            </button>
            <button
              className="rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-semibold text-[var(--gray-text)]"
              disabled={isSaving}
              type="button"
              onClick={() => {
                setTitle(card.title);
                setDetails(card.details);
                setIsEditing(false);
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="flex items-start justify-between gap-3">
          <div>
            <h4 className="font-display text-base font-semibold text-[var(--navy-dark)]">
              {card.title}
            </h4>
            <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
              {card.details}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <button
              type="button"
              onClick={() => {
                setTitle(card.title);
                setDetails(card.details);
                setIsEditing(true);
              }}
              className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
              aria-label={`Edit ${card.title}`}
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => void onDelete(card.id)}
              className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
              aria-label={`Delete ${card.title}`}
            >
              Remove
            </button>
            <button
              type="button"
              className="cursor-grab rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)] active:cursor-grabbing"
              aria-label={`Move ${card.title}`}
              {...attributes}
              {...listeners}
            >
              Drag
            </button>
          </div>
        </div>
      )}
    </article>
  );
};
