# Implementation Plan: Vitest Component Tests for LibrisLog Frontend

## Goal
Add Vitest component tests to the LibrisLog frontend, covering interactive Svelte 5 components with Testing Library.

## Current State
- **Test framework**: Vitest (already installed in frontend)
- **Current tests**: 4 files testing pure utility functions only (`api.test.ts`, `date.test.ts`, `errors.test.ts`, `validation.test.ts`)
- **No component tests exist**
- **No testing library or DOM environment configured**

## Dependencies to Install

```bash
cd /home/raffael/git/librislog/frontend
npm install -D \
  @testing-library/svelte@^5 \
  @testing-library/jest-dom@^6 \
  happy-dom@^17 \
  @vitest/coverage-v8@^4
```

| Package | Purpose |
|---------|---------|
| `@testing-library/svelte` | Render Svelte components, fire events, query DOM (v5+ required for Svelte 5 runes) |
| `@testing-library/jest-dom` | Custom matchers (`toBeInTheDocument`, `toHaveAttribute`, etc.) |
| `happy-dom` | Fast DOM environment for component tests (preferred over jsdom for Vite) |
| `@vitest/coverage-v8` | Code coverage for `.ts` and `.svelte` files |

## Vitest Configuration

Update `vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': 'http://localhost:8000'
		}
	},
	test: {
		environment: 'happy-dom',
		globals: true,
		setupFiles: ['./src/lib/test/setup.ts'],
		include: ['src/**/*.{test,spec}.{js,ts}'],
		coverage: {
			provider: 'v8',
			reporter: ['text', 'json', 'html'],
			include: ['src/**/*.svelte', 'src/**/*.ts'],
			exclude: ['src/**/*.test.ts', 'src/**/*.spec.ts', 'src/lib/test/**', 'src/routes/**']
		}
	}
});
```

## Test Utilities & Setup

Create `src/lib/test/setup.ts`:

```ts
import { vi } from 'vitest';
import '@testing-library/jest-dom/vitest';

// --- Polyfill crypto.randomUUID for happy-dom ---
if (typeof crypto !== 'undefined' && !crypto.randomUUID) {
	crypto.randomUUID = () => '00000000-0000-0000-0000-000000000000';
}

// --- Mock svelte-i18n ($lib/i18n) ---
const enTranslations: Record<string, unknown> = (
	await import('$lib/i18n/locales/en.json')
).default;

function translate(key: string, options?: { values?: Record<string, unknown> }): string {
	const keys = key.split('.');
	let value: unknown = enTranslations;
	for (const k of keys) {
		value = (value as Record<string, unknown>)?.[k];
	}
	let result = typeof value === 'string' ? value : key;
	if (options?.values) {
		for (const [k, v] of Object.entries(options.values)) {
			result = result.replace(new RegExp(`{${k}}`, 'g'), String(v));
		}
	}
	return result;
}

vi.mock('$lib/i18n', async () => {
	const { readable } = await import('svelte/store');
	return {
		_: readable(translate),
		locale: readable('en'),
		setupI18n: () => Promise.resolve(),
		setLocale: () => {},
		getConfiguredDefaultLocale: () => 'en',
		SUPPORTED_LOCALES: ['en', 'de'] as const
	};
});

// --- Mock $app/stores and $app/navigation ---
vi.mock('$app/stores', async () => {
	const { readable } = await import('svelte/store');
	return {
		page: readable({
			url: new URL('http://localhost:5173/'),
			params: {},
			route: { id: null }
		}),
		navigating: readable(null)
	};
});

vi.mock('$app/navigation', () => ({
	goto: () => Promise.resolve(),
	beforeNavigate: () => {},
	afterNavigate: () => {},
	onNavigate: () => () => {}
}));

// --- Reset DOM between tests ---
import { cleanup } from '@testing-library/svelte';

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});
```

## Component Test Examples

### 1. StarRating.test.ts

