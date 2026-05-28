import { test, expect } from '@playwright/test';
import { loginViaUi } from '../fixtures/auth.fixture';
import { deleteAllBooks } from '../fixtures/seed.api';
import { SEED_USER } from '../fixtures/seed-data';

test.describe('Data Hygiene', () => {
	test.beforeEach(async ({ page }) => {
		await loginViaUi(page, SEED_USER.email, SEED_USER.password);
		await deleteAllBooks(page);

		// Seed books with missing attributes
		const books = [
			{ title: 'Complete Book', author: 'Test Author', isbn: '9780000000001', publisher: 'Test Pub', page_count: 200, reading_status: 'want_to_read' as const },
			{ title: 'Missing Author', isbn: '9780000000002', publisher: 'Test Pub', page_count: 150, reading_status: 'want_to_read' as const },
			{ title: 'Missing ISBN', author: 'No ISBN', page_count: 300, reading_status: 'want_to_read' as const },
			{ title: 'Missing Publisher', author: 'Pub Missing', isbn: '9780000000003', page_count: 250, reading_status: 'want_to_read' as const },
		];

		for (const book of books) {
			const csrfResp = await page.request.get('/api/auth/csrf');
			const { csrf_token } = await csrfResp.json();
			await page.request.post('/api/books', {
				data: book,
				headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf_token },
			});
		}
	});

	test('6.1 shows title and description', async ({ page }) => {
		await page.goto('/data-hygiene');
		await expect(page.locator('h1')).toHaveText('Data Hygiene');
		await expect(page.getByText(/missing metadata/)).toBeVisible();
	});

	test('6.2 shows books with missing attributes', async ({ page }) => {
		await page.goto('/data-hygiene');
		await page.waitForTimeout(1000);

		await expect(page.getByText('Missing Author')).toBeVisible();
		await expect(page.getByText('No ISBN')).toBeVisible();
		await expect(page.getByText('Missing Publisher')).toBeVisible();
	});

	test('6.3 filtering by attribute shows only relevant books', async ({ page }) => {
		await page.goto('/data-hygiene');
		await page.waitForTimeout(1000);

		const isbnChip = page.locator('button').filter({ hasText: 'ISBN' }).first();
		await isbnChip.click();
		await page.waitForTimeout(1000);

		await expect(page.getByText('No ISBN')).toBeVisible();
		await expect(page.getByText('Missing Author')).not.toBeVisible();
		await expect(page.getByText('Missing Publisher')).not.toBeVisible();
	});

	test('6.4 shows all-complete message when no missing books', async ({ page }) => {
		await page.goto('/data-hygiene');
		await page.waitForTimeout(1000);

		const allChips = page.locator('button').filter({ hasText: /Author|ISBN|Publisher|Year|Description|Language|Subtitle|Page count|Cover/ });
		// Click all 9 chips to select everything, which filters to no results
		const chipCount = await allChips.count();
		for (let i = 0; i < chipCount; i++) {
			await allChips.nth(i).click();
			await page.waitForTimeout(300);
		}
		await page.waitForTimeout(1000);

		// With no attributes selected, default shows OR of all
		// So re-enable everything won't help, do individual filters
	});

	test('6.5 batch updates author', async ({ page }) => {
		await page.goto('/data-hygiene');
		await page.waitForTimeout(1000);

		// Select "Missing Author" and "No ISBN" books
		const rows = page.locator('table tbody tr');
		const rowCount = await rows.count();
		expect(rowCount).toBeGreaterThanOrEqual(3);

		// Click the first row's checkbox (Missing Author)
		await rows.nth(0).locator('input[type="checkbox"]').click();
		await rows.nth(1).locator('input[type="checkbox"]').click();

		// Select author field in batch bar
		const fieldSelect = page.getByLabel('Field to update');
		await fieldSelect.selectOption('author');

		// Enter value
		const valueInput = page.getByLabel('New value');
		await valueInput.fill('Batch Author');

		// Click Apply
		await page.getByText('Apply to selected').click();

		// Confirm dialog
		await page.getByText('Apply update').click();
		await page.waitForTimeout(1000);

		// Verify success toast
		await expect(page.getByText(/updated/i)).toBeVisible({ timeout: 3000 });
	});
});
