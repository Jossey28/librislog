import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import SearchBar from './SearchBar.svelte';

describe('SearchBar', () => {
	beforeEach(() => {
		vi.useFakeTimers({ shouldAdvanceTime: true });
	});

	afterEach(() => {
		vi.useRealTimers();
		cleanup();
	});

	it('renders with default placeholder', () => {
		render(SearchBar, { props: { value: '' } });
		expect(screen.getByPlaceholderText('Search')).toBeInTheDocument();
	});

	it('renders with custom placeholder', () => {
		render(SearchBar, { props: { value: '', placeholder: 'Find books...' } });
		expect(screen.getByPlaceholderText('Find books...')).toBeInTheDocument();
	});

	it('calls onSearch after debounce when typing', async () => {
		const onSearch = vi.fn();
		render(SearchBar, { props: { value: '', onSearch } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'dune' } });

		expect(onSearch).not.toHaveBeenCalled();

		await vi.advanceTimersByTimeAsync(300);

		expect(onSearch).toHaveBeenCalledTimes(1);
		expect(onSearch).toHaveBeenCalledWith('dune');
	});

	it('does not show clear button when value is empty', () => {
		render(SearchBar, { props: { value: '' } });
		expect(screen.queryByRole('button')).not.toBeInTheDocument();
	});

	it('shows clear button when value is not empty', () => {
		render(SearchBar, { props: { value: 'query' } });
		expect(screen.getByRole('button')).toBeInTheDocument();
	});

	it('clears value and calls onSearch when clear button clicked', async () => {
		const onSearch = vi.fn();
		render(SearchBar, { props: { value: 'query', onSearch } });

		const clearBtn = screen.getByRole('button');
		await fireEvent.click(clearBtn);

		expect(onSearch).toHaveBeenCalledWith('');
	});

	it('resets debounce timer on rapid input', async () => {
		const onSearch = vi.fn();
		render(SearchBar, { props: { value: '', onSearch } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'a' } });
		await vi.advanceTimersByTimeAsync(200);
		await fireEvent.input(input, { target: { value: 'ab' } });
		await vi.advanceTimersByTimeAsync(200);
		await fireEvent.input(input, { target: { value: 'abc' } });
		await vi.advanceTimersByTimeAsync(300);

		expect(onSearch).toHaveBeenCalledTimes(1);
		expect(onSearch).toHaveBeenCalledWith('abc');
	});
});
