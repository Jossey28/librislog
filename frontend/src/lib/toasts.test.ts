import { describe, it, expect, vi, beforeEach } from 'vitest';
import { toasts } from './toasts';
import { get } from 'svelte/store';

describe('toasts', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		// Reset toasts store by removing all
		const current = get(toasts);
		current.forEach((t) => toasts.remove(t.id));
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('starts empty', () => {
		expect(get(toasts)).toEqual([]);
	});

	it('adds a toast with default level', () => {
		toasts.add('Hello world');
		const list = get(toasts);
		expect(list).toHaveLength(1);
		expect(list[0].message).toBe('Hello world');
		expect(list[0].level).toBe('error');
	});

	it('adds a toast with custom level and duration', () => {
		toasts.add('Success', 'success', 2000);
		const list = get(toasts);
		expect(list).toHaveLength(1);
		expect(list[0].message).toBe('Success');
		expect(list[0].level).toBe('success');
	});

	it('auto-removes toast after duration', () => {
		toasts.add('Temp', 'info', 1000);
		expect(get(toasts)).toHaveLength(1);
		vi.advanceTimersByTime(1000);
		expect(get(toasts)).toHaveLength(0);
	});

	it('removes toast manually', () => {
		toasts.add('Stay');
		toasts.add('Go');
		const list = get(toasts);
		expect(list).toHaveLength(2);
		toasts.remove(list[1].id);
		expect(get(toasts)).toHaveLength(1);
		expect(get(toasts)[0].message).toBe('Stay');
	});

	it('assigns unique ids', () => {
		toasts.add('First');
		toasts.add('Second');
		const list = get(toasts);
		expect(list[0].id).not.toBe(list[1].id);
	});
});
