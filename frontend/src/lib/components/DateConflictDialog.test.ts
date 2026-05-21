import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import DateConflictDialog from './DateConflictDialog.svelte';

describe('DateConflictDialog', () => {
	const onKeep = vi.fn();
	const onUseSuggested = vi.fn();
	const onCancel = vi.fn();

	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('does not render when closed', () => {
		render(DateConflictDialog, {
			props: { open: false, existingDate: '2024-01-01', suggestedDate: '2024-01-15' }
		});
		expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
	});

	it('renders date_started conflict with buttons', () => {
		render(DateConflictDialog, {
			props: {
				open: true,
				field: 'date_started',
				existingDate: '2024-01-01',
				suggestedDate: '2024-01-15',
				onKeep,
				onUseSuggested,
				onCancel
			}
		});
		expect(document.body.textContent).toContain('Start date already set');
		const buttons = document.querySelectorAll('.modal-action button');
		expect(buttons).toHaveLength(3);
	});

	it('renders date_finished conflict with buttons', () => {
		render(DateConflictDialog, {
			props: {
				open: true,
				field: 'date_finished',
				existingDate: '2024-01-01',
				suggestedDate: '2024-01-15',
				onKeep,
				onUseSuggested,
				onCancel
			}
		});
		expect(document.body.textContent).toContain('Finish date already set');
		const buttons = document.querySelectorAll('.modal-action button');
		expect(buttons).toHaveLength(3);
	});

	it('renders started_after_finished conflict with extra info', () => {
		render(DateConflictDialog, {
			props: {
				open: true,
				field: 'started_after_finished',
				existingDate: '2024-02-01',
				suggestedDate: '2024-01-15',
				onKeep,
				onUseSuggested,
				onCancel
			}
		});
		expect(document.body.textContent).toContain('Book was already finished');
		const buttons = document.querySelectorAll('.modal-action button');
		expect(buttons).toHaveLength(3);
		expect(document.querySelectorAll('sup')).toHaveLength(4);
		expect(document.body.textContent).toContain('Keeps the finish date');
		expect(document.body.textContent).toContain('Removes the finish date');
	});

	it('calls onCancel when cancel button clicked', async () => {
		render(DateConflictDialog, {
			props: {
				open: true,
				existingDate: '2024-01-01',
				suggestedDate: '2024-01-15',
				onKeep,
				onUseSuggested,
				onCancel
			}
		});
		const buttons = screen.getAllByRole('button');
		await fireEvent.click(buttons[0]); // cancel is first
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('calls onKeep when keep button clicked', async () => {
		render(DateConflictDialog, {
			props: {
				open: true,
				existingDate: '2024-01-01',
				suggestedDate: '2024-01-15',
				onKeep,
				onUseSuggested,
				onCancel
			}
		});
		const buttons = screen.getAllByRole('button');
		await fireEvent.click(buttons[1]); // keep is second
		expect(onKeep).toHaveBeenCalledOnce();
	});

	it('calls onUseSuggested when use new button clicked', async () => {
		render(DateConflictDialog, {
			props: {
				open: true,
				existingDate: '2024-01-01',
				suggestedDate: '2024-01-15',
				onKeep,
				onUseSuggested,
				onCancel
			}
		});
		const buttons = screen.getAllByRole('button');
		await fireEvent.click(buttons[2]); // useSuggested is third
		expect(onUseSuggested).toHaveBeenCalledOnce();
	});
});
