import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import SuggestionInput from './SuggestionInput.svelte';

describe('SuggestionInput', () => {
	beforeEach(() => {
		vi.useFakeTimers({ shouldAdvanceTime: true });
	});

	afterEach(() => {
		vi.useRealTimers();
		cleanup();
	});

	it('renders with label', () => {
		render(SuggestionInput, { props: { value: '', label: 'Author' } });
		expect(screen.getByText('Author')).toBeInTheDocument();
	});

	it('renders with placeholder', () => {
		render(SuggestionInput, { props: { value: '', placeholder: 'Type to search...' } });
		expect(screen.getByPlaceholderText('Type to search...')).toBeInTheDocument();
	});

	it('shows suggestions after debounce', async () => {
		const fetchSuggestions = vi.fn(async () => ['Alice', 'Bob', 'Charlie']);
		render(SuggestionInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('searchbox');
		await fireEvent.input(input, { target: { value: 'Al' } });
		await vi.advanceTimersByTimeAsync(300);

		const options = screen.getAllByRole('option');
		expect(options).toHaveLength(3);
		expect(options[0]).toHaveTextContent('Alice');
	});

	it('selects suggestion on click', async () => {
		const fetchSuggestions = vi.fn(async () => ['Alice', 'Bob']);
		render(SuggestionInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('searchbox');
		await fireEvent.input(input, { target: { value: 'Al' } });
		await vi.advanceTimersByTimeAsync(300);

		const option = screen.getAllByRole('option')[0];
		await fireEvent.mouseDown(option);

		expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
	});

	it('navigates suggestions with keyboard and selects with Enter', async () => {
		const fetchSuggestions = vi.fn(async () => ['Alpha', 'Beta']);
		render(SuggestionInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('searchbox');
		await fireEvent.input(input, { target: { value: 'Al' } });
		await vi.advanceTimersByTimeAsync(300);

		await fireEvent.keyDown(input, { key: 'ArrowDown' });
		const options = screen.getAllByRole('option');
		expect(options[0]).toHaveAttribute('aria-selected', 'true');

		await fireEvent.keyDown(input, { key: 'Enter' });
		expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
	});

	it('closes suggestions on Escape', async () => {
		const fetchSuggestions = vi.fn(async () => ['result']);
		render(SuggestionInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('searchbox');
		await fireEvent.input(input, { target: { value: 'q' } });
		await vi.advanceTimersByTimeAsync(300);

		expect(screen.getByRole('listbox')).toBeInTheDocument();
		await fireEvent.keyDown(input, { key: 'Escape' });
		expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
	});

	it('shows loading spinner while fetching', async () => {
		const fetchSuggestions = vi.fn(async () => {
			await new Promise((resolve) => setTimeout(resolve, 500));
			return ['result'];
		});
		render(SuggestionInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('searchbox');
		await fireEvent.input(input, { target: { value: 'q' } });
		await vi.advanceTimersByTimeAsync(300);

		// Loading spinner uses loading-spinner class
		expect(document.querySelector('.loading-spinner')).toBeInTheDocument();
	});

	it('is disabled when disabled prop is true', () => {
		render(SuggestionInput, { props: { value: '', disabled: true } });
		expect(screen.getByRole('searchbox')).toBeDisabled();
	});

	it('does not fetch suggestions for empty input', async () => {
		const fetchSuggestions = vi.fn(async () => ['result']);
		render(SuggestionInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('searchbox');
		await fireEvent.input(input, { target: { value: '' } });
		await vi.advanceTimersByTimeAsync(300);

		expect(fetchSuggestions).not.toHaveBeenCalled();
	});
});
