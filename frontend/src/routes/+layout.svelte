<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import AddBookModal from '$lib/components/AddBookModal.svelte';
	import Toaster from '$lib/components/Toaster.svelte';
	import { _, setupI18n } from '$lib/i18n';

	let { children } = $props();

	let addBookOpen = $state(false);
	let i18nReady = $state(false);

	// Expose a way for pages to trigger open
	// We use context to share this across routes
	import { setContext } from 'svelte';
	setContext('openAddBook', () => (addBookOpen = true));

	onMount(async () => {
		await setupI18n();
		i18nReady = true;
	});

	const NAV_ITEMS = [
		{ href: '/?status=want_to_read', labelKey: 'nav.want_to_read', icon: '📚' },
		{ href: '/?status=currently_reading', labelKey: 'nav.currently_reading', icon: '📖' },
		{ href: '/?status=read', labelKey: 'nav.read', icon: '✓' },
		{ href: '/?status=did_not_finish', labelKey: 'nav.did_not_finish', icon: '❌' },
		{ href: '/settings', labelKey: 'app.settings', icon: '⚙️' }
	];

	const STATUS_LABEL_KEYS: Record<string, string> = {
		want_to_read: 'status.want_to_read',
		currently_reading: 'status.currently_reading',
		read: 'status.read',
		did_not_finish: 'status.did_not_finish'
	};

	function pageTitle() {
		if (!i18nReady) return 'LibrisLog';

		if ($page.url.pathname.startsWith('/settings')) {
			return `${$_('app.title')} - ${$_('settings.title')}`;
		}

		const status = $page.url.searchParams.get('status') ?? 'want_to_read';
		const statusKey = STATUS_LABEL_KEYS[status] ?? STATUS_LABEL_KEYS.want_to_read;
		return `${$_('app.title')} - ${$_(statusKey)}`;
	}
</script>

<svelte:head>
	<title>{pageTitle()}</title>
</svelte:head>

{#if !i18nReady}
	<div class="min-h-screen bg-base-200 flex items-center justify-center">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else}
<div class="min-h-screen bg-base-200 flex">
	<!-- Sidebar (desktop) -->
	<aside class="hidden md:flex flex-col w-56 bg-base-100 shadow-md fixed top-0 left-0 h-full z-30 p-4 gap-4">
		<div class="text-xl font-bold tracking-tight py-2 px-1">{$_('app.title')}</div>
		<nav class="flex flex-col gap-1 flex-1">
			{#each NAV_ITEMS as item}
				<a
					href={item.href}
					class="btn btn-ghost btn-sm justify-start gap-2 font-normal"
				>
					<span>{item.icon}</span>{$_(item.labelKey)}
				</a>
			{/each}
		</nav>
		<button class="btn btn-primary btn-sm" onclick={() => (addBookOpen = true)}>+ {$_('app.addBook')}</button>
	</aside>

	<!-- Main content -->
	<div class="flex-1 flex flex-col md:ml-56 min-h-screen">
		<!-- Mobile top bar -->
		<header class="md:hidden flex items-center justify-between px-4 py-3 bg-base-100 shadow-sm sticky top-0 z-20">
			<span class="text-lg font-bold tracking-tight">{$_('app.title')}</span>
			<button class="btn btn-primary btn-sm" onclick={() => (addBookOpen = true)}>+ {$_('app.add')}</button>
		</header>

		<!-- Page content -->
		<main class="flex-1 p-4 pb-24 md:pb-4">
			{@render children()}
		</main>

		<!-- Mobile bottom tab bar -->
		<nav class="md:hidden fixed bottom-0 left-0 right-0 bg-base-100 border-t border-base-200 z-20 flex">
			{#each NAV_ITEMS as item}
				<a
					href={item.href}
					class="flex flex-col items-center justify-center flex-1 py-2 text-xs gap-0.5 text-base-content/60 hover:text-base-content"
				>
					<span class="text-lg leading-none">{item.icon}</span>
					<span>{$_(item.labelKey)}</span>
				</a>
			{/each}
		</nav>
	</div>
</div>
{/if}

<AddBookModal bind:open={addBookOpen} onAdded={() => {}} />
<Toaster />
