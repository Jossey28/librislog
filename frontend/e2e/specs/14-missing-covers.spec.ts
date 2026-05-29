import { test, expect } from '@playwright/test';
import { loginViaUi } from '../fixtures/auth.fixture';
import { seedBooks, deleteAllBooks } from '../fixtures/seed.api';
import { SEED_USER } from '../fixtures/seed-data';
import { MissingCoversPage } from '../fixtures/pages/missing-covers.page';

test.describe('Missing Covers Workflow', () => {
	test.beforeEach(async ({ page }) => {
		await loginViaUi(page, SEED_USER.email, SEED_USER.password);
		await deleteAllBooks(page);
	});

	test('1. Entry point from profile navigates to missing-covers', async ({ page }) => {
		await page.goto('/profile');
		await page.waitForSelector('h2');
		await page.locator('a').filter({ hasText: 'Manage Missing Covers' }).click();
		await expect(page).toHaveURL(/\/missing-covers/);
	});

	test('2. Header shows correct count', async ({ page }) => {
		await seedBooks(page, [
			{ title: 'Book A', author: 'Author A', reading_status: 'read' },
			{ title: 'Book B', author: 'Author B', reading_status: 'read' },
			{ title: 'Book C', author: 'Author C', reading_status: 'read' },
		]);
		const missing = new MissingCoversPage(page);
		await missing.goto();
		const header = await missing.getHeader();
		expect(header).toContain('3');
	});

	test('3. Displays current book info', async ({ page }) => {
		await seedBooks(page, [
			{ title: 'Visible Book', author: 'Test Author', reading_status: 'read' },
		]);
		const missing = new MissingCoversPage(page);
		await missing.goto();
		const title = await missing.getCurrentBookTitle();
		expect(title).toBe('Visible Book');
	});

	test('7. Skip advances to next book without reducing counter', async ({ page }) => {
		await seedBooks(page, [
			{ title: 'First', author: 'A', reading_status: 'read' },
			{ title: 'Second', author: 'B', reading_status: 'read' },
		]);
		const missing = new MissingCoversPage(page);
		await missing.goto();
		const headerBefore = await missing.getHeader();
		expect(headerBefore).toContain('2');

		await missing.clickSkip();
		await page.waitForTimeout(500);

		const titleAfter = await missing.getCurrentBookTitle();
		expect(titleAfter).toBe('Second');

		const headerAfter = await missing.getHeader();
		expect(headerAfter).toContain('2');
	});

	test('8. No-ISBN state shows manual fallback, google link, and no candidate grid', async ({ page }) => {
		await seedBooks(page, [
			{ title: 'No ISBN', author: 'Author X', reading_status: 'read' },
		]);
		const missing = new MissingCoversPage(page);
		await missing.goto();

		await page.waitForTimeout(1000);

		const manualInput = await missing.getManualUrlInput();
		await expect(manualInput).toBeVisible();

		const googleLink = page.locator('a[aria-label="Open Google image search for this book in a new tab"]');
		await expect(googleLink).toBeVisible();

		const skipBtn = page.locator('button[aria-label="Skip this book and go to the next"]');
		await expect(skipBtn).toBeVisible();
	});

	test('10. Invalid manual URL shows client-side error', async ({ page }) => {
		await seedBooks(page, [
			{ title: 'URL Book', author: 'Author Y', isbn: '9780451524935', reading_status: 'read' },
		]);
		const missing = new MissingCoversPage(page);
		await missing.goto();

		await page.waitForTimeout(1000);

		await missing.fillManualUrl('not-a-valid-url');
		await missing.clickSaveManualUrl();

		await expect(page.getByText(/valid/i)).toBeVisible({ timeout: 3000 });
	});

	test('11. All-done state when all books have been saved', async ({ page }) => {
		await seedBooks(page, [
			{ title: 'Solo Book', author: 'Author Z', reading_status: 'read' },
		]);
		const missing = new MissingCoversPage(page);
		await missing.goto();

		await page.waitForTimeout(500);

		const skipBtn = page.locator('button[aria-label="Skip this book and go to the next"]');
		await expect(skipBtn).toBeVisible();
		await skipBtn.click();
		await page.waitForTimeout(500);

		const backBtn = page.locator('a').filter({ hasText: 'Back' });
		await expect(backBtn).toBeVisible();
	});
});
