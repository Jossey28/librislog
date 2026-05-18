<script lang="ts">
	import { onMount } from 'svelte';
	import { _, locale } from '$lib/i18n';
	import { api } from '$lib/api';
	import type { StatisticsResponse } from '$lib/types';
	import { toasts } from '$lib/toasts';
	import { formatLanguageCode } from '$lib/utils/language';

	type Segment = {
		label: string;
		value: number;
		className: string;
	};

	type Point = {
		label: string;
		value: number;
	};

	let loading = $state(true);
	let stats = $state<StatisticsResponse | null>(null);

	onMount(() => {
		let active = true;
		void loadStatistics(() => active);
		return () => {
			active = false;
		};
	});

	async function loadStatistics(isActive: () => boolean) {
		loading = true;
		try {
			const data = await api.statistics.get();
			if (isActive()) {
				stats = data;
			}
		} catch (e: unknown) {
			if (isActive()) {
				const message = e instanceof Error ? e.message : $_('common.actionFailed', { values: { action: 'load' } });
				toasts.add(message, 'error');
				stats = null;
			}
		} finally {
			if (isActive()) {
				loading = false;
			}
		}
	}

	const appLocale: string = $derived($locale ?? 'en');

	function formatNumber(value: number | null | undefined, maximumFractionDigits = 2, minimumFractionDigits = 0): string {
		if (value === null || value === undefined) return '-';
		return new Intl.NumberFormat(appLocale, { maximumFractionDigits, minimumFractionDigits }).format(value);
	}

	function formatMonthLabel(value: string | null | undefined): string {
		if (!value) return '-';
		const [year, month] = value.split('-');
		const dt = new Date(Date.UTC(Number(year), Number(month) - 1, 1));
		if (Number.isNaN(dt.getTime())) return value;
		return dt.toLocaleDateString(appLocale, { month: 'short', year: 'numeric' });
	}

	function safePercentage(value: number, sum: number): number {
		if (sum <= 0) return 0;
		return (value / sum) * 100;
	}

	const languageSegments = $derived.by<Segment[]>(() => {
		if (!stats) return [];
		const colors = ['bg-primary', 'bg-secondary', 'bg-accent', 'bg-info', 'bg-success', 'bg-warning', 'bg-error'];
		return stats.language_distribution.map((entry, idx) => ({
			label: entry.language ? formatLanguageCode(entry.language, appLocale) : $_('statistics.unknownLanguage'),
			value: entry.count,
			className: colors[idx % colors.length]
		}));
	});

	const statusSegments = $derived.by<Segment[]>(() => {
		if (!stats) return [];
		return [
			{ label: $_('status.want_to_read'), value: stats.status_distribution.want_to_read, className: 'bg-info' },
			{ label: $_('status.currently_reading'), value: stats.status_distribution.currently_reading, className: 'bg-warning' },
			{ label: $_('status.read'), value: stats.status_distribution.read, className: 'bg-success' },
			{ label: $_('status.did_not_finish'), value: stats.status_distribution.did_not_finish, className: 'bg-error' }
		].filter((item) => item.value > 0);
	});

	const pageSegments = $derived.by<Segment[]>(() => {
		if (!stats) return [];
		return [
			{ label: $_('statistics.pagesToRead'), value: stats.page_buckets.pages_to_read, className: 'bg-info' },
			{ label: $_('statistics.pagesRead'), value: stats.page_buckets.pages_read, className: 'bg-success' },
			{ label: $_('statistics.pagesWasted'), value: stats.page_buckets.pages_wasted, className: 'bg-error' }
		].filter((item) => item.value > 0);
	});

	function toPoints(source: Array<{ month: string; pages: number }> | Array<{ month: string; count: number }>): Point[] {
		return source.map((entry) => ({
			label: formatMonthLabel(entry.month),
			value: 'pages' in entry ? entry.pages : entry.count
		}));
	}

	function toYearPoints(source: Array<{ year: number; count: number }>): Point[] {
		return source.map((entry) => ({
			label: String(entry.year),
			value: entry.count
		}));
	}

	function buildLine(points: Point[]) {
		if (points.length === 0) return { path: '', circles: [] as Array<{ x: number; y: number; label: string; value: number }> };
		const width = 360;
		const height = 140;
		const padX = 24;
		const padY = 12;
		const innerW = width - padX * 2;
		const innerH = height - padY * 2;
		if (points.length === 1) {
			const centerX = width / 2;
			const max = Math.max(points[0].value, 1);
			const y = padY + innerH - (points[0].value / max) * innerH;
			return {
				path: '',
				circles: [{ x: centerX, y, label: points[0].label, value: points[0].value }]
			};
		}
		const max = Math.max(...points.map((p) => p.value), 1);
		const circles = points.map((p, idx) => {
			const x = padX + (idx / (points.length - 1)) * innerW;
			const y = padY + innerH - (p.value / max) * innerH;
			return { x, y, label: p.label, value: p.value };
		});
		const path = circles.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
		return { path, circles };
	}

	const pagesReadPoints = $derived(stats ? toPoints(stats.pages_read_per_month) : []);
	const booksByMonthPoints = $derived(stats ? toPoints(stats.books_finished_per_month) : []);
	const booksByYearPoints = $derived(stats ? toYearPoints(stats.books_finished_per_year) : []);

	const pagesReadLine = $derived(buildLine(pagesReadPoints));
	const booksByMonthLine = $derived(buildLine(booksByMonthPoints));
	const booksByYearLine = $derived(buildLine(booksByYearPoints));

	function chartLabels(points: Point[]): string[] {
		if (points.length <= 6) return points.map((p) => p.label);
		const step = Math.ceil(points.length / 6);
		return points.map((p, idx) => (idx % step === 0 || idx === points.length - 1 ? p.label : ''));
	}

	function total(segments: Segment[]): number {
		return segments.reduce((acc, curr) => acc + curr.value, 0);
	}
