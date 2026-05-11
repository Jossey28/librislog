import type {
	Book,
	BookImportCandidate,
	StatusTransitionRequest,
	StatusTransitionResponse,
	ImportSearchMode,
	ReadingStatus,
	SearchStage,
	SortField,
	SortOrder
} from './types';

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		headers: { 'Content-Type': 'application/json', ...options?.headers },
		...options
	});
	if (!res.ok) {
		const detail = await res.json().catch(() => ({}));
		throw new Error(detail?.detail ?? `HTTP ${res.status}`);
	}
	if (res.status === 204) return undefined as T;
	return res.json() as Promise<T>;
}

export const api = {
	books: {
		list(params?: {
			status?: ReadingStatus;
			q?: string;
			sort?: SortField;
			order?: SortOrder;
			smart_sort?: boolean;
		}): Promise<Book[]> {
			const qs = new URLSearchParams();
			if (params?.status) qs.set('status', params.status);
			if (params?.q) qs.set('q', params.q);
			if (params?.sort) qs.set('sort', params.sort);
			if (params?.order) qs.set('order', params.order);
			if (params?.smart_sort !== undefined) qs.set('smart_sort', String(params.smart_sort));
			const query = qs.toString() ? `?${qs}` : '';
			return request<Book[]>(`/books${query}`);
		},

		get(id: number): Promise<Book> {
			return request<Book>(`/books/${id}`);
		},

		create(data: Partial<Book>): Promise<Book> {
			return request<Book>('/books', { method: 'POST', body: JSON.stringify(data) });
		},

		update(id: number, data: Partial<Book>): Promise<Book> {
			return request<Book>(`/books/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
		},

		transitionStatus(id: number, data: StatusTransitionRequest): Promise<StatusTransitionResponse> {
			return request<StatusTransitionResponse>(`/books/${id}/transition-status`, {
				method: 'POST',
				body: JSON.stringify(data)
			});
		},

		delete(id: number): Promise<void> {
			return request<void>(`/books/${id}`, { method: 'DELETE' });
		}
	},

	covers: {
		async upload(file: File): Promise<string> {
			const form = new FormData();
			form.append('file', file);
			const res = await fetch(`${BASE}/covers/upload`, { method: 'POST', body: form });
			if (!res.ok) {
				const detail = await res.json().catch(() => ({}));
				throw new Error((detail as { detail?: string })?.detail ?? `HTTP ${res.status}`);
			}
			const data = (await res.json()) as { cover_url: string };
			return data.cover_url;
		}
	},

	import: {
		search(q: string, type: 'title' | 'isbn' = 'title'): Promise<BookImportCandidate[]> {
			return request<BookImportCandidate[]>(
				`/import/search?q=${encodeURIComponent(q)}&type=${type}`
			);
		},

		importBook(candidate: BookImportCandidate, status: ReadingStatus = 'want_to_read'): Promise<Book> {
			return request<Book>('/import', {
				method: 'POST',
				body: JSON.stringify({ candidate, reading_status: status })
			});
		},

		async *searchStream(
			q: string,
			type: 'title' | 'isbn' = 'title',
			mode: ImportSearchMode = 'auto'
		): AsyncGenerator<SearchStage> {
			const res = await fetch(
				`${BASE}/import/search/stream?q=${encodeURIComponent(q)}&type=${type}&mode=${mode}`
			);
			if (!res.ok || !res.body) {
				const detail = await res.json().catch(() => ({}));
				throw new Error((detail as { detail?: string })?.detail ?? `HTTP ${res.status}`);
			}
			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() ?? '';
				for (const line of lines) {
					if (line.startsWith('data: ')) {
						const text = line.slice(6).trim();
						if (text) yield JSON.parse(text) as SearchStage;
					}
				}
			}
		}
	}
};
