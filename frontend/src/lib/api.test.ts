import { ApiError, boardApi } from "@/lib/api";
import { initialData } from "@/lib/kanban";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("boardApi", () => {
  it("sends the persisted move destination and returns the canonical board", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(initialData));

    await expect(boardApi.moveCard("card-1", "col-review", 0)).resolves.toEqual(
      initialData
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board/cards/card-1/move",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ columnId: "col-review", position: 0 }),
      })
    );
  });

  it("exposes the status and concise backend error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Authentication required" }, 401)
    );

    await expect(boardApi.read()).rejects.toEqual(
      new ApiError("Authentication required", 401)
    );
  });
});
