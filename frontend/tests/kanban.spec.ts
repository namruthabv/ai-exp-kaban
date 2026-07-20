import { expect, test, type Page } from "@playwright/test";

const signIn = async (page: Page) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
};

test("requires a valid session and supports login persistence and logout", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeHidden();

  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByText("Invalid username or password.", { exact: true })
  ).toBeVisible();

  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("loads the kanban board", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("persists board changes after refresh", async ({ page }) => {
  await signIn(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const renamedColumn = `Ideas ${Date.now()}`;
  await firstColumn.getByRole("button", { name: /edit .* column title/i }).click();
  await firstColumn.getByLabel("Column title").fill(renamedColumn);
  await firstColumn.getByLabel("Column title").press("Enter");
  await expect(firstColumn.getByText(renamedColumn)).toBeVisible();

  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  const originalTitle = `Playwright card ${Date.now()}`;
  const editedTitle = `${originalTitle} edited`;
  await firstColumn.getByPlaceholder("Card title").fill(originalTitle);
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(originalTitle)).toBeVisible();

  await firstColumn.getByRole("button", { name: `Edit ${originalTitle}` }).click();
  await firstColumn.getByLabel("Card title").fill(editedTitle);
  await firstColumn.getByLabel("Card details").fill("Edited via e2e.");
  await firstColumn.getByRole("button", { name: "Save" }).click();
  await expect(firstColumn.getByText(editedTitle)).toBeVisible();

  const card = firstColumn.locator("article").filter({ hasText: editedTitle });
  const dragHandle = card.getByRole("button", { name: `Move ${editedTitle}` });
  const targetColumn = page.locator('[data-testid^="column-"]').nth(4);
  const dropArea = targetColumn;
  const handleBox = await dragHandle.boundingBox();
  const dropBox = await dropArea.boundingBox();
  if (!handleBox || !dropBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }
  await page.mouse.move(
    handleBox.x + handleBox.width / 2,
    handleBox.y + handleBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    dropBox.x + dropBox.width - 12,
    dropBox.y + dropBox.height / 2,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByText(editedTitle)).toBeVisible();

  await page.reload();
  await expect(
    firstColumn.getByRole("button", {
      name: `Edit ${renamedColumn} column title`,
    })
  ).toBeVisible();
  await expect(
    page.locator('[data-testid^="column-"]').nth(4).getByText(editedTitle)
  ).toBeVisible();

  await page
    .getByRole("button", { name: `Delete ${editedTitle}` })
    .click();
  await expect(page.getByText(editedTitle)).toBeHidden();
  await page.reload();
  await expect(page.getByText(editedTitle)).toBeHidden();
});
