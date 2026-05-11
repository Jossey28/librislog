import { describe, expect, it } from 'vitest';
import { isValidEmailFormat } from './validation';

describe('isValidEmailFormat', () => {
	it('accepts valid email addresses', () => {
		expect(isValidEmailFormat('alice@example.com')).toBe(true);
		expect(isValidEmailFormat('bob.smith+books@sub.domain.org')).toBe(true);
		expect(isValidEmailFormat('  user@domain.net  ')).toBe(true);
	});

	it('rejects invalid email addresses', () => {
		expect(isValidEmailFormat('invalid')).toBe(false);
		expect(isValidEmailFormat('missing-at.example.com')).toBe(false);
		expect(isValidEmailFormat('missing-domain@')).toBe(false);
		expect(isValidEmailFormat('has spaces@example.com')).toBe(false);
		expect(isValidEmailFormat('user@domain')).toBe(false);
	});
});
