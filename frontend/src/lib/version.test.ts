import { describe, it, expect } from 'vitest';
import { version, gitSha } from './version';

describe('version', () => {
	it('exports version string', () => {
		expect(typeof version).toBe('string');
		expect(version.length).toBeGreaterThan(0);
	});

	it('exports gitSha string', () => {
		expect(typeof gitSha).toBe('string');
		expect(gitSha.length).toBeGreaterThan(0);
	});
});
