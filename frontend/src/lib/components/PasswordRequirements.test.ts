import { describe, it, expect, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import PasswordRequirements from './PasswordRequirements.svelte';

describe('PasswordRequirements', () => {
	afterEach(() => {
		cleanup();
	});

	it('renders with empty password', () => {
		render(PasswordRequirements, { props: { password: '' } });
		expect(screen.getByText('Password requirements')).toBeInTheDocument();
		expect(screen.getByText('Not ready')).toBeInTheDocument();
	});

	it('shows all requirements', () => {
		render(PasswordRequirements, { props: { password: '' } });
		expect(screen.getByText('At least 8 characters')).toBeInTheDocument();
		expect(screen.getByText('At least one uppercase letter')).toBeInTheDocument();
		expect(screen.getByText('At least one lowercase letter')).toBeInTheDocument();
		expect(screen.getByText('At least one number')).toBeInTheDocument();
		expect(screen.getByText('At least one special character')).toBeInTheDocument();
	});

	it('shows strong enough for valid password', () => {
		render(PasswordRequirements, { props: { password: 'Strong1!' } });
		expect(screen.getByText('Strong enough')).toBeInTheDocument();
	});

	it('shows progress bar', () => {
		render(PasswordRequirements, { props: { password: 'abc' } });
		expect(document.querySelector('progress')).toBeInTheDocument();
	});

	it('shows checkmarks for passed requirements', () => {
		render(PasswordRequirements, { props: { password: 'Strong1!' } });
		const badges = document.querySelectorAll('.badge-success');
		expect(badges.length).toBeGreaterThan(0);
	});

	it('shows X marks for failed requirements', () => {
		render(PasswordRequirements, { props: { password: 'weak' } });
		const badges = document.querySelectorAll('.badge-error');
		expect(badges.length).toBeGreaterThan(0);
	});

	it('updates when password changes', () => {
		const { rerender } = render(PasswordRequirements, { props: { password: '' } });
		expect(screen.getByText('Not ready')).toBeInTheDocument();

		rerender({ password: 'Strong1!' });
		expect(screen.getByText('Strong enough')).toBeInTheDocument();
	});
});
