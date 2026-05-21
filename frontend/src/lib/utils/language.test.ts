import { describe, it, expect } from 'vitest';
import { formatLanguageCode } from '$lib/utils/language';

describe('formatLanguageCode', () => {
	it('returns dash for null', () => {
		expect(formatLanguageCode(null, 'en')).toBe('-');
	});

	it('returns dash for undefined', () => {
		expect(formatLanguageCode(undefined, 'en')).toBe('-');
	});

	it('returns dash for empty string', () => {
		expect(formatLanguageCode('', 'en')).toBe('-');
	});

	it('returns dash for whitespace-only string', () => {
		expect(formatLanguageCode('   ', 'en')).toBe('-');
	});

	it('formats valid language code', () => {
		expect(formatLanguageCode('en', 'en')).toBe('English');
	});

	it('formats uppercase input to proper display name', () => {
		expect(formatLanguageCode('DE', 'en')).toBe('German');
	});

	it('returns formatted code for unknown language', () => {
		const result = formatLanguageCode('xx', 'en');
		// Intl.DisplayNames may return the code itself or uppercase it
		expect(result).toMatch(/xx/i);
	});
});
