import type { Page, Locator } from '@playwright/test';

export class MissingCoversPage {
	constructor(private page: Page) {}

	async goto() {
		await this.page.goto('/missing-covers');
		await this.page.waitForSelector('h1');
	}

	async getHeader(): Promise<string | null> {
		return this.page.locator('h1').textContent();
	}

	async getCurrentBookTitle(): Promise<string | null> {
		const el = this.page.locator('.text-lg.font-semibold').first();
		return el.textContent();
	}

	async getCurrentBookAuthor(): Promise<string | null> {
		const el = this.page.locator('.text-sm.text-base-content\\/70').first();
		return el.textContent();
	}

	async getCandidateGrid(): Promise<Locator> {
		return this.page.locator('.grid.grid-cols-2');
	}

	async getCandidateButtons() {
		return this.page.locator('.grid.grid-cols-2 button[type="button"]');
	}

	async selectCandidate(index: number) {
		const btns = this.getCandidateButtons();
		await btns.nth(index).click();
	}

	async clickSkip() {
		await this.page.locator('button[aria-label="Skip this book and go to the next"]').click();
	}

	async clickSaveManualUrl() {
		await this.page.locator('button').filter({ hasText: 'Save Cover' }).click();
	}

	async fillManualUrl(url: string) {
		await this.page.locator('input[type="url"]').fill(url);
	}

	async getManualUrlInput(): Promise<Locator> {
		return this.page.locator('input[type="url"]');
	}

	async clickGoogleSearchLink() {
		await this.page.locator('a[aria-label="Open Google image search for this book in a new tab"]').click();
	}

	async getBackLink(): Promise<Locator> {
		return this.page.locator('a').filter({ hasText: 'Back' });
	}

	async getKeyboardHint(): Promise<string | null> {
		return this.page.locator('text="Tip:"').textContent();
	}

	async waitForCandidates() {
		await this.page.waitForFunction(() => {
			const grid = document.querySelector('.grid.grid-cols-2');
			return grid && grid.querySelectorAll('button[type="button"]').length > 0;
		}, { timeout: 15000 });
	}
}
