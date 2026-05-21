import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/svelte';
import TagInput from './TagInput.svelte';

describe('TagInput', () => {
	beforeEach(() => {
		vi.useFakeTimers({ shouldAdvanceTime: true });
	});

	afterEach(() => {
		vi.useRealTimers();
		cleanup();
	});

	it('renders tags from value prop', () => {
		render(TagInput, { props: { value: 'fiction, classic' } });

		expect(screen.getByText('fiction')).toBeInTheDocument();
		expect(screen.getByText('classic')).toBeInTheDocument();
	});

	it('adds a tag on Enter key', async () => {
		render(TagInput, { props: { value: '' } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'new-tag' } });
		await fireEvent.keyDown(input, { key: 'Enter' });

		expect(screen.getByText('new-tag')).toBeInTheDocument();
		expect(input).toHaveValue('');
	});

	it('adds a tag on comma key', async () => {
		render(TagInput, { props: { value: '' } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'comma-tag' } });
		await fireEvent.keyDown(input, { key: ',' });

		expect(screen.getByText('comma-tag')).toBeInTheDocument();
	});

	it('adds a tag on Tab key', async () => {
		render(TagInput, { props: { value: '' } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'tab-tag' } });
		await fireEvent.keyDown(input, { key: 'Tab' });

		expect(screen.getByText('tab-tag')).toBeInTheDocument();
	});

	it('removes last tag on Backspace when input is empty', async () => {
		render(TagInput, { props: { value: 'first, second' } });

		const input = screen.getByRole('textbox');
		await fireEvent.keyDown(input, { key: 'Backspace' });

		expect(screen.queryByText('second')).not.toBeInTheDocument();
		expect(screen.getByText('first')).toBeInTheDocument();
	});

	it('removes a tag when clicking its remove button', async () => {
		render(TagInput, { props: { value: 'remove-me' } });

		const removeBtn = screen.getByRole('button', { name: 'Remove' });
		await fireEvent.click(removeBtn);

		expect(screen.queryByText('remove-me')).not.toBeInTheDocument();
	});

	it('prevents duplicate tags (case-insensitive)', async () => {
		render(TagInput, { props: { value: 'Fiction' } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'fiction' } });
		await fireEvent.keyDown(input, { key: 'Enter' });

		expect(screen.getAllByText(/Fiction/i)).toHaveLength(1);
	});

	it('respects maxTagsCount', async () => {
		render(TagInput, { props: { value: 'one, two', maxTagsCount: 2 } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'three' } });
		await fireEvent.keyDown(input, { key: 'Enter' });

		expect(screen.queryByText('three')).not.toBeInTheDocument();
		expect(screen.getByText('one')).toBeInTheDocument();
		expect(screen.getByText('two')).toBeInTheDocument();
	});

	it('shows suggestions after debounce when typing', async () => {
		const fetchSuggestions = vi.fn(async () => ['fantasy', 'fiction', 'history']);

		render(TagInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'fan' } });

		expect(fetchSuggestions).not.toHaveBeenCalled(); // debounced

		await vi.advanceTimersByTimeAsync(300);

		const options = screen.getAllByRole('option');
		expect(options[0]).toHaveTextContent('fantasy');
		expect(options[1]).toHaveTextContent('fiction');
	});

	it('navigates suggestions with ArrowDown/ArrowUp and selects with Enter', async () => {
		const fetchSuggestions = vi.fn(async () => ['alpha', 'beta']);

		render(TagInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'al' } });
		await vi.advanceTimersByTimeAsync(300);

		const options1 = screen.getAllByRole('option');
		expect(options1[0]).toHaveTextContent('alpha');

		await fireEvent.keyDown(input, { key: 'ArrowDown' });
		const options = screen.getAllByRole('option');
		expect(options[0]).toHaveAttribute('aria-selected', 'true');

		await fireEvent.keyDown(input, { key: 'Enter' });

		expect(screen.getByText('alpha')).toBeInTheDocument();
		expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
	});

	it('closes suggestions on Escape', async () => {
		const fetchSuggestions = vi.fn(async () => ['result']);

		render(TagInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'q' } });
		await vi.advanceTimersByTimeAsync(300);

		const options2 = screen.getAllByRole('option');
		expect(options2[0]).toHaveTextContent('result');
		await fireEvent.keyDown(input, { key: 'Escape' });

		expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
	});

	it('disables interaction when disabled prop is true', () => {
		render(TagInput, { props: { value: 'tag', disabled: true } });

		expect(screen.getByRole('textbox')).toBeDisabled();
		expect(screen.queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument();
	});

	it('blurs without fetchSuggestions adds current input as tag', async () => {
		render(TagInput, { props: { value: '' } }); // no fetchSuggestions

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'blurred' } });
		await fireEvent.blur(input);

		expect(screen.getByText('blurred')).toBeInTheDocument();
	});
});
