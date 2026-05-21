import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import AutoSearchCoverModal from './AutoSearchCoverModal.svelte';

describe('AutoSearchCoverModal', () => {
	const onCancel = vi.fn();
	const onSelect = vi.fn();

	const candidates = [
		{ source: 'AbeBooks', url: 'https://example.com/1.jpg', available: true, filesize: 512, width: 200, height: 300 },
		{ source: 'OpenLibrary', url: 'https://example.com/2.jpg', available: true, filesize: 1024 * 1024, width: 400, height: 600 },
		{ source: 'Amazon', url: 'https://example.com/3.jpg', available: false, filesize: null, width: null, height: null }
	];

	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('does not render when closed', () => {
		render(AutoSearchCoverModal, {
			props: { open: false, loading: false, candidates: [], onCancel, onSelect }
		});
		expect(screen.queryByText('Auto-search covers')).not.toBeInTheDocument();
	});

	it('renders in loading state', () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: true, candidates: [], onCancel, onSelect }
		});
		expect(screen.getByText('Auto-search covers')).toBeInTheDocument();
		expect(screen.getByText('Searching cover sources...')).toBeInTheDocument();
		expect(document.querySelector('.loading-spinner')).toBeInTheDocument();
	});

	it('renders error message', () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates: [], error: 'Search failed', onCancel, onSelect }
		});
		expect(screen.getByText('Search failed')).toBeInTheDocument();
	});

	it('renders no candidates message', () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates: [], error: null, onCancel, onSelect }
		});
		expect(screen.getByText('No cover candidates were found for this ISBN.')).toBeInTheDocument();
	});

	it('renders available candidates and filters unavailable', () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates, error: null, onCancel, onSelect }
		});
		const imgButtons = screen.getAllByRole('button').filter((b) =>
			b.querySelector('img')
		);
		expect(imgButtons).toHaveLength(2);
	});

	it('shows filesize and resolution labels', () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates, error: null, onCancel, onSelect }
		});
		expect(document.body.textContent).toContain('512 B');
		expect(document.body.textContent).toContain('1.0 MB');
		expect(document.body.textContent).toContain('200x300');
		expect(document.body.textContent).toContain('400x600');
	});

	it('calls onSelect when candidate clicked', async () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates, error: null, onCancel, onSelect }
		});
		const imgButtons = screen.getAllByRole('button').filter((b) =>
			b.querySelector('img')
		);
		await fireEvent.click(imgButtons[0]);
		expect(onSelect).toHaveBeenCalledOnce();
		expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ source: 'AbeBooks' }));
	});

	it('calls onCancel when close button clicked', async () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates: [], error: null, onCancel, onSelect }
		});
		const closeBtn = screen.getAllByRole('button').find((b) =>
			b.getAttribute('aria-label') === 'Close'
		);
		expect(closeBtn).toBeTruthy();
		await fireEvent.click(closeBtn!);
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('calls onCancel when cancel button clicked', async () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates: [], error: null, onCancel, onSelect }
		});
		await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('calls onCancel when backdrop clicked', async () => {
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates: [], error: null, onCancel, onSelect }
		});
		await fireEvent.click(document.querySelector('.modal-backdrop'));
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('shows n/a for missing filesize and resolution', () => {
		const candidateNoMeta = [
			{ source: 'Test', url: 'https://example.com/x.jpg', available: true, filesize: null, width: null, height: null }
		];
		render(AutoSearchCoverModal, {
			props: { open: true, loading: false, candidates: candidateNoMeta, error: null, onCancel, onSelect }
		});
		expect(document.body.textContent).toContain('n/a - n/a');
	});
});