</script>

<div class="flex flex-col gap-6">
	<div class="hero rounded-2xl bg-base-100 shadow-sm border border-base-200">
		<div class="hero-content text-center py-10">
			<div class="max-w-2xl">
				<h1 class="text-3xl sm:text-4xl font-extrabold tracking-tight">{$_('statistics.title')}</h1>
				<p class="text-base-content/70 mt-2">{$_('statistics.subtitle')}</p>
			</div>
		</div>
	</div>

	{#if loading}
		<div class="card bg-base-100 border border-base-200 shadow-sm">
			<div class="card-body items-center py-10">
				<span class="loading loading-spinner loading-lg"></span>
				<p>{$_('statistics.loading')}</p>
			</div>
		</div>
	{:else if !stats}
		<div class="card bg-base-100 border border-base-200 shadow-sm">
			<div class="card-body py-10 text-center">
				<p>{$_('statistics.noData')}</p>
			</div>
		</div>
	{:else}
		<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
			<div class="stat bg-base-100 rounded-2xl shadow-sm border border-base-200">
				<div class="stat-title">{$_('statistics.avgBooksPerMonth')}</div>
				<div class="stat-value text-primary text-3xl">{formatNumber(stats.avg_books_per_month, 2, 1)}</div>
			</div>
			<div class="stat bg-base-100 rounded-2xl shadow-sm border border-base-200">
				<div class="stat-title">{$_('statistics.busiestMonth')}</div>
				<div class="stat-value text-success text-2xl">{formatMonthLabel(stats.busiest_month)}</div>
				<div class="stat-desc">{$_('statistics.booksCount', { values: { count: stats.busiest_month_count ?? 0 } })}</div>
			</div>
			<div class="stat bg-base-100 rounded-2xl shadow-sm border border-base-200">
				<div class="stat-title">{$_('statistics.avgPageCount')}</div>
				<div class="stat-value text-info text-3xl">{formatNumber(stats.avg_page_count, 0)}</div>
			</div>
			<div class="stat bg-base-100 rounded-2xl shadow-sm border border-base-200">
				<div class="stat-title">{$_('statistics.mostPopularLanguage')}</div>
				<div class="stat-value text-warning text-2xl">
					{stats.most_popular_language ? formatLanguageCode(stats.most_popular_language, appLocale) : '-'}
				</div>
				<div class="stat-desc">{formatNumber(stats.most_popular_language_count, 0)}</div>
			</div>
		</div>

		<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
			<div class="card bg-base-100 border border-base-200 shadow-sm">
				<div class="card-body">
					<h2 class="card-title text-base">{$_('statistics.languageDistribution')}</h2>
					<div role="img" aria-label={$_('statistics.languageDistribution')} class="flex h-8 w-full overflow-hidden rounded-lg bg-base-200">
						{#if total(languageSegments) === 0}
							<div class="w-full h-full"></div>
						{:else}
							{#each languageSegments as segment}
								<div class={`h-full ${segment.className}`} style={`width:${safePercentage(segment.value, total(languageSegments))}%`}></div>
							{/each}
						{/if}
					</div>
					<div class="flex flex-wrap gap-3 text-sm">
						{#each languageSegments as segment}
							<div class="flex items-center gap-2">
								<span class={`inline-block w-3 h-3 rounded ${segment.className}`}></span>
								<span>{segment.label}: {formatNumber(segment.value, 0)}</span>
							</div>
						{/each}
					</div>
				</div>
			</div>

			<div class="card bg-base-100 border border-base-200 shadow-sm">
				<div class="card-body">
					<h2 class="card-title text-base">{$_('statistics.statusDistribution')}</h2>
					<div role="img" aria-label={$_('statistics.statusDistribution')} class="flex h-8 w-full overflow-hidden rounded-lg bg-base-200">
						{#if total(statusSegments) === 0}
							<div class="w-full h-full"></div>
						{:else}
							{#each statusSegments as segment}
								<div class={`h-full ${segment.className}`} style={`width:${safePercentage(segment.value, total(statusSegments))}%`}></div>
							{/each}
						{/if}
					</div>
					<div class="flex flex-wrap gap-3 text-sm">
						{#each statusSegments as segment}
							<div class="flex items-center gap-2">
								<span class={`inline-block w-3 h-3 rounded ${segment.className}`}></span>
								<span>{segment.label}: {formatNumber(segment.value, 0)}</span>
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<div class="card bg-base-100 border border-base-200 shadow-sm">
			<div class="card-body">
				<h2 class="card-title text-base">{$_('statistics.pageBuckets')}</h2>
				<div role="img" aria-label={$_('statistics.pageBuckets')} class="flex h-8 w-full overflow-hidden rounded-lg bg-base-200">
					{#if total(pageSegments) === 0}
						<div class="w-full h-full"></div>
					{:else}
						{#each pageSegments as segment}
							<div class={`h-full ${segment.className}`} style={`width:${safePercentage(segment.value, total(pageSegments))}%`}></div>
						{/each}
					{/if}
				</div>
				<div class="flex flex-wrap gap-3 text-sm">
					{#each pageSegments as segment}
						<div class="flex items-center gap-2">
							<span class={`inline-block w-3 h-3 rounded ${segment.className}`}></span>
							<span>{segment.label}: {formatNumber(segment.value, 0)}</span>
						</div>
					{/each}
				</div>
				<p class="text-xs text-base-content/70">{$_('statistics.pagesWastedFootnote')}</p>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-4">
			<div class="card bg-base-100 border border-base-200 shadow-sm">
				<div class="card-body gap-4">
					<h2 class="card-title text-base">{$_('statistics.pagesReadPerMonth')}</h2>
					<svg viewBox="0 0 360 140" role="img" aria-label={$_('statistics.pagesReadPerMonth')} class="w-full h-40">
						<path d={pagesReadLine.path} class="stroke-primary fill-none" stroke-width="2"></path>
						{#each pagesReadLine.circles as point}
							<circle cx={point.x} cy={point.y} r="3" class="fill-primary">
								<title>{point.label}: {point.value}</title>
							</circle>
						{/each}
					</svg>
					<div class="flex justify-between gap-2 text-xs text-base-content/60 overflow-hidden">
						{#each chartLabels(pagesReadPoints) as label}
							<span class="truncate">{label}</span>
						{/each}
					</div>
				</div>
			</div>

			<div class="card bg-base-100 border border-base-200 shadow-sm">
				<div class="card-body gap-4">
					<h2 class="card-title text-base">{$_('statistics.booksFinishedPerMonth')}</h2>
					<svg viewBox="0 0 360 140" role="img" aria-label={$_('statistics.booksFinishedPerMonth')} class="w-full h-40">
						<path d={booksByMonthLine.path} class="stroke-secondary fill-none" stroke-width="2"></path>
						{#each booksByMonthLine.circles as point}
							<circle cx={point.x} cy={point.y} r="3" class="fill-secondary">
								<title>{point.label}: {point.value}</title>
							</circle>
						{/each}
					</svg>
					<div class="flex justify-between gap-2 text-xs text-base-content/60 overflow-hidden">
						{#each chartLabels(booksByMonthPoints) as label}
							<span class="truncate">{label}</span>
						{/each}
					</div>
				</div>
			</div>

			<div class="card bg-base-100 border border-base-200 shadow-sm">
				<div class="card-body gap-4">
					<h2 class="card-title text-base">{$_('statistics.booksFinishedPerYear')}</h2>
					<svg viewBox="0 0 360 140" role="img" aria-label={$_('statistics.booksFinishedPerYear')} class="w-full h-40">
						<path d={booksByYearLine.path} class="stroke-accent fill-none" stroke-width="2"></path>
						{#each booksByYearLine.circles as point}
							<circle cx={point.x} cy={point.y} r="3" class="fill-accent">
								<title>{point.label}: {point.value}</title>
							</circle>
						{/each}
					</svg>
					<div class="flex justify-between gap-2 text-xs text-base-content/60 overflow-hidden">
						{#each chartLabels(booksByYearPoints) as label}
							<span class="truncate">{label}</span>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<div class="card bg-base-100 border border-base-200 shadow-sm">
			<div class="card-body gap-3">
				<h2 class="card-title text-base">{$_('statistics.favoriteAuthor')}</h2>
				{#if stats.favorite_author}
					<div class="font-semibold text-lg">{stats.favorite_author.author}</div>
					<div class="text-sm text-base-content/70">
						{$_('statistics.booksCount', { values: { count: stats.favorite_author.book_count } })}
					</div>
					<div class="flex items-end gap-2 overflow-x-auto pb-1">
						{#each stats.favorite_author.cover_urls as url}
							<img src={url} alt={$_('book.cover')} class="h-28 w-auto rounded shadow-sm" />
						{/each}
					</div>
				{:else}
					<p class="text-base-content/70">{$_('statistics.noData')}</p>
				{/if}
			</div>
		</div>
	{/if}
</div>
