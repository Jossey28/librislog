import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import CalendarCellRenderer from './CalendarCellRenderer.svelte';

vi.mock('layerchart', async () => {
	const { default: MockRect } = await import('$lib/test/mocks/Rect.svelte');
	return {
		Rect: MockRect,
		getChartContext: vi.fn(() => ({
			tooltip: { show: vi.fn(), hide: vi.fn() }
		}))
	};
});

describe('CalendarCellRenderer', () => {
	const cells = [
		{ x: 0, y: 0, data: { date: '2024-01-01', pages: 10 } },
		{ x: 1, y: 0, data: { date: '2024-01-02', pages: 0 } },
		{ x: 2, y: 0, data: { date: '2024-01-03' } }
	];

	it('renders rects for each cell', () => {
		render(CalendarCellRenderer, {
			props: { cells, cellSize: [20, 20], maxPages: 20 }
		});
		expect(document.querySelectorAll('[role="gridcell"]')).toHaveLength(3);
	});

	it('handles zero and undefined pages', () => {
		render(CalendarCellRenderer, {
			props: { cells, cellSize: [20, 20], maxPages: 20 }
		});
		const rects = document.querySelectorAll('[role="gridcell"]');
		expect(rects).toHaveLength(3);
	});

	it('uses maxPages of 1', () => {
		render(CalendarCellRenderer, {
			props: {
				cells: [{ x: 0, y: 0, data: { date: '2024-01-01', pages: 5 } }],
				cellSize: [20, 20],
				maxPages: 1
			}
		});
		expect(document.querySelector('[role="gridcell"]')).toBeInTheDocument();
	});
});
