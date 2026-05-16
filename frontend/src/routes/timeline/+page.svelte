<script lang="ts">
	import { onMount } from 'svelte';
	import dayjs from 'dayjs';
	import type { Book } from '$lib/types';
	import { api } from '$lib/api';
	import { _, locale } from '$lib/i18n';
	import { toasts } from '$lib/toasts';
	import { shouldShowActionToast } from '$lib/errors';
	import { getTimezone } from '$lib/stores/timezone';
	import BookDetailDialog from '$lib/components/BookDetailDialog.svelte';
	import BookDrawer from '$lib/components/BookDrawer.svelte';

	let loading = $state(true);
	let books = $state<Book[]>([]);
	let selectedBook = $state<Book | null>(null);
	let detailOpen = $state(false);
	let drawerOpen = $state(false);
	let tz = $state('UTC');
	const appLocale: string = $derived($locale ?? 'en');

	onMount(() => {
		tz = getTimezone();
		void loadTimeline();
	});

	async function loadTimeline() {
		loading = true;
		try {
			const allRead = await api.books.list({
				status: 'read',
				sort: 'date_finished',
				order: 'desc',
				smart_sort: false
			});
			books = allRead.filter((b) => b.date_finished !== null);
		} catch (e: unknown) {
			const msg = e instanceof Error ? e.message : $_('common.actionFailed', { values: { action: 'load' } });
			if (shouldShowActionToast(msg)) {
				toasts.add(msg, 'error');
			}
			books = [];
		} finally {
			loading = false;
		}
	}

	let grouped = $derived.by(() => {
		const map = new Map<string, Book[]>();
		for (const b of books) {
			if (!b.date_finished) continue;
			const key = dayjs(b.date_finished).tz(tz).format('YYYY-MM');
			if (!map.has(key)) map.set(key, []);
			map.get(key)!.push(b);
		}
		return [...map.entries()].sort(([a], [b]) => b.localeCompare(a));
	});

	interface TimelineHeader { type: 'header'; key: string; dateFinished: string }
	interface TimelineBook { type: 'book'; book: Book }
	type TimelineItem = TimelineHeader | TimelineBook;

	let flatItems = $derived.by(() => {
		const items: TimelineItem[] = [];
		for (const [key, monthBooks] of grouped) {
			items.push({ type: 'header', key, dateFinished: monthBooks[0].date_finished! });
			for (const book of monthBooks) {
				items.push({ type: 'book', book });
			}
		}
		return items;
	});

	function formatMonthYear(iso: string): string {
		return dayjs(iso).tz(tz).toDate().toLocaleDateString(appLocale, {
			month: 'short',
			year: 'numeric'
		});
	}

	function formatDay(iso: string): string {
		return dayjs(iso).tz(tz).toDate().toLocaleDateString(appLocale, {
			month: 'short',
			day: 'numeric'
		});
	}

	function stars(rating: number | null): string {
		if (rating === null || rating < 1) return '';
		return '★'.repeat(rating) + '☆'.repeat(5 - rating);
	}

	function openDetailView(book: Book) {
		selectedBook = book;
		detailOpen = true;
		drawerOpen = false;
	}

	function openEditFromDetail(book: Book) {
		selectedBook = book;
		detailOpen = false;
		drawerOpen = true;
	}

	function handleSave(updated: Book) {
		if (updated.reading_status !== 'read' || !updated.date_finished) {
			void loadTimeline();
			return;
		}
		books = books.map((b) => (b.id === updated.id ? updated : b));
	}

	function handleDelete(id: number) {
		detailOpen = false;
		drawerOpen = false;
		books = books.filter((b) => b.id !== id);
	}
</script>

<div class="flex flex-col gap-6">
	<div class="hero bg-base-100 rounded-box shadow-sm p-6">
		<div class="hero-content text-center p-0">
			<div class="max-w-md">
				<h1 class="text-2xl font-bold">{$_('timeline.title')}</h1>
				<p class="text-base-content/70 mt-2">{$_('timeline.subtitle')}</p>
				<a href="/library?status=read" class="btn btn-ghost btn-sm mt-3">{$_('timeline.viewInLibrary')}</a>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center py-16">
			<span class="loading loading-spinner loading-lg"></span>
		</div>
	{:else if books.length === 0}
		<div class="hero bg-base-100 rounded-box shadow-sm p-12">
			<div class="hero-content text-center">
				<div class="max-w-md">
					<p class="text-base-content/70">{$_('timeline.noReadBooks')}</p>
					<a href="/library" class="btn btn-primary btn-sm mt-4">{$_('library.title')}</a>
				</div>
			</div>
		</div>
	{:else}
		<ul class="timeline timeline-vertical timeline-snap-icon">
			{#each flatItems as item, i (item.type === 'header' ? item.key : item.book.id)}
				<li>
					{#if i > 0}<hr />{/if}
					{#if item.type === 'header'}
						<div class="timeline-start text-base font-semibold">
							{formatMonthYear(item.dateFinished)}
						</div>
						<div class="timeline-middle">
							<svg class="text-primary h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
								<circle cx="10" cy="10" r="5" />
							</svg>
						</div>
					{:else}
						<div class="timeline-start text-xs sm:text-sm">
							{formatDay(item.book.date_finished!)}
						</div>
						<div class="timeline-middle">
							<svg class="text-primary h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
								<circle cx="10" cy="10" r="3" />
							</svg>
						</div>
						<div
							class="timeline-end timeline-box cursor-pointer hover:bg-base-200 transition-colors"
							onclick={() => openDetailView(item.book)}
							role="button"
							tabindex="0"
							onkeydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									openDetailView(item.book);
								}
							}}
						>
							<div class="flex gap-3 items-start">
								{#if item.book.cover_url}
									<img
										src={item.book.cover_url}
										alt={item.book.title}
										class="w-10 h-14 object-cover rounded shrink-0"
									/>
								{/if}
								<div class="min-w-0">
									<p class="font-medium truncate">{item.book.title}</p>
									{#if item.book.author}
										<p class="text-sm text-base-content/70 truncate">{item.book.author}</p>
									{/if}
									{#if item.book.rating}
										<p class="text-warning text-sm">{stars(item.book.rating)}</p>
									{/if}
								</div>
							</div>
						</div>
					{/if}
					{#if i < flatItems.length - 1}<hr />{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>

<BookDetailDialog bind:book={selectedBook} bind:open={detailOpen} onEdit={openEditFromDetail} onDelete={handleDelete} />

<BookDrawer bind:book={selectedBook} bind:open={drawerOpen} onSave={handleSave} />
