import { writable } from 'svelte/store';

export type ToastLevel = 'error' | 'warning' | 'success' | 'info';

export interface Toast {
	id: number;
	message: string;
	level: ToastLevel;
}

let _id = 0;
const { subscribe, update } = writable<Toast[]>([]);

function add(message: string, level: ToastLevel = 'error', duration = 4000) {
	const id = ++_id;
	update((toasts) => [...toasts, { id, message, level }]);
	setTimeout(() => remove(id), duration);
}

function remove(id: number) {
	update((toasts) => toasts.filter((t) => t.id !== id));
}

export const toasts = { subscribe, add, remove };