```ts
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import StarRating from './StarRating.svelte';

describe('StarRating', () => {
	it('renders 5 radio inputs', () => {
		render(StarRating, { props: { value: null } });
		expect(screen.getAllByRole('radio')).toHaveLength(5);
	});

	it('checks the star matching the value prop', () => {
		render(StarRating, { props: { value: 3 } });
		const stars = screen.getAllByRole('radio');
		expect(stars[0]).not.toBeChecked();
		expect(stars[1]).not.toBeChecked();
		expect(stars[2]).toBeChecked();
		expect(stars[3]).not.toBeChecked();
		expect(stars[4]).not.toBeChecked();
	});

	it('calls onChange with the clicked star value', async () => {
		const onChange = vi.fn();
		render(StarRating, { props: { value: null, onChange } });

		const stars = screen.getAllByRole('radio');
		await fireEvent.click(stars[3]);

		expect(onChange).toHaveBeenCalledTimes(1);
		expect(onChange).toHaveBeenCalledWith(4);
	});

	it('does not call onChange when readonly', async () => {
		const onChange = vi.fn();
		render(StarRating, { props: { value: 2, readonly: true, onChange } });

		const stars = screen.getAllByRole('radio');
		await fireEvent.click(stars[4]);

		expect(onChange).not.toHaveBeenCalled();
		expect(stars[4]).not.toBeChecked();
	});

	it('has accessible aria-labels for each star', () => {
		render(StarRating, { props: { value: null } });
		expect(screen.getByLabelText('1 star')).toBeInTheDocument();
		expect(screen.getByLabelText('5 star')).toBeInTheDocument();
	});
});
```

### 2. BookCard.test.ts

```ts
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import BookCard from './BookCard.svelte';
import type { Book } from '$lib/types';

const mockBook = (overrides?: Partial<Book>): Book => ({
	id: 1,
	title: 'The Test Book',
	subtitle: null,
	author: 'Jane Tester',
	isbn: '9781234567890',
	cover_url: 'http://localhost/cover.jpg',
	publisher: null,
	published_year: 2024,
	page_count: 300,
	language: 'en',
	tags: 'fiction,classic',
	notes: null,
	blurb: null,
	rating: 4,
	reading_status: 'currently_reading',
	date_added: '2024-01-01T00:00:00.000Z',
	date_started: null,
	date_finished: null,
	...overrides
});

describe('BookCard', () => {
	it('renders title and author', () => {
		render(BookCard, { props: { book: mockBook(), onClick: vi.fn() } });
		expect(screen.getByText('The Test Book')).toBeInTheDocument();
		expect(screen.getByText('Jane Tester')).toBeInTheDocument();
	});

	it('shows cover image when cover_url is present', () => {
		render(BookCard, { props: { book: mockBook(), onClick: vi.fn() } });
		const img = screen.getByAltText('Cover of The Test Book');
		expect(img).toBeInTheDocument();
		expect(img).toHaveAttribute('src', 'http://localhost/cover.jpg');
	});

	it('shows placeholder when cover_url is missing', () => {
		render(BookCard, {
			props: { book: mockBook({ cover_url: null }), onClick: vi.fn() }
		});
		expect(screen.queryByAltText(/Cover of/)).not.toBeInTheDocument();
	});

	it('shows reading status badge', () => {
		render(BookCard, { props: { book: mockBook(), onClick: vi.fn() } });
		expect(screen.getByText('Currently Reading')).toBeInTheDocument();
	});

	it('shows progress bar when currentPage is greater than 0', () => {
		render(BookCard, {
			props: { book: mockBook(), onClick: vi.fn(), currentPage: 150 }
		});
		const progress = document.querySelector('.bg-primary.rounded-full');
		expect(progress).toBeInTheDocument();
		expect(progress).toHaveAttribute('style', expect.stringContaining('width: 50%'));
	});

	it('does not show progress bar when currentPage is 0', () => {
		render(BookCard, {
			props: { book: mockBook(), onClick: vi.fn(), currentPage: 0 }
		});
		expect(document.querySelector('.bg-primary.rounded-full')).not.toBeInTheDocument();
	});

	it('calls onClick with the book when card is clicked', async () => {
		const book = mockBook();
		const onClick = vi.fn();
		render(BookCard, { props: { book, onClick } });

		const card = screen.getByText('The Test Book').closest('button');
		await fireEvent.click(card!);

		expect(onClick).toHaveBeenCalledTimes(1);
		expect(onClick).toHaveBeenCalledWith(book);
	});
});
```

