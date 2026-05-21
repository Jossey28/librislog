import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import Toaster from './Toaster.svelte';

// Create mock store inside a helper that can be used by both mock and tests
const createMockToasts = () => writable<Array<{ id: number; message: string; level: string }>>([]);

vi.mock('$lib/toasts', async () => {
	const { writable } = await import('svelte/store');
	const store = writable<Array<{ id: number; message: string; level: string }>>([]);
	return {
		toasts: {
			subscribe: store.subscribe,
			add: vi.fn(),
			remove: vi.fn()
		},
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		ToastLevel: {} as any,
		// Expose for tests
		_mockStore: store
	};
});

import { toasts, _mockStore } from '$lib/toasts';

describe('Toaster', () => {
	afterEach(() => {
		_mockStore.set([]);
		cleanup();
		vi.clearAllMocks();
	});

	it('renders nothing when no toasts', () => {
		render(Toaster);
		expect(screen.queryByRole('alert')).not.toBeInTheDocument();
	});

	it('renders a toast message', () => {
		_mockStore.set([{ id: 1, message: 'Book saved', level: 'success' }]);
		render(Toaster);
		expect(screen.getByText('Book saved')).toBeInTheDocument();
	});

	it('renders multiple toasts', () => {
		_mockStore.set([
			{ id: 1, message: 'First toast', level: 'info' },
			{ id: 2, message: 'Second toast', level: 'warning' }
		]);
		render(Toaster);
		expect(screen.getByText('First toast')).toBeInTheDocument();
		expect(screen.getByText('Second toast')).toBeInTheDocument();
	});

	it('calls remove when dismiss button clicked', async () => {
		_mockStore.set([{ id: 42, message: 'Dismiss me', level: 'error' }]);
		render(Toaster);

		const dismissBtn = screen.getByRole('button', { name: 'Dismiss' });
		await fireEvent.click(dismissBtn);

		expect(toasts.remove).toHaveBeenCalledWith(42);
	});

	it('applies correct alert class for error level', () => {
		_mockStore.set([{ id: 1, message: 'Error!', level: 'error' }]);
		const { container } = render(Toaster);
		expect(container.querySelector('.alert-error')).toBeInTheDocument();
	});

	it('applies correct alert class for success level', () => {
		_mockStore.set([{ id: 1, message: 'Success!', level: 'success' }]);
		const { container } = render(Toaster);
		expect(container.querySelector('.alert-success')).toBeInTheDocument();
	});

	it('applies correct alert class for warning level', () => {
		_mockStore.set([{ id: 1, message: 'Warning!', level: 'warning' }]);
		const { container } = render(Toaster);
		expect(container.querySelector('.alert-warning')).toBeInTheDocument();
	});

	it('applies correct alert class for info level', () => {
		_mockStore.set([{ id: 1, message: 'Info!', level: 'info' }]);
		const { container } = render(Toaster);
		expect(container.querySelector('.alert-info')).toBeInTheDocument();
	});
});
