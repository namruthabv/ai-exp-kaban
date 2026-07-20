import type { BoardData } from "@/lib/kanban";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
  }
}

const requestBoard = async (
  path: string,
  options?: RequestInit
): Promise<BoardData> => {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = "Unable to save board changes.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Use the concise fallback when the server did not return JSON.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as BoardData;
};

const jsonRequest = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const boardApi = {
  read: () => requestBoard("/api/board"),
  renameColumn: (columnId: string, title: string) =>
    requestBoard(
      `/api/board/columns/${encodeURIComponent(columnId)}`,
      jsonRequest("PATCH", { title })
    ),
  createCard: (columnId: string, title: string, details: string) =>
    requestBoard(
      "/api/board/cards",
      jsonRequest("POST", { columnId, title, details })
    ),
  editCard: (cardId: string, title: string, details: string) =>
    requestBoard(
      `/api/board/cards/${encodeURIComponent(cardId)}`,
      jsonRequest("PATCH", { title, details })
    ),
  deleteCard: (cardId: string) =>
    requestBoard(`/api/board/cards/${encodeURIComponent(cardId)}`, {
      method: "DELETE",
    }),
  moveCard: (cardId: string, columnId: string, position: number) =>
    requestBoard(
      `/api/board/cards/${encodeURIComponent(cardId)}/move`,
      jsonRequest("POST", { columnId, position })
    ),
};