### 3. TagInput.test.ts

```ts
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
	});

	it('shows suggestions after debounce when typing', async () => {
		const fetchSuggestions = vi.fn(async () => ['fantasy', 'fiction', 'history']);
		render(TagInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'fan' } });
		expect(fetchSuggestions).not.toHaveBeenCalled();

		vi.advanceTimersByTime(300);

		await waitFor(() => {
			expect(screen.getByText('fantasy')).toBeInTheDocument();
			expect(screen.getByText('fiction')).toBeInTheDocument();
		});
	});

	it('navigates suggestions with ArrowDown/ArrowUp and selects with Enter', async () => {
		const fetchSuggestions = vi.fn(async () => ['alpha', 'beta']);
		render(TagInput, { props: { value: '', fetchSuggestions } });

		const input = screen.getByRole('textbox');
		await fireEvent.input(input, { target: { value: 'al' } });
		vi.advanceTimersByTime(300);

		await waitFor(() => screen.getByText('alpha'));

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
		vi.advanceTimersByTime(300);

		await waitFor(() => screen.getByText('result'));
		await fireEvent.keyDown(input, { key: 'Escape' });
		expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
	});

	it('disables interaction when disabled prop is true', () => {
		render(TagInput, { props: { value: 'tag', disabled: true } });
		expect(screen.getByRole('textbox')).toBeDisabled();
		expect(screen.queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument();
	});
});
```

## File Structure

```
frontend/src/lib/
├── api.ts
├── api.test.ts              # existing
├── date.ts
├── date.test.ts             # existing
├── errors.ts
├── errors.test.ts           # existing
├── validation.ts
├── validation.test.ts       # existing
├── test/
│   └── setup.ts             # NEW: global mocks, matchers, cleanup
├── i18n/
│   └── ...
├── components/
│   ├── StarRating.svelte
│   ├── StarRating.test.ts   # NEW
│   ├── BookCard.svelte
│   ├── BookCard.test.ts     # NEW
│   ├── TagInput.svelte
│   ├── TagInput.test.ts     # NEW
│   ├── SearchBar.svelte
│   └── SearchBar.test.ts    # NEW (future)
└── stores/
    ├── auth.ts
    └── timezone.ts
```

## Running Tests

Update `package.json` scripts:

```json
{
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "prepare": "svelte-kit sync || echo ''",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
    "check:watch": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json --watch",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  }
}
```

## Implementation Order

1. Install dependencies and update `vite.config.ts`
2. Create `src/lib/test/setup.ts` with i18n mock
3. Run existing tests to verify nothing breaks
4. Write `StarRating.test.ts` (simplest component)
5. Write `BookCard.test.ts` (display component with sub-components)
6. Write `TagInput.test.ts` (complex stateful component)
7. Add `SearchBar.test.ts` and others
8. Enable coverage reporting

## Known Constraints

| Constraint | Mitigation |
|------------|------------|
| Svelte 5 runes | `@testing-library/svelte@^5` handles `$props`, `$state`, `$derived`, `$bindable` |
| `$_` i18n syntax | Mocked in setup using a `readable` store that returns a translator function |
| `crypto.randomUUID` | Polyfilled in setup for happy-dom compatibility |
| `$app/stores` / `$app/navigation` | Mocked in setup so future component imports won't crash |
| Tailwind/DaisyUI classes | Not processed in tests, but elements are still renderable. Assert on roles, text, and attributes rather than computed styles |

## Coverage Targets

- **Utility functions**: 90%+ (already close)
- **Simple components** (StarRating, BookCard, SearchBar): 80%+
- **Complex components** (TagInput, AddBookModal): 70%+
- **Page components** (`src/routes/**`): Exclude or measure via E2E
