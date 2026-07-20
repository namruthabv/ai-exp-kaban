import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const boardWithCard = (
  title = "New card",
  details = "Notes"
): BoardData => ({
  ...initialData,
  columns: initialData.columns.map((column, index) =>
    index === 0
      ? { ...column, cardIds: [...column.cardIds, "card-new"] }
      : column
  ),
  cards: {
    ...initialData.cards,
    "card-new": { id: "card-new", title, details },
  },
});

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("KanbanBoard", () => {
  it("loads the canonical board and persists column rename", async () => {
    const renamedBoard = {
      ...initialData,
      columns: initialData.columns.map((column, index) =>
        index === 0 ? { ...column, title: "Ideas" } : column
      ),
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(initialData))
      .mockResolvedValueOnce(jsonResponse(renamedBoard));

    render(<KanbanBoard />);

    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
    const firstColumn = screen.getAllByTestId(/column-/i)[0];
    await userEvent.click(
      within(firstColumn).getByRole("button", {
        name: /edit backlog column title/i,
      })
    );
    const titleInput = within(firstColumn).getByLabelText("Column title");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Ideas{Enter}");

    expect(await within(firstColumn).findByText("Ideas")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/board/columns/col-backlog",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ title: "Ideas" }),
      })
    );
  });

  it("creates, edits, and deletes a card using server responses", async () => {
    const createdBoard = boardWithCard();
    const editedBoard = boardWithCard("Edited card", "Updated notes");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(initialData))
      .mockResolvedValueOnce(jsonResponse(createdBoard, 201))
      .mockResolvedValueOnce(jsonResponse(editedBoard))
      .mockResolvedValueOnce(jsonResponse(initialData));

    render(<KanbanBoard />);
    const firstColumn = (await screen.findAllByTestId(/column-/i))[0];
    await userEvent.click(
      within(firstColumn).getByRole("button", { name: /add a card/i })
    );
    await userEvent.type(
      within(firstColumn).getByPlaceholderText("Card title"),
      "New card"
    );
    await userEvent.type(
      within(firstColumn).getByPlaceholderText("Details"),
      "Notes"
    );
    await userEvent.click(
      within(firstColumn).getByRole("button", { name: "Add card" })
    );

    await userEvent.click(
      await within(firstColumn).findByRole("button", { name: "Edit New card" })
    );
    const titleInput = within(firstColumn).getByLabelText("Card title");
    const detailsInput = within(firstColumn).getByLabelText("Card details");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Edited card");
    await userEvent.clear(detailsInput);
    await userEvent.type(detailsInput, "Updated notes");
    await userEvent.click(
      within(firstColumn).getByRole("button", { name: "Save" })
    );

    await userEvent.click(
      await within(firstColumn).findByRole("button", {
        name: "Delete Edited card",
      })
    );
    await waitFor(() =>
      expect(within(firstColumn).queryByText("Edited card")).not.toBeInTheDocument()
    );
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("shows load failures and returns unauthorized users to sign-in", async () => {
    const onUnauthorized = vi.fn();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse({ detail: "Unavailable" }, 500)
    );
    const { unmount } = render(<KanbanBoard onUnauthorized={onUnauthorized} />);

    expect(
      await screen.findByText("Unable to load your board. Please try again.")
    ).toBeInTheDocument();
    unmount();

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse({ detail: "Authentication required" }, 401)
    );
    render(<KanbanBoard onUnauthorized={onUnauthorized} />);
    await waitFor(() => expect(onUnauthorized).toHaveBeenCalledOnce());
  });

  it("keeps the canonical board visible when a mutation fails", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(initialData))
      .mockResolvedValueOnce(jsonResponse({ detail: "Save failed" }, 500));

    render(<KanbanBoard />);
    const firstColumn = (await screen.findAllByTestId(/column-/i))[0];
    await userEvent.click(
      within(firstColumn).getByRole("button", {
        name: /edit backlog column title/i,
      })
    );
    const titleInput = within(firstColumn).getByLabelText("Column title");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Ideas{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent("Save failed");
    expect(within(firstColumn).getByText("Backlog")).toBeInTheDocument();
    expect(within(firstColumn).queryByText("Ideas")).not.toBeInTheDocument();
  });
});
