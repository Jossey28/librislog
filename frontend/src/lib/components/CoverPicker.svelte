<script lang="ts">
	import { api } from '$lib/api';
	import { toasts } from '$lib/toasts';

	let {
		value = $bindable<string | null>(null),
		disabled = false
	}: {
		value?: string | null;
		disabled?: boolean;
	} = $props();

	let urlInput = $state('');
	let uploading = $state(false);
	let dragging = $state(false);
	let fileInput: HTMLInputElement | undefined = $state();

	async function handleFile(file: File) {
		if (disabled) return;
		uploading = true;
		try {
			value = await api.covers.upload(file);
			urlInput = '';
		} catch (e: unknown) {
			toasts.add(e instanceof Error ? e.message : 'Upload failed', 'error');
		} finally {
			uploading = false;
		}
	}

	function onFileChange(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (file) handleFile(file);
		input.value = '';
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragging = false;
		const file = e.dataTransfer?.files?.[0];
		if (file) handleFile(file);
	}

	async function fetchUrl() {
		if (!urlInput.trim() || disabled) return;
		value = urlInput.trim();
		urlInput = '';
	}

	function clear() {
		value = null;
		urlInput = '';
	}
</script>

<div class="flex flex-col gap-2">
	<span class="label label-text">Cover</span>

	{#if value}
		<!-- Preview + clear -->
		<div class="flex items-start gap-3">
			<img src={value} alt="Cover preview" class="w-20 rounded shadow object-cover flex-shrink-0" />
			{#if !disabled}
				<button
					type="button"
					class="btn btn-ghost btn-xs"
					onclick={clear}
					aria-label="Remove cover"
				>Remove</button>
			{/if}
		</div>
	{:else}
		<!-- Drop zone -->
		<div
			role="button"
			tabindex={disabled ? -1 : 0}
			aria-disabled={disabled}
			class="border-2 border-dashed rounded-lg p-4 text-center text-sm text-base-content/50 transition-colors
				{dragging ? 'border-primary bg-primary/10' : 'border-base-300'}
				{disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-primary'}"
			ondragover={(e) => { e.preventDefault(); dragging = true; }}
			ondragleave={() => (dragging = false)}
			ondrop={onDrop}
			onclick={() => !disabled && fileInput?.click()}
			onkeydown={(e) => e.key === 'Enter' && !disabled && fileInput?.click()}
		>
			{#if uploading}
				<span class="loading loading-spinner loading-sm"></span>
			{:else}
				<p>Drag & drop an image, or <span class="text-primary font-medium">browse</span></p>
			{/if}
		</div>

		<!-- Hidden file input -->
		<input
			bind:this={fileInput}
			type="file"
			accept="image/*"
			class="hidden"
			onchange={onFileChange}
		/>

		<!-- URL input -->
		<div class="flex gap-2">
			<input
				class="input input-bordered input-sm flex-1"
				placeholder="Or paste an image URL…"
				bind:value={urlInput}
				{disabled}
				onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), fetchUrl())}
			/>
			<button
				type="button"
				class="btn btn-sm btn-outline"
				disabled={disabled || !urlInput.trim()}
				onclick={fetchUrl}
			>Use URL</button>
		</div>
	{/if}
</div>
