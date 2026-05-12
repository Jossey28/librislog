<script lang="ts">
	import { _ } from '$lib/i18n';

	let {
		value = $bindable(''),
		disabled = false
	}: {
		value?: string;
		disabled?: boolean;
	} = $props();

	let inputValue = $state('');

	const tags = $derived.by(() =>
		value
			.split(',')
			.map((tag) => tag.trim())
			.filter(Boolean)
	);

	function setTags(nextTags: string[]) {
		value = nextTags.join(', ');
	}

	function addCurrentTag() {
		if (disabled) return;
		const next = inputValue.trim();
		if (!next) return;

		if (tags.some((existing) => existing.toLowerCase() === next.toLowerCase())) {
			inputValue = '';
			return;
		}

		setTags([...tags, next]);
		inputValue = '';
	}

	function removeTag(tag: string) {
		if (disabled) return;
		setTags(tags.filter((entry) => entry !== tag));
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ',') {
			event.preventDefault();
			addCurrentTag();
			return;
		}

		if (event.key === 'Backspace' && inputValue === '' && tags.length > 0) {
			event.preventDefault();
			setTags(tags.slice(0, -1));
		}
	}
</script>

<div class="flex flex-col gap-2">
	<span class="label label-text">{$_('book.tags')}</span>

	{#if tags.length > 0}
		<div class="flex flex-wrap gap-2">
			{#each tags as tag (tag)}
				<span class="badge badge-outline badge-primary gap-1 px-2 py-3 text-xs">
					{tag}
					{#if !disabled}
						<button
							type="button"
							class="btn btn-ghost btn-xs btn-circle"
							onclick={() => removeTag(tag)}
							aria-label={$_('common.remove')}
						>
							x
						</button>
					{/if}
				</span>
			{/each}
		</div>
	{/if}

	<input
		type="text"
		class="input input-bordered input-sm"
		placeholder={$_('book.tagsPlaceholder')}
		bind:value={inputValue}
		{disabled}
		onkeydown={handleKeydown}
		onblur={addCurrentTag}
	/>

	<p class="text-xs text-base-content/60">{$_('book.tagsHint')}</p>
</div>
