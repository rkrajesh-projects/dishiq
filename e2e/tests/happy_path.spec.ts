import { test, expect } from '@playwright/test';

test('Happy Path: Search -> Recipe -> Grocery -> Cook -> Feedback', async ({ page }) => {
  // Capture all console errors so we see exact crash messages in the report
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  // 1. Search for a recipe
  await page.goto('/');
  await page.getByPlaceholder('Search recipes by dish, ingredient or craving...').fill('Paneer');
  await page.keyboard.press('Enter');
  
  // Wait for search results and click the "View Recipe" link (not the inert heading text)
  await expect(page.getByText('Paneer Bhurji').first()).toBeVisible({ timeout: 15000 });
  await page.getByRole('link', { name: /view recipe/i }).first().click();
  
  // 2. Open recipe, ingredients parsed, pantry checked
  await expect(page.getByRole('heading', { name: /ingredients/i })).toBeVisible({ timeout: 15000 });
  
  // 3. Products matched, prices compared, cart recommended
  await page.locator('a[href^="/grocery?recipeId="]').click();
  await expect(page.getByRole('heading', { name: /grocery product matching/i })).toBeVisible({ timeout: 15000 });
  await expect(page.getByText('Best Cart')).toBeVisible({ timeout: 30000 });
  
  // 4. Start cooking session
  await page.goBack();
  await page.getByRole('button', { name: /start cooking/i }).click();
  
  // If the cooking page crashes, the local CookingErrorBoundary will render the real error
  // message in data-testid="cooking-crash-message". Check for it and fail with detail.
  const crashMessage = page.getByTestId('cooking-crash-message');
  const cookingStep = page.getByText(/step 1 of/i);
  
  // Wait for either the cooking step counter (success) or the crash message (failure)
  await Promise.race([
    expect(cookingStep).toBeVisible({ timeout: 15000 }),
    expect(crashMessage).toBeVisible({ timeout: 15000 }).then(async () => {
      const errorText = await crashMessage.textContent();
      const stackEl = page.getByTestId('cooking-crash-stack');
      const stackText = await stackEl.textContent().catch(() => '(stack unavailable)');
      throw new Error(
        `CookingPage crashed with: "${errorText}"\n\nStack:\n${stackText}\n\nConsole errors:\n${consoleErrors.join('\n')}`
      );
    }),
  ]);

  // 5. Steps progress
  await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 15000 });
  
  // Click "Next Step" until the last step shows "Complete Cooking"
  while (await page.getByRole('button', { name: /next step/i }).isVisible()) {
    await page.getByRole('button', { name: /next step/i }).click();
    await page.waitForTimeout(500);
  }
  
  // Click "Complete Cooking" (only appears on the last step)
  await page.getByRole('button', { name: /complete cooking/i }).click();

  // The session is now complete, confirm the success heading
  await expect(page.getByText(/cooking complete/i)).toBeVisible({ timeout: 15000 });
  
  // 6. Feedback form
  await expect(page.getByText('How was your cooking experience?')).toBeVisible({ timeout: 15000 });

  // Select a rating (required — feedback is blocked if rating === 0)
  await page.getByRole('button', { name: /rate 5 stars/i }).click();

  // Submit feedback
  await page.getByRole('button', { name: /submit feedback/i }).click();
  
  // Handle both possible outcomes (fresh success OR already submitted)
  const alreadySubmitted = page.getByText(/feedback already submitted/i);
  const thankYou = page.getByText(/thank you/i);
  await expect(alreadySubmitted.or(thankYou)).toBeVisible({ timeout: 10000 });
});
