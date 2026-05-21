import { describe, it, expect } from 'vitest';
import {
	getPasswordChecks,
	passwordChecksPassed,
	passwordStrengthPercent,
	passwordStrengthClass,
	complexityRequirementLabels,
	passwordPattern
} from './password';

describe('password', () => {
	describe('getPasswordChecks', () => {
		it('returns all false for empty password', () => {
			const checks = getPasswordChecks('');
			expect(checks).toEqual({
				minLength: false,
				hasUppercase: false,
				hasLowercase: false,
				hasNumber: false,
				hasSpecial: false
			});
		});

		it('detects minimum length', () => {
			expect(getPasswordChecks('short').minLength).toBe(false);
			expect(getPasswordChecks('longenough').minLength).toBe(true);
		});

		it('detects uppercase', () => {
			expect(getPasswordChecks('lowercase').hasUppercase).toBe(false);
			expect(getPasswordChecks('Uppercase').hasUppercase).toBe(true);
		});

		it('detects lowercase', () => {
			expect(getPasswordChecks('UPPERCASE').hasLowercase).toBe(false);
			expect(getPasswordChecks('Lowercase').hasLowercase).toBe(true);
		});

		it('detects numbers', () => {
			expect(getPasswordChecks('nonumbers').hasNumber).toBe(false);
			expect(getPasswordChecks('has1number').hasNumber).toBe(true);
		});

		it('detects special characters', () => {
			expect(getPasswordChecks('nospecial').hasSpecial).toBe(false);
			expect(getPasswordChecks('has!special').hasSpecial).toBe(true);
		});

		it('returns all true for strong password', () => {
			const checks = getPasswordChecks('Strong1!');
			expect(checks.minLength).toBe(true);
			expect(checks.hasUppercase).toBe(true);
			expect(checks.hasLowercase).toBe(true);
			expect(checks.hasNumber).toBe(true);
			expect(checks.hasSpecial).toBe(true);
		});
	});

	describe('passwordChecksPassed', () => {
		it('returns false when any check fails', () => {
			expect(passwordChecksPassed(getPasswordChecks('weak'))).toBe(false);
		});

		it('returns true when all checks pass', () => {
			expect(passwordChecksPassed(getPasswordChecks('Strong1!'))).toBe(true);
		});
	});

	describe('passwordStrengthPercent', () => {
		it('returns 0 for no checks passed', () => {
			expect(passwordStrengthPercent(getPasswordChecks(''))).toBe(0);
		});

	it('returns 20 for one check passed', () => {
		expect(passwordStrengthPercent(getPasswordChecks('a'))).toBe(20);
	});

		it('returns 100 for all checks passed', () => {
			expect(passwordStrengthPercent(getPasswordChecks('Strong1!'))).toBe(100);
		});
	});

	describe('passwordStrengthClass', () => {
	it('returns progress-error for 0-2 checks', () => {
		expect(passwordStrengthClass(getPasswordChecks(''))).toBe('progress-error');
		expect(passwordStrengthClass(getPasswordChecks('ab'))).toBe('progress-error');
		expect(passwordStrengthClass(getPasswordChecks('Abcdef'))).toBe('progress-error');
	});

	it('returns progress-warning for 3-4 checks', () => {
		expect(passwordStrengthClass(getPasswordChecks('Abcdefgh1'))).toBe('progress-warning');
		expect(passwordStrengthClass(getPasswordChecks('abcdefgh1!'))).toBe('progress-warning');
	});

		it('returns progress-success for 5 checks', () => {
			expect(passwordStrengthClass(getPasswordChecks('Strong1!'))).toBe('progress-success');
		});
	});

	describe('complexityRequirementLabels', () => {
		it('returns all 5 requirements', () => {
			const t = (key: string) => key;
			const labels = complexityRequirementLabels(t);
			expect(labels).toHaveLength(5);
			expect(labels[0]).toEqual({ key: 'minLength', label: 'password.minLength' });
			expect(labels[4]).toEqual({ key: 'hasSpecial', label: 'password.special' });
		});
	});

	describe('passwordPattern', () => {
		it('is a valid regex pattern string', () => {
			expect(passwordPattern).toBeDefined();
			expect(passwordPattern.length).toBeGreaterThan(0);
		});
	});
});
