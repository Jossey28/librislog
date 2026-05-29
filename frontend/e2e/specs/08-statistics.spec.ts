import { test, expect } from '@playwright/test';
import { loginViaUi } from '../fixtures/auth.fixture';
import { seedBooks, deleteAllBooks } from '../fixtures/seed.api';
import { SEED_USER, SEED_BOOKS } from '../fixtures/seed-data';

test.describe('Statistics', () => {
	test.beforeEach(async ({ page }) => {
		await loginViaUi(page, SEED_USER.email, SEED_USER.password);
		await deleteAllBooks(page);
		await seedBooks(page, SEED_BOOKS);
	});

	test('8.1 statistics page loads', async ({ page }) => {
		await page.goto('/statistics');
		await page.waitForTimeout(2000);
		const body = page.locator('body');
		await expect(body).toContainText(/total|books|pages|rating|read/i);
	});

	test('8.2 rating statistics are displayed', async ({ page }) => {
		await page.goto('/statistics');
		await page.waitForTimeout(2000);

		await expect(page.getByText('Books with Rating')).toBeVisible();
		await expect(page.getByText('Books without Rating')).toBeVisible();
		await expect(page.getByText('Avg Rating')).toBeVisible();

		await expect(page.getByText('Top Rated')).toBeVisible();
		await expect(page.getByText('Worst Rated')).toBeVisible();

		await expect(page.getByText('To Kill a Mockingbird')).toBeVisible();
		await expect(page.getByText('1984')).toBeVisible();
		await expect(page.getByText('The Great Gatsby')).toBeVisible();
		await expect(page.getByText('Brave New World')).toBeVisible();
	});
});
